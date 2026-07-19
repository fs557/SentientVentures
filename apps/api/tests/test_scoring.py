from __future__ import annotations

from dataclasses import dataclass

from src.core.scoring import category_score, mean_score, overall_score, score_label


@dataclass
class Item:
    id: str
    score: int | None


def test_rounding_and_null_exclusion() -> None:
    assert mean_score([72, 73]) == 73
    assert mean_score([80, None, 90]) == 85
    assert mean_score([None, None]) is None


def test_home_is_never_scored_and_portfolio_unavailable_is_excluded() -> None:
    assert category_score("home", [Item("home.company_name", 100)]) is None
    market = [Item("market.portfolio_fit", None), Item("market.portfolio_synergies", None)]
    # Missing non-portfolio items are invalid artifacts, but unavailable portfolio criteria do not create a score.
    assert category_score("market", market) is None


def test_overall_is_equal_weighted_and_ignores_home() -> None:
    scores = {"home": None, "idea": 80, "market": 70, "financial": 60, "management": 50}
    assert overall_score(scores) == 65
    assert overall_score({"home": None, "idea": 80, "market": None, "financial": 70, "management": None}) == 75


def test_invalid_scores_never_gain_a_label() -> None:
    assert score_label(None) is None
    assert score_label(0) is None
    assert score_label(39) == "Critical"
    assert score_label(90) == "Exceptional"
