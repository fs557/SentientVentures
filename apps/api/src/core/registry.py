"""Read-only access to the frozen v1 question registry."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Final, Literal

Category = Literal["home", "idea", "market", "financial", "management"]
CATEGORIES: Final[tuple[Category, ...]] = ("home", "idea", "market", "financial", "management")
OVERALL_CATEGORIES: Final[tuple[Category, ...]] = ("idea", "market", "financial", "management")


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    id: str
    category: Category
    title: str
    score_required: bool
    portfolio_required: bool
    display_order: int
    rubric: str


class RegistryError(ValueError):
    """The checked-in registry is missing or violates its frozen invariants."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def registry_path() -> Path:
    return _repository_root() / "packages/contracts/schema/question-registry.v1.json"


def load_registry(path: Path | None = None) -> tuple[RegistryEntry, ...]:
    """Load and defensively validate the immutable registry in display order."""
    try:
        raw = json.loads((path or registry_path()).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError("Unable to read the question registry") from exc
    if raw.get("schemaVersion") != 1 or raw.get("registryVersion") != 1:
        raise RegistryError("Unsupported question registry version")
    if tuple(raw.get("categories", [])) != CATEGORIES:
        raise RegistryError("Question registry categories do not match v1")
    entries: list[RegistryEntry] = []
    for item in raw.get("entries", []):
        try:
            category = item["category"]
            if category not in CATEGORIES:
                raise RegistryError("Question registry contains an unknown category")
            entries.append(RegistryEntry(
                id=item["id"], category=category, title=item["title"],
                score_required=item["scoreRequired"], portfolio_required=item["portfolioRequired"],
                display_order=item["displayOrder"], rubric=item["rubric"],
            ))
        except (KeyError, TypeError) as exc:
            raise RegistryError("Question registry entry is malformed") from exc
    if len(entries) != 75 or len({entry.id for entry in entries}) != 75:
        raise RegistryError("Question registry must contain exactly 75 unique entries")
    for category in CATEGORIES:
        category_entries = [entry for entry in entries if entry.category == category]
        if [entry.display_order for entry in category_entries] != list(range(1, len(category_entries) + 1)):
            raise RegistryError(f"Question registry order is invalid for {category}")
    return tuple(entries)


REGISTRY: Final[tuple[RegistryEntry, ...]] = load_registry()
REGISTRY_BY_ID: Final[dict[str, RegistryEntry]] = {entry.id: entry for entry in REGISTRY}


def entries_for_category(category: Category) -> tuple[RegistryEntry, ...]:
    if category not in CATEGORIES:
        raise ValueError(f"Unsupported category: {category}")
    return tuple(entry for entry in REGISTRY if entry.category == category)
