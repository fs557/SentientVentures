from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

from src.core.markdown import parse_evaluation_document
from src.core.registry import CATEGORIES
from src.core.scoring import category_scores, overall_score


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
