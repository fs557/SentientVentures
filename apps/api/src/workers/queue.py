"""Bounded local queue for the Phase 4 document preparation stages."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..core.classify import build_document_index
from ..core.facts import extract_facts, investment_terms
from ..core.pdf_extract import PdfExtractionError, extract_pdf
from ..core.storage import atomic_write_json
from ..core.storage import write_evaluation_set
from ..core.submissions import MAX_JOB_ATTEMPTS, SubmissionRepository, SubmissionStorageError
from ..core.scoring import category_scores, overall_score
from ..core.council import CouncilError, run_council
from ..providers.council import CouncilProvider

_STAGES = (("validating", 5), ("extracting", 20), ("classifying", 35), ("fact_extracting", 50), ("council_preparing", 55), ("council", 70), ("validating_output", 85), ("publishing", 95))
_ERROR_MESSAGES = {
    "PROVIDER_UNAVAILABLE": "The LLM council provider is unavailable or misconfigured. Check the provider, model, credentials, and network access.",
    "COUNCIL_OUTPUT_INVALID": "The LLM council returned an invalid evaluation. The result was not published.",
}


class ProcessingWorker:
    def __init__(self, repository: SubmissionRepository, provider: CouncilProvider | None = None) -> None:
        self.repository = repository
        # Phase 4 callers intentionally omit a provider and stop at the durable
        # council-preparation checkpoint.  Application wiring opts in explicitly.
        self.provider = provider
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        for slug in self.repository.recover_processing_jobs():
            await self.enqueue(slug)
        self._task = asyncio.create_task(self._run(), name="submission-processing-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)
        await self._task
        self._task = None

    async def enqueue(self, slug: str) -> None:
        await self._queue.put(slug)

    async def _run(self) -> None:
        while True:
            slug = await self._queue.get()
            if slug is None:
                return
            await self.process(slug)

    async def process(self, slug: str) -> None:
        try:
            await asyncio.to_thread(self._process_sync, slug)
        except Exception:
            # Per-job errors are persisted in _process_sync. The queue must survive one bad upload.
            return

    def _process_sync(self, slug: str) -> None:
        try:
            metadata = self.repository.load_processing_metadata(slug)
            job = metadata["current_job"]
            if not isinstance(job, dict) or job.get("state") != "queued":
                return
            job_id = str(job["id"])
            self._stage(slug, job_id, "validating", 5)
            documents = metadata.get("source_documents")
            if not isinstance(documents, list) or not documents:
                raise PdfExtractionError("INVALID_MANIFEST", "Submission manifest is invalid")
            self._stage(slug, job_id, "extracting", 20)
            company = self.repository.company_ref(slug)
            extractions = []
            for raw_document in documents:
                if not isinstance(raw_document, dict):
                    raise PdfExtractionError("INVALID_MANIFEST", "Submission manifest is invalid")
                document_id = raw_document.get("id")
                stored_name = raw_document.get("stored_name")
                if not isinstance(document_id, str) or not isinstance(stored_name, str):
                    raise PdfExtractionError("INVALID_MANIFEST", "Submission manifest is invalid")
                extraction = extract_pdf(company.path("source", stored_name), document_id)
                extractions.append(extraction)
                raw_document["page_count"] = extraction.page_count
                raw_document["extraction"] = {"native_pages": list(extraction.native_pages), "ocr_pages": list(extraction.ocr_pages), "warnings": list(extraction.warnings)}
            atomic_write_json(company, "extracted/document-text.json", {"version": 1, "documents": [item.as_dict() for item in extractions]})
            self.repository.update_processing_metadata(slug, job_id, {"source_documents": documents})
            self._stage(slug, job_id, "classifying", 35)
            index = build_document_index(documents, extractions)
            atomic_write_json(company, "extracted/document-index.json", index)
            self._stage(slug, job_id, "fact_extracting", 50)
            facts = extract_facts(metadata, extractions)
            atomic_write_json(company, "extracted/company-facts.json", {"version": 1, "facts": [fact.as_dict() for fact in facts if fact.subject != "founder"]})
            atomic_write_json(company, "extracted/founder-facts.json", {"version": 1, "facts": [fact.as_dict() for fact in facts if fact.subject == "founder"]})
            self._stage(slug, job_id, "council_preparing", 55)
            if self.provider is None:
                return
            self._stage(slug, job_id, "council", 70)
            documents, repair_count = run_council(metadata, facts, self.provider)
            self._stage(slug, job_id, "validating_output", 85)
            # write_evaluation_set serializes and reparses every document before a swap.
            self._stage(slug, job_id, "publishing", 95)
            write_evaluation_set(company, documents)
            scores = category_scores({category: document.items for category, document in documents.items()})
            hashes = {category: sha256(company.path("evaluation", f"{slug}_{category}.md").read_bytes()).hexdigest() for category in documents}
            self.repository.publish_ready(slug, job_id, {
                "schema_version": 1, "registry_version": 1, "category_scores": scores,
                "overall_score": overall_score(scores), "validation_errors": [], "output_hashes": hashes,
                "investment": investment_terms(facts),
            }, repair_count=repair_count)
            self._log(slug, job_id, "ready", "ok")
        except CouncilError as exc:
            self._fail(slug, locals().get("job_id"), exc.code)
        except PdfExtractionError as exc:
            self._fail(slug, locals().get("job_id"), exc.code)
        except (OSError, ValueError, SubmissionStorageError):
            self._fail(slug, locals().get("job_id"), "PROCESSING_FAILED")

    def _stage(self, slug: str, job_id: str, stage: str, progress: int) -> None:
        self.repository.update_job(slug, job_id, state="running", stage=stage, progress=progress, error=None, retry_allowed=False)
        self._log(slug, job_id, stage, "ok")

    def _fail(self, slug: str, job_id: object, code: str) -> None:
        if isinstance(job_id, str):
            try:
                job = self.repository.get_job(slug)
                attempt = job.get("attempt")
                retry_allowed = isinstance(attempt, int) and not isinstance(attempt, bool) and attempt < MAX_JOB_ATTEMPTS
                self.repository.update_job(slug, job_id, state="failed", stage="failed", progress=100,
                    error={"code": code, "message": _ERROR_MESSAGES.get(code, "Document processing could not be completed")}, retry_allowed=retry_allowed)
                self._log(slug, job_id, "failed", code)
            except SubmissionStorageError:
                pass

    def _log(self, slug: str, job_id: str, stage: str, outcome: str) -> None:
        company = self.repository.company_ref(slug)
        path = company.path("logs", f"job-{job_id}.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {"job_id": job_id, "company_slug": slug, "stage": stage, "outcome": outcome,
                 "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
