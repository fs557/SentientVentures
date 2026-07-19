"""Focused Phase 5 council, repair-bound, and ready-publication tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from src.api.companies import CompanyRepository, FixtureIndexError, FixtureRepository, LiveCompanyRepository
from src.core.council import CouncilError, run_council
from src.core.facts import FactRecord
from src.core.registry import REGISTRY
from src.core.scoring import category_scores, overall_score
from src.core.storage import CompanyRef, atomic_write_json, write_evaluation_set
from src.core.submissions import SubmissionRepository
from src.providers.council import DeterministicFakeProvider


def _metadata(slug: str = "council-labs") -> dict[str, object]:
    return {
        "company_id": str(uuid4()), "slug": slug, "display_name": "Council Labs",
        "created_at": "2026-07-19T12:00:00Z", "source_documents": [
            {"id": "doc_550e8400-e29b-41d4-a716-446655440000", "page_count": 1}
        ], "current_job": {"id": str(uuid4()), "state": "running", "stage": "council", "progress": 70,
                              "attempt": 1, "repairCount": 0, "updatedAt": "2026-07-19T12:00:00Z", "error": None, "retryAllowed": False},
    }


def _facts() -> list[FactRecord]:
    return [FactRecord("fact.company", "company", "company.name", "Council Labs", "fact", (
        {"kind": "fact", "documentId": "doc_550e8400-e29b-41d4-a716-446655440000", "page": 1,
         "text": "Council Labs supplies workflow software."},), ("doc_550e8400-e29b-41d4-a716-446655440000",))]


def test_fake_council_generates_all_registry_documents_without_network() -> None:
    documents, repairs = run_council(_metadata(), _facts(), DeterministicFakeProvider())
    assert repairs == 0
    assert set(documents) == {"home", "idea", "market", "financial", "management"}
    assert all(document.items for document in documents.values())
    assert all(item.score is None and item.confidence is None for document in documents.values() for item in document.items)


def test_structured_provider_scores_are_built_with_server_owned_evidence() -> None:
    class StructuredProvider(DeterministicFakeProvider):
        def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
            if role not in {"judge", "repair"}:
                return super().respond(role, prompt, payload)
            return {"evaluations": [{
                "id": entry.id,
                "score": 72 if entry.score_required and not entry.portfolio_required else None,
                "confidence": 68 if entry.score_required and not entry.portfolio_required else None,
                "assessment": "The submitted evidence supports a bounded assessment.",
                "positiveArguments": ["The submitted material provides direct support."],
                "negativeArguments": ["Independent validation remains outstanding."],
                "evidenceFactIds": ["fact.company"],
                "missingInformation": [],
            } for entry in REGISTRY]}

    documents, repairs = run_council(_metadata(), _facts(), StructuredProvider())
    assert repairs == 0
    assert documents["idea"].items[0].score == 72
    assert documents["idea"].items[0].confidence == 68
    assert documents["home"].items[0].score is None
    assert next(item for item in documents["market"].items if item.id == "market.portfolio_fit").score is None
    assert documents["idea"].items[0].evidence[0].document_id == "doc_550e8400-e29b-41d4-a716-446655440000"


def test_council_permits_exactly_one_contract_repair() -> None:
    class OneRepairProvider(DeterministicFakeProvider):
        calls: list[str] = []

        def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
            self.calls.append(role)
            if role == "judge":
                return {"documents": {}}
            return super().respond(role, prompt, payload)

    provider = OneRepairProvider()
    _, repairs = run_council(_metadata(), _facts(), provider)
    assert repairs == 1
    assert provider.calls == ["pro", "contra", "judge", "repair"]


def test_council_overwrites_provider_owned_identity_fields() -> None:
    class WrongIdentityProvider(DeterministicFakeProvider):
        def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
            result = super().respond(role, prompt, payload)
            if role in {"judge", "repair"}:
                documents = deepcopy(result["documents"])
                for document in documents.values():
                    document["company"] = "Provider Chosen Company"
                    document["slug"] = "provider-slug"
                    document["sourceDocuments"] = []
                    document["generatedAt"] = "1999-01-01T00:00:00Z"
                return {"documents": documents}
            return result

    documents, repairs = run_council(_metadata(), _facts(), WrongIdentityProvider())
    assert repairs == 0
    assert all(document.company == "Council Labs" for document in documents.values())
    assert all(document.slug == "council-labs" for document in documents.values())
    assert all(document.source_documents == ["doc_550e8400-e29b-41d4-a716-446655440000"] for document in documents.values())
    assert all(document.generated_at != "1999-01-01T00:00:00Z" for document in documents.values())


def test_council_rejects_fabricated_or_out_of_bounds_citations() -> None:
    class FabricatingProvider(DeterministicFakeProvider):
        def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
            result = super().respond(role, prompt, payload)
            if role in {"judge", "repair"}:
                documents = deepcopy(result["documents"])
                documents["idea"]["items"][0]["evidence"][0].update({"page": 999, "text": "Invented support"})
                return {"documents": documents}
            return result

    with pytest.raises(CouncilError, match="COUNCIL_OUTPUT_INVALID"):
        run_council(_metadata(), _facts(), FabricatingProvider())


def test_council_rejects_unsupported_numeric_score_and_factual_claim() -> None:
    class ScoringProvider(DeterministicFakeProvider):
        def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
            result = super().respond(role, prompt, payload)
            if role in {"judge", "repair"}:
                documents = deepcopy(result["documents"])
                documents["idea"]["items"][0].update({"score": 91, "confidence": 90, "assessment": "The company has a proven market advantage."})
                return {"documents": documents}
            return result

    with pytest.raises(CouncilError, match="COUNCIL_OUTPUT_INVALID"):
        run_council(_metadata(), _facts(), ScoringProvider())


def test_company_repository_fails_closed_on_live_fixture_slug_collision() -> None:
    class StaticIndex:
        def load_index(self) -> dict[str, object]:
            return {"same-slug": object()}

    repository = CompanyRepository(StaticIndex(), StaticIndex())  # type: ignore[arg-type]
    with pytest.raises(FixtureIndexError, match="collide"):
        repository.list_companies(50)


def test_atomic_publication_makes_live_company_listable_only_after_ready(tmp_path: Path) -> None:
    root = tmp_path / "companies"
    repository = SubmissionRepository(root)
    metadata = _metadata()
    company = CompanyRef.from_root(root, "council-labs")
    company.root.mkdir()
    atomic_write_json(company, "metadata.json", metadata)
    assert LiveCompanyRepository(root).load_index() == {}
    documents, _ = run_council(metadata, _facts(), DeterministicFakeProvider())
    write_evaluation_set(company, documents)
    scores = category_scores({category: document.items for category, document in documents.items()})
    repository.publish_ready("council-labs", str(metadata["current_job"]["id"]), {
        "schema_version": 1, "registry_version": 1, "category_scores": scores,
        "overall_score": overall_score(scores), "validation_errors": [], "output_hashes": {},
    }, repair_count=0)
    fixtures = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "companies"
    companies = CompanyRepository(FixtureRepository(fixtures), LiveCompanyRepository(root))
    record = companies.get_company("council-labs")
    assert record.company == "Council Labs"
    assert record.overall_score is None
