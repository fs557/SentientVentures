"""Contained, atomic filesystem operations for one resolved company root."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

from .markdown import EvaluationDocument, ParseResult, parse_evaluation_document, serialize_evaluation_document
from .registry import Category, CATEGORIES


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CompanyRef:
    slug: str
    root: Path

    @classmethod
    def from_root(cls, companies_root: Path, slug: str) -> "CompanyRef":
        if not slug or "/" in slug or "\\" in slug or slug in {".", ".."}:
            raise StorageError("Invalid company slug")
        base = companies_root.resolve()
        root = (base / slug).resolve()
        if root.parent != base:
            raise StorageError("Company path escapes configured storage")
        return cls(slug, root)

    def path(self, *parts: str) -> Path:
        target = self.root.joinpath(*parts).resolve()
        if target != self.root and self.root not in target.parents:
            raise StorageError("Company path escapes its root")
        return target


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(company: CompanyRef, relative_name: str, value: Mapping[str, object]) -> None:
    target = company.path(relative_name)
    atomic_write_bytes(target, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def write_evaluation_set(company: CompanyRef, documents: Mapping[Category, EvaluationDocument]) -> None:
    """Validate every document before replacing the complete evaluation directory."""
    if set(documents) != set(CATEGORIES):
        raise StorageError("An evaluation set must include exactly five categories")
    evaluation_root = company.path("evaluation")
    company.root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".evaluation.", dir=company.root))
    backup = company.path(".evaluation.previous")
    try:
        for category in CATEGORIES:
            text = serialize_evaluation_document(documents[category])
            result = parse_evaluation_document(text, company.slug, category)
            if not result.is_valid:
                raise StorageError(f"Serialized {category} evaluation failed validation")
            atomic_write_bytes(temporary / f"{company.slug}_{category}.md", text.encode("utf-8"))
        if backup.exists():
            raise StorageError("Previous evaluation swap has not been cleaned up")
        if evaluation_root.exists(): os.replace(evaluation_root, backup)
        os.replace(temporary, evaluation_root)
        if backup.exists():
            for child in backup.iterdir(): child.unlink()
            backup.rmdir()
    except Exception:
        # A failed second rename must not turn a previous valid evaluation into an
        # unavailable one. Restore it before reporting the failed replacement.
        if backup.exists() and not evaluation_root.exists():
            os.replace(backup, evaluation_root)
        if temporary.exists():
            for child in temporary.iterdir(): child.unlink()
            temporary.rmdir()
        raise


def read_evaluation(company: CompanyRef, category: Category) -> ParseResult:
    path = company.path("evaluation", f"{company.slug}_{category}.md")
    try:
        return parse_evaluation_document(path.read_text(encoding="utf-8"), company.slug, category)
    except OSError as exc:
        raise StorageError("Evaluation document is unavailable") from exc
