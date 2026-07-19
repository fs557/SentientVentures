#!/usr/bin/env python3
"""Generate deterministic, fictional v1 evaluation fixture companies from source facts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.core.markdown import EvidenceReference, EvaluationDocument, EvaluationItem
from src.core.registry import CATEGORIES, entries_for_category
from src.core.scoring import PORTFOLIO_UNAVAILABLE_IDS, category_scores, overall_score
from src.core.storage import CompanyRef, atomic_write_json, write_evaluation_set


def _load_facts(path: Path) -> list[dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    companies = parsed.get("companies")
    if not isinstance(companies, list) or len(companies) != 2:
        raise ValueError("Fixture facts must define exactly two companies")
    return companies


def _score(facts: dict[str, Any], category: str, order: int, item_id: str) -> int | None:
    if item_id in PORTFOLIO_UNAVAILABLE_IDS:
        return None
    # The calculation is deterministic and deliberately produces imperfect variation.
    category_offset = {"idea": 1, "market": -2, "financial": 0, "management": 2}.get(category, 0)
    return max(1, min(100, int(facts["scoreBase"]) + category_offset + ((order * 7) % 9) - 4))


def _document(facts: dict[str, Any], category: str) -> EvaluationDocument:
    source = str(facts["documentId"])
    items: list[EvaluationItem] = []
    for entry in entries_for_category(category):
        unavailable = entry.id in PORTFOLIO_UNAVAILABLE_IDS
        score = None if category == "home" else _score(facts, category, entry.display_order, entry.id)
        assessment = (
            f"For {entry.title.lower()}, the supplied fictional materials describe {facts['theme']}. "
            f"This assessment is limited to those materials."
        )
        if unavailable:
            assessment = "VC portfolio data is not configured, so this criterion is unavailable rather than estimated."
        items.append(EvaluationItem(
            id=entry.id, category=category, title=entry.title, score=score,
            confidence=None if unavailable else max(1, min(100, int(facts["scoreBase"]) + 5)),
            assessment=assessment,
            positive_arguments=[f"The materials indicate that {facts['strength']}."],
            negative_arguments=[f"A documented risk is that {facts['risk']} ."],
            evidence=[EvidenceReference("fact", source, f"Fixture fact: {facts['theme']}", page=1)],
            missing_information=["VC portfolio data is not configured." if unavailable else f"Not provided: {facts['missing']} ."],
            source_references=[EvidenceReference("fact", source, "Structured fixture facts", page=1)],
        ))
    return EvaluationDocument(1, 1, str(facts["company"]), str(facts["slug"]), category, str(facts["generatedAt"]), [source], items)


def _metadata(facts: dict[str, Any], documents: dict[str, EvaluationDocument]) -> dict[str, object]:
    scores = category_scores({category: document.items for category, document in documents.items()})
    return {
        "company_id": facts["companyId"], "slug": facts["slug"], "display_name": facts["company"], "stage": facts["stage"],
        "created_at": facts["generatedAt"], "state": "ready", "schema_version": 1, "registry_version": 1,
        "submission": {"founder_name": "Fictional Founder", "founder_email": "fictional@example.invalid"},
        "source_documents": [{"id": facts["documentId"], "role": "pitch_deck", "original_name": "fictional-pitch.pdf", "stored_name": "fixture-facts.json", "media_type": "application/pdf", "size_bytes": 0, "sha256": "0" * 64, "uploaded_at": facts["generatedAt"]}],
        "category_scores": scores, "overall_score": overall_score(scores), "validation_errors": [],
    }


def generate(destination: Path, facts_path: Path) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for facts in _load_facts(facts_path):
        slug = str(facts["slug"])
        company_root = destination / slug
        if company_root.exists():
            shutil.rmtree(company_root)
        reference = CompanyRef.from_root(destination, slug)
        documents = {category: _document(facts, category) for category in CATEGORIES}
        write_evaluation_set(reference, documents)
        atomic_write_json(reference, "extracted/company-facts.json", facts)
        atomic_write_json(reference, "extracted/document-index.json", {"documents": [{"id": facts["documentId"], "kind": "pitch_deck"}]})
        atomic_write_json(reference, "metadata.json", _metadata(facts, documents))
        for path in sorted(company_root.rglob("*")):
            if path.is_file(): hashes[str(path.relative_to(destination))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"generator": "v1", "files": dict(sorted(hashes.items()))}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tests/fixtures/companies")
    parser.add_argument("--facts", type=Path, default=ROOT / "tests/fixtures/example-company-facts.json")
    args = parser.parse_args()
    generate(args.output, args.facts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
