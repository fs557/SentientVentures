"""Small deterministic fact extractor with strict source provenance."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Literal

from .pdf_extract import DocumentExtraction

FactStatus = Literal["fact", "inference", "missing_information"]
_DIRECT_FIELDS = (
    ("investment.requested", "investment", r"(?:investment requested|funding sought|raising)\s*[:\-]?\s*([^\n]{1,120})"),
    ("investment.equity_offered", "investment", r"(?:equity offered|equity)\s*[:\-]?\s*([^\n]{1,80})"),
    ("financial.current_revenue", "financial", r"(?:current revenue|revenue)\s*[:\-]?\s*([^\n]{1,120})"),
    ("financial.current_profit_loss", "financial", r"(?:profit|loss|ebitda)\s*[:\-]?\s*([^\n]{1,120})"),
    ("company.valuation", "company", r"(?:valuation|pre-money)\s*[:\-]?\s*([^\n]{1,120})"),
)


@dataclass(frozen=True, slots=True)
class FactRecord:
    id: str
    subject: Literal["company", "founder", "investment", "market", "financial"]
    field: str
    value: str | int | float | bool | list[str] | None
    status: FactStatus
    evidence: tuple[dict[str, Any], ...]
    source_document_ids: tuple[str, ...]
    missing_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"id": self.id, "subject": self.subject, "field": self.field,
            "value": self.value, "status": self.status, "evidence": list(self.evidence),
            "sourceDocumentIds": list(self.source_document_ids)}
        if self.missing_reason is not None:
            result["missingReason"] = self.missing_reason
        return result


def _fact(identifier: str, subject: Literal["company", "founder", "investment", "market", "financial"], field: str,
          value: str, document_id: str, page: int) -> FactRecord:
    evidence = {"kind": "fact", "documentId": document_id, "page": page, "text": value}
    return FactRecord(identifier, subject, field, value, "fact", (evidence,), (document_id,))


def extract_facts(submission: dict[str, Any], extractions: Iterable[DocumentExtraction]) -> list[FactRecord]:
    """Create only direct facts and explicit missing records, never guessed values."""
    records: list[FactRecord] = []
    company_name = submission.get("display_name")
    if isinstance(company_name, str) and company_name:
        records.append(FactRecord("fact.company_name", "company", "company.name", company_name, "fact",
            ({"kind": "fact", "documentId": "submission", "text": "Company name supplied at submission."},), ("submission",)))
    founder_name = submission.get("submission", {}).get("founder_name") if isinstance(submission.get("submission"), dict) else None
    if isinstance(founder_name, str) and founder_name:
        records.append(FactRecord("fact.founder_name", "founder", "founder.name", founder_name, "fact",
            ({"kind": "fact", "documentId": "submission", "text": "Founder name supplied at submission."},), ("submission",)))
    found_fields: set[str] = set()
    count = 0
    for extraction in extractions:
        for page in extraction.pages:
            for field, subject, pattern in _DIRECT_FIELDS:
                match = re.search(pattern, page.text, flags=re.IGNORECASE)
                if not match or field in found_fields:
                    continue
                value = match.group(1).strip(" .:-")
                if value:
                    count += 1
                    records.append(_fact(f"fact.extracted.{count}", subject, field, value, extraction.document_id, page.page))
                    found_fields.add(field)
    for field, subject in (("investment.requested", "investment"), ("investment.equity_offered", "investment"),
                           ("financial.current_revenue", "financial"), ("company.valuation", "company")):
        if field not in found_fields:
            count += 1
            records.append(FactRecord(f"fact.missing.{count}", subject, field, None, "missing_information", (), (),
                "Not provided in submitted material."))
    validate_facts(records)
    return records


def validate_facts(records: Iterable[FactRecord]) -> None:
    for record in records:
        if record.status == "missing_information":
            if record.value is not None or record.evidence or record.source_document_ids or not record.missing_reason:
                raise ValueError("Missing information records must be null and uncited")
        elif not record.evidence or not record.source_document_ids:
            raise ValueError("Facts require source provenance")
