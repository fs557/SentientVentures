"""The sole v1 implementation of deterministic evaluation scoring."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Protocol

from .registry import CATEGORIES, OVERALL_CATEGORIES, Category, RegistryEntry, entries_for_category

PORTFOLIO_UNAVAILABLE_IDS = frozenset({"market.portfolio_fit", "market.portfolio_synergies"})


class ScoredItem(Protocol):
    id: str
    score: int | None


def is_valid_score(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100


def round_half_up(value: Decimal | float | int) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def mean_score(scores: Iterable[object]) -> int | None:
    valid = [score for score in scores if is_valid_score(score)]
    if not valid:
        return None
    return round_half_up(Decimal(sum(valid)) / Decimal(len(valid)))


def category_score(
    category: Category,
    items: Iterable[ScoredItem],
    *,
    portfolio_available: bool = False,
) -> int | None:
    """Average valid required scores, preserving unavailable criteria as unavailable."""
    if category == "home":
        return None
    expected: dict[str, RegistryEntry] = {entry.id: entry for entry in entries_for_category(category)}
    supplied = {item.id: item for item in items}
    values: list[object] = []
    for item_id, entry in expected.items():
        if not entry.score_required:
            continue
        if entry.portfolio_required and not portfolio_available:
            continue
        values.append(supplied[item_id].score if item_id in supplied else None)
    return mean_score(values)


def category_scores(
    documents: Mapping[Category, Iterable[ScoredItem]], *, portfolio_available: bool = False
) -> dict[Category, int | None]:
    return {category: category_score(category, documents.get(category, ()), portfolio_available=portfolio_available)
            for category in CATEGORIES}


def overall_score(scores: Mapping[Category, int | None]) -> int | None:
    """Equal-weight mean of available non-Home category scores."""
    return mean_score(scores.get(category) for category in OVERALL_CATEGORIES)


def score_label(score: int | None) -> str | None:
    if not is_valid_score(score):
        return None
    if score <= 39:
        return "Critical"
    if score <= 59:
        return "Weak"
    if score <= 69:
        return "Mixed"
    if score <= 79:
        return "Promising"
    if score <= 89:
        return "Strong"
    return "Exceptional"
