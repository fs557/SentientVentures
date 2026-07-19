from __future__ import annotations

from pathlib import Path

import pytest

from src.core.markdown import document_to_contract_dict, parse_evaluation_document, serialize_evaluation_document
from src.core.registry import entries_for_category


ROOT = Path(__file__).resolve().parents[3]
VALID = ROOT / "tests/fixtures/companies/aether-robotics/evaluation/aether-robotics_idea.md"


def _text() -> str:
    return VALID.read_text(encoding="utf-8")


def test_parses_complete_canonical_document() -> None:
    result = parse_evaluation_document(_text(), "aether-robotics", "idea")
    assert result.is_valid
    assert result.document is not None
    assert [item.id for item in result.document.items] == [entry.id for entry in entries_for_category("idea")]
    assert document_to_contract_dict(result.document)["schemaVersion"] == 1


def test_rejects_missing_front_matter() -> None:
    result = parse_evaluation_document(_text().replace("---\n", "", 1), "aether-robotics", "idea")
    assert not result.is_valid
    assert "FRONT_MATTER_MISSING" in {error.code for error in result.errors}


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        ("company: Aether Robotics", "company: 42"),
        ("slug: aether-robotics", "slug: [aether-robotics]"),
        ("category: idea", "category: {name: idea}"),
        ("generated_at: '2026-07-19T12:00:00Z'", "generated_at: [2026-07-19T12:00:00Z]"),
        ("source_documents:\n- doc_11111111-1111-4111-8111-111111111111", "source_documents: {id: fixture}"),
    ],
)
def test_malformed_front_matter_values_return_validation_issues(original: str, replacement: str) -> None:
    result = parse_evaluation_document(_text().replace(original, replacement, 1), "aether-robotics", "idea")
    assert not result.is_valid
    assert result.document is None
    assert "FRONT_MATTER_VALUE_INVALID" in {error.code for error in result.errors}


def test_rejects_duplicate_question_and_title_mismatch() -> None:
    text = _text()
    first = "## idea.uniqueness | How unique is the company idea?"
    replacement = first + "\n\n" + first
    result = parse_evaluation_document(text.replace(first, replacement, 1), "aether-robotics", "idea")
    assert not result.is_valid
    assert "DUPLICATE_ITEM" in {error.code for error in result.errors}
    result = parse_evaluation_document(text.replace("How unique is the company idea?", "Other title", 1), "aether-robotics", "idea")
    assert "REGISTRY_MISMATCH" in {error.code for error in result.errors}


def test_rejects_invalid_scores_but_preserves_item() -> None:
    result = parse_evaluation_document(_text().replace("**Score:** 86", "**Score:** 101", 1), "aether-robotics", "idea")
    assert not result.is_valid
    assert result.document is not None
    assert result.document.items[0].score is None
    assert result.document.items[0].validation_errors
    assert "SCORE_INVALID" in {error.code for error in result.errors}


def test_accepts_score_boundaries_and_home_na() -> None:
    assert parse_evaluation_document(_text().replace("**Score:** 86", "**Score:** 1", 1), "aether-robotics", "idea").is_valid
    assert parse_evaluation_document(_text().replace("**Score:** 86", "**Score:** 100", 1), "aether-robotics", "idea").is_valid
    home = Path(ROOT / "tests/fixtures/companies/aether-robotics/evaluation/aether-robotics_home.md").read_text(encoding="utf-8")
    assert parse_evaluation_document(home, "aether-robotics", "home").is_valid


def test_rejects_unknown_section_raw_html_and_slug_mismatch() -> None:
    text = _text().replace("### Assessment", "### Unknown", 1)
    result = parse_evaluation_document(text, "aether-robotics", "idea")
    assert not result.is_valid
    assert "SECTION_MISSING_OR_REORDERED" in {error.code for error in result.errors}
    result = parse_evaluation_document(_text().replace("This assessment", "<b>This assessment</b>", 1), "other-company", "idea")
    codes = {error.code for error in result.errors}
    assert {"RAW_HTML_FORBIDDEN", "SLUG_MISMATCH"} <= codes


def test_portfolio_na_is_allowed_only_for_the_configured_market_items() -> None:
    valid = Path(ROOT / "tests/fixtures/companies/aether-robotics/evaluation/aether-robotics_market.md").read_text(encoding="utf-8")
    assert parse_evaluation_document(valid, "aether-robotics", "market").is_valid
    result = parse_evaluation_document(_text().replace("**Score:** 86", "**Score:** N/A", 1), "aether-robotics", "idea")
    assert "SCORE_REQUIRED" in {error.code for error in result.errors}


def test_source_reference_kind_and_section_survive_markdown_round_trip() -> None:
    parsed = parse_evaluation_document(_text(), "aether-robotics", "idea")
    assert parsed.document is not None
    reference = parsed.document.items[0].source_references[0]
    reference.kind = "inference"
    reference.section = "section traction"
    rendered = serialize_evaluation_document(parsed.document)
    reparsed = parse_evaluation_document(rendered, "aether-robotics", "idea")
    assert reparsed.is_valid and reparsed.document is not None
    round_tripped = reparsed.document.items[0].source_references[0]
    assert (round_tripped.kind, round_tripped.section) == ("inference", "section traction")
