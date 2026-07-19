"""Strict serializer and deliberately narrow parser for v1 evaluation Markdown."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Iterable, Mapping

import yaml

from .registry import CATEGORIES, Category, REGISTRY_BY_ID, entries_for_category
from .scoring import PORTFOLIO_UNAVAILABLE_IDS, is_valid_score

_FRONT_MATTER_KEYS = ("schema_version", "registry_version", "company", "slug", "category", "generated_at", "source_documents")
_SECTION_NAMES = ("Assessment", "Positive Arguments", "Negative Arguments and Risks", "Evidence", "Missing Information", "Source References")
_HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DOCUMENT_ID = re.compile(r"^doc_[0-9a-fA-F-]{36}$")
_SCORE = re.compile(r"^(?:[1-9][0-9]?|100)$")
_HEADING = re.compile(r"^## ([a-z]+\.[a-z0-9_]+) \| (.+)$")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    severity: str = "error"


@dataclass(slots=True)
class EvidenceReference:
    kind: str
    document_id: str
    text: str
    page: int | None = None
    section: str | None = None


@dataclass(slots=True)
class EvaluationItem:
    id: str
    category: Category
    title: str
    score: int | None
    confidence: int | None
    assessment: str
    positive_arguments: list[str]
    negative_arguments: list[str]
    evidence: list[EvidenceReference]
    missing_information: list[str]
    source_references: list[EvidenceReference]
    validation_errors: list[ValidationIssue] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationDocument:
    schema_version: int
    registry_version: int
    company: str
    slug: str
    category: Category
    generated_at: str
    source_documents: list[str]
    items: list[EvaluationItem]
    validation_errors: list[ValidationIssue] = field(default_factory=list)


@dataclass(slots=True)
class ParseResult:
    document: EvaluationDocument | None
    errors: list[ValidationIssue]

    @property
    def is_valid(self) -> bool:
        return self.document is not None and not self.errors


def document_to_contract_dict(document: EvaluationDocument) -> dict[str, object]:
    """Return the frozen camelCase normalized shape for API adapters."""
    def issue(value: ValidationIssue) -> dict[str, str]:
        return {"code": value.code, "path": value.path, "message": value.message, "severity": value.severity}
    def reference(value: EvidenceReference) -> dict[str, object]:
        result: dict[str, object] = {"kind": value.kind, "documentId": value.document_id, "text": value.text}
        if value.page is not None: result["page"] = value.page
        if value.section is not None: result["section"] = value.section
        return result
    return {
        "schemaVersion": document.schema_version, "registryVersion": document.registry_version,
        "company": document.company, "slug": document.slug, "category": document.category,
        "generatedAt": document.generated_at, "sourceDocuments": document.source_documents,
        "items": [{
            "id": item.id, "category": item.category, "title": item.title, "score": item.score,
            "confidence": item.confidence, "assessment": item.assessment,
            "positiveArguments": item.positive_arguments, "negativeArguments": item.negative_arguments,
            "evidence": [reference(value) for value in item.evidence],
            "missingInformation": item.missing_information,
            "sourceReferences": [reference(value) for value in item.source_references],
            "validationErrors": [issue(value) for value in item.validation_errors],
        } for item in document.items],
        "validationErrors": [issue(value) for value in document.validation_errors],
    }


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise yaml.YAMLError(f"duplicate front matter key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _issue(errors: list[ValidationIssue], code: str, path: str, message: str) -> None:
    errors.append(ValidationIssue(code, path, message))


def _as_document(value: EvaluationDocument | Mapping[str, Any]) -> EvaluationDocument:
    if isinstance(value, EvaluationDocument):
        return value
    try:
        items = [EvaluationItem(
            id=item["id"], category=item["category"], title=item["title"], score=item.get("score"),
            confidence=item.get("confidence"), assessment=item["assessment"],
            positive_arguments=list(item["positiveArguments"]), negative_arguments=list(item["negativeArguments"]),
            evidence=[EvidenceReference(e["kind"], e["documentId"], e["text"], e.get("page"), e.get("section")) for e in item["evidence"]],
            missing_information=list(item.get("missingInformation", [])),
            source_references=[EvidenceReference(e["kind"], e["documentId"], e["text"], e.get("page"), e.get("section")) for e in item["sourceReferences"]],
        ) for item in value["items"]]
        return EvaluationDocument(value["schemaVersion"], value["registryVersion"], value["company"], value["slug"], value["category"], value["generatedAt"], list(value["sourceDocuments"]), items)
    except (KeyError, TypeError) as exc:
        raise ValueError("Evaluation document does not match the v1 serializer input") from exc


def _validate_document(document: EvaluationDocument, *, expected_slug: str | None = None, expected_category: Category | None = None) -> list[ValidationIssue]:
    errors: list[ValidationIssue] = []
    if (not isinstance(document.schema_version, int) or isinstance(document.schema_version, bool) or document.schema_version != 1
            or not isinstance(document.registry_version, int) or isinstance(document.registry_version, bool) or document.registry_version != 1):
        _issue(errors, "VERSION_INVALID", "/", "schema and registry versions must both be 1")
    if not document.company.strip():
        _issue(errors, "COMPANY_INVALID", "/company", "company must not be empty")
    if not _SLUG.fullmatch(document.slug):
        _issue(errors, "SLUG_INVALID", "/slug", "slug must use lowercase hyphenated ASCII")
    if expected_slug is not None and document.slug != expected_slug:
        _issue(errors, "SLUG_MISMATCH", "/slug", "document slug does not match expected slug")
    if document.category not in CATEGORIES:
        _issue(errors, "CATEGORY_INVALID", "/category", "unsupported category")
        return errors
    if expected_category is not None and document.category != expected_category:
        _issue(errors, "CATEGORY_MISMATCH", "/category", "document category does not match expected category")
    try:
        parsed_time = datetime.fromisoformat(document.generated_at.replace("Z", "+00:00"))
        if parsed_time.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        _issue(errors, "TIMESTAMP_INVALID", "/generatedAt", "generated_at must be an ISO-8601 UTC timestamp")
    if len(set(document.source_documents)) != len(document.source_documents) or any(not _DOCUMENT_ID.fullmatch(doc) for doc in document.source_documents):
        _issue(errors, "SOURCE_DOCUMENTS_INVALID", "/sourceDocuments", "source documents must be unique document IDs")
    expected = entries_for_category(document.category)
    if len(document.items) != len(expected):
        _issue(errors, "ITEM_COUNT_INVALID", "/items", "document does not contain every category question")
    for index, (item, entry) in enumerate(zip(document.items, expected)):
        path = f"/items/{index}"
        if (item.id, item.category, item.title) != (entry.id, entry.category, entry.title):
            _issue(errors, "REGISTRY_MISMATCH", path, "item ID, category, title, or order differs from registry")
        if item.score is not None and not is_valid_score(item.score):
            _issue(errors, "SCORE_INVALID", path + "/score", "score must be an integer from 1 through 100")
        unavailable = item.id in PORTFOLIO_UNAVAILABLE_IDS
        if (item.score is None and item.category != "home" and not unavailable
                and "Sufficient criterion-specific evidence was not provided." not in item.missing_information):
            _issue(errors, "SCORE_REQUIRED", path + "/score", "a scored criterion requires an integer score")
        if item.confidence is not None and not is_valid_score(item.confidence):
            _issue(errors, "CONFIDENCE_INVALID", path + "/confidence", "confidence must be an integer from 1 through 100")
        if not item.assessment.strip() or not item.positive_arguments or not item.negative_arguments or not item.evidence or not item.source_references:
            _issue(errors, "SECTION_EMPTY", path, "all required item sections must contain content")
        for reference in [*item.evidence, *item.source_references]:
            if reference.kind not in {"fact", "inference"} or (reference.document_id != "submission" and reference.document_id not in document.source_documents) or not reference.text.strip() or (reference.page is not None and reference.page < 1):
                _issue(errors, "EVIDENCE_INVALID", path, "evidence must use a declared document ID or submission")
    return errors


def _reference_to_line(reference: EvidenceReference, *, include_kind: bool = True) -> str:
    parts = [reference.kind, reference.document_id] if include_kind else [reference.document_id]
    if reference.page is not None:
        parts.append(f"p. {reference.page}")
    if reference.section:
        parts.append(reference.section)
    parts.append(reference.text)
    return "- " + " | ".join(parts)


def serialize_evaluation_document(value: EvaluationDocument | Mapping[str, Any]) -> str:
    """Serialize a fully valid document to the canonical LF-terminated v1 grammar."""
    document = _as_document(value)
    errors = _validate_document(document)
    if errors:
        raise ValueError("Cannot serialize invalid evaluation document: " + "; ".join(issue.code for issue in errors))
    front_matter = {
        "schema_version": 1, "registry_version": 1, "company": document.company, "slug": document.slug,
        "category": document.category, "generated_at": document.generated_at, "source_documents": document.source_documents,
    }
    lines = ["---", yaml.safe_dump(front_matter, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip(), "---", "", f"# {document.category.title()} Evaluation", ""]
    for item in document.items:
        lines.extend([f"## {item.id} | {item.title}", "", f"**Score:** {item.score if item.score is not None else 'N/A'}"])
        if item.confidence is not None:
            lines.append(f"**Confidence:** {item.confidence}")
        lines.extend(["", "### Assessment", item.assessment.strip(), "", "### Positive Arguments"])
        lines.extend(f"- {argument}" for argument in item.positive_arguments)
        lines.extend(["", "### Negative Arguments and Risks"])
        lines.extend(f"- {argument}" for argument in item.negative_arguments)
        lines.extend(["", "### Evidence"])
        lines.extend(_reference_to_line(reference) for reference in item.evidence)
        lines.extend(["", "### Missing Information"])
        lines.extend(f"- {item_text}" for item_text in item.missing_information or ["No material missing information was identified."])
        lines.extend(["", "### Source References"])
        # Source references are evidence too.  Keeping their kind avoids
        # silently turning an inference into a fact during a round-trip.
        lines.extend(_reference_to_line(reference) for reference in item.source_references)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _parse_reference(line: str, source_documents: set[str], *, allow_implicit_fact: bool) -> EvidenceReference | None:
    if not line.startswith("- "):
        return None
    parts = [part.strip() for part in line[2:].split("|")]
    # Accept legacy source-reference lines without a kind, but the serializer
    # always writes one so kind and section survive a round-trip.
    if allow_implicit_fact and len(parts) >= 2 and parts[0] not in {"fact", "inference"}:
        parts.insert(0, "fact")
    if len(parts) < 3 or parts[0] not in {"fact", "inference"}:
        return None
    kind, document_id, *remaining = parts
    if document_id != "submission" and document_id not in source_documents:
        return None
    page: int | None = None
    section: str | None = None
    if len(remaining) >= 2 and re.fullmatch(r"p\. [1-9][0-9]*", remaining[0]):
        page = int(remaining.pop(0)[3:])
    if len(remaining) >= 2 and remaining[0].startswith("section "):
        section = remaining.pop(0)
    text = " | ".join(remaining).strip()
    return EvidenceReference(kind, document_id, text, page, section) if text else None


def parse_evaluation_document(markdown: str, expected_slug: str, expected_category: Category) -> ParseResult:
    """Parse exactly the supported grammar and return all validation issues found."""
    errors: list[ValidationIssue] = []
    if "\r" in markdown:
        _issue(errors, "LINE_ENDING_INVALID", "/", "documents must use LF line endings")
    if not markdown.endswith("\n"):
        _issue(errors, "FINAL_NEWLINE_MISSING", "/", "document must end with one newline")
    elif markdown.endswith("\n\n"):
        _issue(errors, "FINAL_NEWLINE_INVALID", "/", "document must have exactly one final newline")
    if _HTML.search(markdown):
        _issue(errors, "RAW_HTML_FORBIDDEN", "/", "raw HTML is forbidden")
    lines = markdown.splitlines()
    if not lines or lines[0] != "---":
        _issue(errors, "FRONT_MATTER_MISSING", "/", "document must start with YAML front matter")
        return ParseResult(None, errors)
    try:
        close = lines.index("---", 1)
    except ValueError:
        _issue(errors, "FRONT_MATTER_MISSING", "/", "front matter closing delimiter is missing")
        return ParseResult(None, errors)
    try:
        front_matter = yaml.load("\n".join(lines[1:close]), Loader=_UniqueKeyLoader)
    except yaml.YAMLError:
        _issue(errors, "FRONT_MATTER_INVALID", "/", "front matter is not valid unique-key YAML")
        return ParseResult(None, errors)
    if not isinstance(front_matter, dict) or set(front_matter) != set(_FRONT_MATTER_KEYS):
        _issue(errors, "FRONT_MATTER_KEYS_INVALID", "/", "front matter keys must exactly match the v1 contract")
        return ParseResult(None, errors)

    expected_types: dict[str, type[object]] = {
        "schema_version": int,
        "registry_version": int,
        "company": str,
        "slug": str,
        "category": str,
        "generated_at": str,
        "source_documents": list,
    }
    invalid_value_types = False
    for key, expected_type in expected_types.items():
        value = front_matter[key]
        if not isinstance(value, expected_type) or (
            expected_type is int and isinstance(value, bool)
        ):
            _issue(errors, "FRONT_MATTER_VALUE_INVALID", f"/{key}", f"{key} must be a {expected_type.__name__}")
            invalid_value_types = True
    source_documents_value = front_matter["source_documents"]
    if isinstance(source_documents_value, list) and not all(isinstance(value, str) for value in source_documents_value):
        _issue(errors, "SOURCE_DOCUMENTS_INVALID", "/source_documents", "source_documents must be a list of IDs")
        invalid_value_types = True
    if invalid_value_types:
        return ParseResult(None, errors)

    category = front_matter["category"]
    if category not in CATEGORIES:
        _issue(errors, "CATEGORY_INVALID", "/category", "unsupported category")
        return ParseResult(None, errors)
    source_documents = front_matter["source_documents"]
    document = EvaluationDocument(
        front_matter["schema_version"], front_matter["registry_version"], front_matter["company"],
        front_matter["slug"], category, front_matter["generated_at"], source_documents, [],
    )
    body = lines[close + 1:]
    while body and not body[0].strip():
        body.pop(0)
    if not body or body.pop(0) != f"# {category.title()} Evaluation":
        _issue(errors, "DOCUMENT_HEADING_INVALID", "/", "document title must match category")
    while body and not body[0].strip():
        body.pop(0)
    index = 0
    seen: set[str] = set()
    expected_entries = entries_for_category(category)
    while index < len(body):
        heading = _HEADING.match(body[index])
        if not heading:
            _issue(errors, "PREAMBLE_OR_HEADING_INVALID", f"/body/{index}", "expected an exact question heading")
            index += 1
            continue
        item_id, title = heading.groups()
        index += 1
        entry = REGISTRY_BY_ID.get(item_id)
        if item_id in seen:
            _issue(errors, "DUPLICATE_ITEM", f"/items/{item_id}", "question ID appears more than once")
        seen.add(item_id)
        if entry is None or entry.category != category or entry.title != title:
            _issue(errors, "REGISTRY_MISMATCH", f"/items/{item_id}", "heading does not match this category registry")
        while index < len(body) and not body[index].strip():
            index += 1
        score: int | None = None
        confidence: int | None = None
        if index >= len(body) or not body[index].startswith("**Score:** "):
            _issue(errors, "SCORE_MISSING", f"/items/{item_id}/score", "Score line is required")
        else:
            raw_score = body[index][11:].strip(); index += 1
            if _SCORE.fullmatch(raw_score): score = int(raw_score)
            elif raw_score != "N/A": _issue(errors, "SCORE_INVALID", f"/items/{item_id}/score", "score must be 1..100 or N/A")
        if index < len(body) and body[index].startswith("**Confidence:** "):
            raw_confidence = body[index][16:].strip(); index += 1
            if _SCORE.fullmatch(raw_confidence): confidence = int(raw_confidence)
            elif raw_confidence != "N/A": _issue(errors, "CONFIDENCE_INVALID", f"/items/{item_id}/confidence", "confidence must be 1..100 or N/A")
        sections: dict[str, list[str]] = {}
        for section_name in _SECTION_NAMES:
            while index < len(body) and not body[index].strip(): index += 1
            if index >= len(body) or body[index] != f"### {section_name}":
                _issue(errors, "SECTION_MISSING_OR_REORDERED", f"/items/{item_id}", f"expected {section_name}")
                sections[section_name] = []
                continue
            index += 1; content: list[str] = []
            while index < len(body) and not body[index].startswith("### ") and not body[index].startswith("## "):
                content.append(body[index]); index += 1
            while content and not content[-1].strip(): content.pop()
            sections[section_name] = content
        def bullets(section: str) -> list[str]:
            values = [line[2:].strip() for line in sections[section] if line.startswith("- ") and line[2:].strip()]
            if not values: _issue(errors, "SECTION_EMPTY", f"/items/{item_id}/{section}", f"{section} needs at least one list item")
            if any(line.strip() and not line.startswith("- ") for line in sections[section]): _issue(errors, "SECTION_CONTENT_INVALID", f"/items/{item_id}/{section}", "list section must contain only bullets")
            return values
        assessment = "\n".join(line for line in sections["Assessment"] if line.strip()).strip()
        if not assessment: _issue(errors, "SECTION_EMPTY", f"/items/{item_id}/assessment", "Assessment must not be empty")
        evidence = [_parse_reference(line, set(source_documents), allow_implicit_fact=False) for line in sections["Evidence"] if line.strip()]
        source_refs = [_parse_reference(line, set(source_documents), allow_implicit_fact=True) for line in sections["Source References"] if line.strip()]
        if not evidence or any(reference is None for reference in evidence): _issue(errors, "EVIDENCE_INVALID", f"/items/{item_id}/evidence", "Evidence must contain valid references")
        if not source_refs or any(reference is None for reference in source_refs): _issue(errors, "EVIDENCE_INVALID", f"/items/{item_id}/sourceReferences", "Source references must contain valid references")
        document.items.append(EvaluationItem(item_id, category, title, score, confidence, assessment, bullets("Positive Arguments"), bullets("Negative Arguments and Risks"), [reference for reference in evidence if reference], bullets("Missing Information"), [reference for reference in source_refs if reference]))
    errors.extend(_validate_document(document, expected_slug=expected_slug, expected_category=expected_category))
    document.validation_errors = list(errors)
    for index, item in enumerate(document.items):
        item.validation_errors = [error for error in errors if error.path.startswith(f"/items/{index}") or error.path.startswith(f"/items/{item.id}")]
    return ParseResult(document, errors)
