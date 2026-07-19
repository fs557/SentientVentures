"""Deterministic document indexing; uploaded roles are never inferred upward."""
from __future__ import annotations

from typing import Any, Iterable

from .pdf_extract import DocumentExtraction


def build_document_index(documents: Iterable[dict[str, Any]], extractions: Iterable[DocumentExtraction]) -> dict[str, Any]:
    by_id = {item.document_id: item for item in extractions}
    indexed: list[dict[str, Any]] = []
    for document in documents:
        document_id = document.get("id")
        extraction = by_id.get(document_id) if isinstance(document_id, str) else None
        if extraction is None:
            continue
        role = document.get("role")
        if role not in {"pitch_deck", "cv", "supporting"}:
            role = "supporting"
        indexed.append({
            "document_id": extraction.document_id,
            "role": role,
            "page_count": extraction.page_count,
            "text_pages": [page.page for page in extraction.pages if page.text],
            "warnings": list(extraction.warnings),
        })
    return {"version": 1, "documents": indexed}
