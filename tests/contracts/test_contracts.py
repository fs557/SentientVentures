"""Phase-0 contract-boundary checks; no API or UI behavior belongs here."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "packages" / "contracts" / "schema"


def load(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_contract_documents_are_valid_json_schemas() -> None:
    for name in ("common.v1.json", "evaluation.v1.json", "api.v1.json"):
        jsonschema.Draft202012Validator.check_schema(load(name))


def test_registry_is_frozen_complete_and_ordered() -> None:
    registry = load("question-registry.v1.json")
    entries = registry["entries"]
    assert registry["schemaVersion"] == registry["registryVersion"] == 1
    assert registry["overallCategories"] == ["idea", "market", "financial", "management"]
    assert len(entries) == 75
    assert len({entry["id"] for entry in entries}) == 75
    categories = {category: [] for category in registry["categories"]}
    for entry in entries:
        categories[entry["category"]].append(entry)
        assert entry["id"].startswith(f'{entry["category"]}.')
        assert entry["title"] and entry["rubric"]
        assert entry["scoreRequired"] is (entry["category"] != "home")
        assert entry["portfolioRequired"] is (entry["id"] in {"market.portfolio_fit", "market.portfolio_synergies"})
    assert [len(categories[name]) for name in registry["categories"]] == [13, 12, 15, 19, 16]
    for entries_in_category in categories.values():
        assert [entry["displayOrder"] for entry in entries_in_category] == list(range(1, len(entries_in_category) + 1))


def test_scoring_vectors_capture_shared_rounding_contract() -> None:
    vectors = load("score-vectors.v1.json")["vectors"]
    assert {vector["name"] for vector in vectors} >= {"half-up-explicit", "exclude-null", "all-null", "overall-equal-weight"}
    assert next(vector for vector in vectors if vector["name"] == "half-up-explicit")["expected"] == 73
