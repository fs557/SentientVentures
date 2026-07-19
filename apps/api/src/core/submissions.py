"""Safe local persistence for submission metadata, documents, and jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
from threading import RLock
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .storage import CompanyRef, StorageError, atomic_write_bytes, atomic_write_json

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SAFE_NAME = re.compile(r"[^a-z0-9._-]+")
MAX_JOB_ATTEMPTS = 3


class SubmissionStorageError(RuntimeError):
    """A local submission artifact could not be persisted safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    normalized = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "company"


def safe_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name.lower()
    stem = _SAFE_NAME.sub("-", basename).strip(".-")
    if not stem:
        stem = "document.pdf"
    if not stem.endswith(".pdf"):
        stem += ".pdf"
    return stem[:80].rstrip(".") or "document.pdf"


@dataclass(frozen=True, slots=True)
class PendingDocument:
    role: str
    original_name: str
    content_type: str
    temporary_path: Path
    size_bytes: int
    sha256: str


class SubmissionRepository:
    """Filesystem-backed submission repository with one process-local write lock."""

    def __init__(self, companies_root: Path, *, reserved_slugs: Iterable[str] = ()) -> None:
        self.root = companies_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._idempotency_path = self.root / ".idempotency.json"
        self._reserved_slugs = frozenset(slug for slug in reserved_slugs if _SLUG.fullmatch(slug))
        self._lock = RLock()

    def create_temp_path(self) -> Path:
        uploads = self.root / ".uploads"
        uploads.mkdir(mode=0o700, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix="upload-", suffix=".pdf", dir=uploads)
        Path(name).chmod(0o600)
        # The caller opens it by path; close the descriptor first.
        import os

        os.close(descriptor)
        return Path(name)

    def persist_submission(
        self,
        *,
        request_hash: str,
        idempotency_key: str,
        company_name: str,
        founder_name: str,
        founder_email: str,
        linkedin_url: str | None,
        github_url: str | None,
        website_url: str | None,
        documents: list[PendingDocument],
    ) -> tuple[dict[str, Any], bool]:
        """Store one submission, or return its prior response for an exact replay."""
        with self._lock:
            records = self._load_idempotency()
            existing = records.get(idempotency_key)
            if existing is not None:
                if existing.get("request_hash") != request_hash:
                    raise SubmissionStorageError("IDEMPOTENCY_CONFLICT")
                response = existing.get("response")
                if isinstance(response, dict):
                    return response, True
                raise SubmissionStorageError("Stored idempotency record is invalid")

            slug = self._available_slug(company_name)
            company = CompanyRef.from_root(self.root, slug)
            company.root.mkdir(mode=0o700)
            source_root = company.path("source")
            source_root.mkdir(mode=0o700)
            created_at = utc_now()
            company_id = str(uuid4())
            source_documents: list[dict[str, object]] = []
            try:
                for pending in documents:
                    document_id = f"doc_{uuid4()}"
                    stored_name = f"{document_id}-{safe_filename(pending.original_name)}"
                    destination = company.path("source", stored_name)
                    shutil.move(str(pending.temporary_path), destination)
                    destination.chmod(0o600)
                    source_documents.append(
                        {
                            "id": document_id,
                            "role": pending.role,
                            "original_name": pending.original_name,
                            "stored_name": stored_name,
                            "media_type": "application/pdf",
                            "size_bytes": pending.size_bytes,
                            "sha256": pending.sha256,
                            "uploaded_at": created_at,
                        }
                    )
                job = self._new_job(slug)
                metadata: dict[str, object] = {
                    "company_id": company_id,
                    "slug": slug,
                    "display_name": company_name,
                    "created_at": created_at,
                    "submission": {
                        "founder_name": founder_name,
                        "founder_email": founder_email,
                        "linkedin_url": linkedin_url,
                        "github_url": github_url,
                        "website_url": website_url,
                    },
                    "source_documents": source_documents,
                    "current_job": job,
                    "job_history": [job],
                    "retry_idempotency": {},
                }
                atomic_write_json(company, "metadata.json", metadata)
                response: dict[str, Any] = {
                    "company": {"id": company_id, "slug": slug, "name": company_name},
                    "job": {"id": job["id"], "state": "queued", "statusUrl": f"/api/v1/jobs/{slug}"},
                    "acceptedAt": created_at,
                }
                records[idempotency_key] = {"request_hash": request_hash, "response": response}
                self._save_idempotency(records)
                return response, False
            except Exception:
                # No partially-created company is made addressable by an idempotency record.
                shutil.rmtree(company.root, ignore_errors=True)
                raise

    def get_job(self, slug: str) -> dict[str, object]:
        metadata = self._load_metadata(slug)
        job = metadata.get("current_job")
        if not isinstance(job, dict):
            raise SubmissionStorageError("Job is unavailable")
        return dict(job)

    def company_ref(self, slug: str) -> CompanyRef:
        """Resolve a company only through validated metadata."""
        return self._company_and_metadata(slug)[0]

    def load_processing_metadata(self, slug: str) -> dict[str, Any]:
        """Return a private metadata snapshot for an in-process worker."""
        with self._lock:
            return self._company_and_metadata(slug)[1]

    def update_processing_metadata(self, slug: str, job_id: str, updates: Mapping[str, object]) -> None:
        with self._lock:
            company, metadata = self._company_and_metadata(slug)
            job = metadata.get("current_job")
            if not isinstance(job, dict) or job.get("id") != job_id:
                raise SubmissionStorageError("STALE_JOB")
            metadata.update(updates)
            atomic_write_json(company, "metadata.json", metadata)

    def update_job(
        self, slug: str, job_id: str, *, state: str, stage: str, progress: int,
        error: Mapping[str, object] | None, retry_allowed: bool,
    ) -> None:
        """Persist a bounded job transition without accepting caller-provided paths."""
        if state not in {"queued", "running", "failed", "ready"} or not 0 <= progress <= 100:
            raise SubmissionStorageError("INVALID_JOB_UPDATE")
        with self._lock:
            company, metadata = self._company_and_metadata(slug)
            job = metadata.get("current_job")
            if not isinstance(job, dict) or job.get("id") != job_id:
                raise SubmissionStorageError("STALE_JOB")
            if job.get("state") in {"failed", "ready"}:
                raise SubmissionStorageError("STALE_JOB")
            job.update({"state": state, "stage": stage, "progress": progress, "updatedAt": utc_now(),
                        "error": dict(error) if error is not None else None, "retryAllowed": retry_allowed})
            atomic_write_json(company, "metadata.json", metadata)

    def publish_ready(self, slug: str, job_id: str, updates: Mapping[str, object], *, repair_count: int) -> None:
        """Make an already-validated evaluation discoverable in one metadata write.

        Evaluation files are swapped before this call.  Thus a crash can leave an
        unindexed candidate set, but can never expose a partial set as ready.
        """
        with self._lock:
            company, metadata = self._company_and_metadata(slug)
            job = metadata.get("current_job")
            if not isinstance(job, dict) or job.get("id") != job_id or job.get("state") in {"failed", "ready"}:
                raise SubmissionStorageError("STALE_JOB")
            metadata.update(updates)
            metadata["state"] = "ready"
            job.update({"state": "ready", "stage": "ready", "progress": 100, "updatedAt": utc_now(),
                        "repairCount": repair_count, "error": None, "retryAllowed": False})
            atomic_write_json(company, "metadata.json", metadata)

    def recover_processing_jobs(self) -> list[str]:
        """Resume queued work and make interrupted active work safely retryable."""
        queued: list[str] = []
        with self._lock:
            for root in self.root.iterdir():
                if not root.is_dir() or root.name.startswith(".") or not _SLUG.fullmatch(root.name):
                    continue
                try:
                    company, metadata = self._company_and_metadata(root.name)
                except SubmissionStorageError:
                    continue
                job = metadata.get("current_job")
                if not isinstance(job, dict):
                    continue
                if job.get("state") == "queued":
                    queued.append(root.name)
                elif job.get("state") == "running":
                    job.update({"state": "failed", "stage": "failed", "progress": 100, "updatedAt": utc_now(),
                                "error": {"code": "WORKER_INTERRUPTED", "message": "Processing was interrupted"}, "retryAllowed": True})
                    atomic_write_json(company, "metadata.json", metadata)
        return queued

    def retry_job(self, slug: str, idempotency_key: str) -> tuple[dict[str, object], bool]:
        with self._lock:
            company, metadata = self._company_and_metadata(slug)
            retry_records = metadata.get("retry_idempotency")
            if not isinstance(retry_records, dict):
                raise SubmissionStorageError("Stored retry record is invalid")
            replay = retry_records.get(idempotency_key)
            if isinstance(replay, dict):
                return dict(replay), True
            job = metadata.get("current_job")
            attempt = job.get("attempt") if isinstance(job, dict) else None
            if (not isinstance(job, dict) or job.get("state") != "failed"
                    or not isinstance(attempt, int) or isinstance(attempt, bool) or attempt >= MAX_JOB_ATTEMPTS):
                raise SubmissionStorageError("RETRY_NOT_ALLOWED")
            updated = self._new_job(slug, attempt=attempt + 1)
            history = metadata.get("job_history")
            if not isinstance(history, list):
                raise SubmissionStorageError("Stored job history is invalid")
            history.append(updated)
            metadata["current_job"] = updated
            retry_records[idempotency_key] = updated
            atomic_write_json(company, "metadata.json", metadata)
            return dict(updated), False

    def _available_slug(self, company_name: str) -> str:
        base = slugify(company_name)
        candidate = base
        number = 2
        while candidate in self._reserved_slugs or (self.root / candidate).exists():
            candidate = f"{base}-{number}"
            number += 1
        return candidate

    def _new_job(self, slug: str, *, attempt: int = 1) -> dict[str, object]:
        return {
            "id": str(uuid4()), "companySlug": slug, "state": "queued", "stage": "queued",
            "progress": 0, "attempt": attempt, "repairCount": 0, "updatedAt": utc_now(),
            "error": None, "retryAllowed": False,
        }

    def _company_and_metadata(self, slug: str) -> tuple[CompanyRef, dict[str, Any]]:
        if not _SLUG.fullmatch(slug):
            raise SubmissionStorageError("NOT_FOUND")
        try:
            company = CompanyRef.from_root(self.root, slug)
        except StorageError as exc:
            raise SubmissionStorageError("NOT_FOUND") from exc
        try:
            loaded = json.loads(company.path("metadata.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SubmissionStorageError("NOT_FOUND") from exc
        if not isinstance(loaded, dict) or loaded.get("slug") != slug:
            raise SubmissionStorageError("NOT_FOUND")
        return company, loaded

    def _load_metadata(self, slug: str) -> dict[str, Any]:
        return self._company_and_metadata(slug)[1]

    def _load_idempotency(self) -> dict[str, Any]:
        if not self._idempotency_path.exists():
            return {}
        try:
            value = json.loads(self._idempotency_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SubmissionStorageError("Idempotency records are unavailable") from exc
        if not isinstance(value, dict):
            raise SubmissionStorageError("Idempotency records are invalid")
        return value

    def _save_idempotency(self, records: Mapping[str, Any]) -> None:
        atomic_write_bytes(self._idempotency_path, (json.dumps(records, sort_keys=True) + "\n").encode("utf-8"))


def request_digest(fields: Mapping[str, str | None], documents: list[PendingDocument]) -> str:
    """Hash metadata and contents, never names/paths supplied by the server."""
    payload = {"fields": dict(sorted(fields.items())), "documents": [
        {"role": item.role, "name": item.original_name, "sha256": item.sha256, "size": item.size_bytes}
        for item in documents
    ]}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
