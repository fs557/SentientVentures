from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

from src.core.markdown import parse_evaluation_document
from src.core.registry import CATEGORIES, REGISTRY
from src.core.scoring import PORTFOLIO_UNAVAILABLE_IDS, category_scores, overall_score


def test_two_complete_fixture_companies_are_isolated_and_scored_from_artifacts() -> None:
    root = ROOT / "tests/fixtures/companies"
    summaries = {}
    for company in ("aether-robotics", "harborloop"):
        documents = {}
        for category in CATEGORIES:
            result = parse_evaluation_document((root / company / "evaluation" / f"{company}_{category}.md").read_text(encoding="utf-8"), company, category)
            assert result.is_valid
            assert result.document is not None
            documents[category] = result.document.items
        scores = category_scores(documents)
        assert scores["home"] is None
        summaries[company] = overall_score(scores)
    assert summaries["aether-robotics"] != summaries["harborloop"]


def test_fixture_criteria_are_complete_specific_and_terms_are_consistent() -> None:
    root = ROOT / "tests/fixtures/companies"
    expected_ids = {entry.id for entry in REGISTRY}
    for company in ("aether-robotics", "harborloop"):
        metadata = json.loads((root / company / "metadata.json").read_text(encoding="utf-8"))
        terms = metadata["investment"]
        assert terms["amount"] == 100000
        assert terms["postMoneyValuation"] == terms["preMoneyValuation"] + terms["amount"]
        assert terms["impliedValuation"] == terms["postMoneyValuation"]
        assert terms["equityPercentage"] == terms["amount"] / terms["postMoneyValuation"] * 100
        assert terms["useOfFunds"]

        items = []
        for category in CATEGORIES:
            result = parse_evaluation_document(
                (root / company / "evaluation" / f"{company}_{category}.md").read_text(encoding="utf-8"),
                company,
                category,
            )
            assert result.is_valid and result.document is not None
            items.extend(result.document.items)
        assert {item.id for item in items} == expected_ids
        assert len(items) == len(expected_ids)
        by_id = {item.id: item for item in items}
        assert by_id["home.company_name"].evidence[0].kind == "fact"
        assert by_id["financial.current_revenue"].evidence[0].kind == "fact"
        assert by_id["idea.defensibility"].evidence[0].kind == "inference"
        assert by_id["financial.projection_plausibility"].evidence[0].kind == "inference"
        assert by_id["idea.defensibility"].source_references[0].kind == "inference"
        terms_text = ", ".join(terms["useOfFunds"])
        assert terms_text in by_id["home.use_of_investment"].assessment
        assert f"{terms['currency']} {terms['amount']:,.0f}" in by_id["home.investment_requested"].assessment
        assert f"{terms['equityPercentage']:g}%" in by_id["home.equity_offered"].assessment
        assert f"{terms['currency']} {terms['impliedValuation']:,.0f}" in by_id["home.implied_valuation"].assessment
        for item in items:
            assert "This assessment is limited to those materials" not in item.assessment
            assert all("Not provided:" not in value for value in item.missing_information)
            assert item.assessment and item.positive_arguments and item.negative_arguments and item.evidence
            assert item.missing_information == []
            assert not item.evidence[0].text.startswith(item.id)
            assert "Structured fact" not in item.source_references[0].text
            if item.id in PORTFOLIO_UNAVAILABLE_IDS:
                assert item.score is None
                assert "portfolio" in item.assessment.lower()
        confidences = {item.confidence for item in items if item.confidence is not None}
        assert len(confidences) >= 8
