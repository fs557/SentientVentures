"""Small deterministic fact extractor with strict source provenance."""
from __future__ import annotations

from dataclasses import dataclass
import math
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
    extraction_list = list(extractions)
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
    for extraction in extraction_list:
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
    document_roles = {
        item.get("id"): item.get("role")
        for item in submission.get("source_documents", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for extraction in extraction_list:
        subject = "founder" if document_roles.get(extraction.document_id) == "cv" else "company"
        field = "founder.source_excerpt" if subject == "founder" else "company.source_excerpt"
        for page in extraction.pages:
            text = " ".join(page.text.split()).strip()
            if not text:
                continue
            count += 1
            records.append(_fact(
                f"fact.source.{count}", subject, field, text,
                extraction.document_id, page.page,
            ))
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


def _number(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(?<!\d)(\d[\d.,\s]*\d|\d)\s*(k|m|thousand|million)?\b", value, flags=re.IGNORECASE)
    if not match:
        return None
    raw = re.sub(r"\s", "", match.group(1))
    separators = [index for index, character in enumerate(raw) if character in ".,"]
    if len(separators) == 1 and len(raw) - separators[0] - 1 in {1, 2}:
        raw = raw.replace(",", ".")
    else:
        raw = raw.replace(",", "").replace(".", "")
    try:
        parsed = float(raw)
    except ValueError:
        return None
    multiplier = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000}.get((match.group(2) or "").lower(), 1)
    parsed *= multiplier
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def investment_terms(records: Iterable[FactRecord]) -> dict[str, object]:
    """Derive contract-shaped terms only from explicit, mutually consistent facts."""
    facts = {record.field: record.value for record in records if record.status == "fact"}
    requested = facts.get("investment.requested")
    valuation = facts.get("company.valuation")
    amount = _number(requested)
    pre_money = _number(valuation)
    equity = _number(facts.get("investment.equity_offered"))
    currencies = {
        match.group(1).upper()
        for value in (requested, valuation)
        if isinstance(value, str) and (match := re.search(r"\b([A-Za-z]{3})\b", value))
    }
    currency = next(iter(currencies)) if len(currencies) == 1 else None
    post_money = pre_money + amount if pre_money is not None and amount is not None else None
    implied = amount / (equity / 100) if amount is not None and equity is not None and equity > 0 else None
    if post_money is not None and implied is not None and not math.isclose(post_money, implied, rel_tol=1e-9, abs_tol=1e-6):
        implied = None
    return {
        "amount": amount,
        "currency": currency,
        "equityPercentage": equity,
        "preMoneyValuation": pre_money,
        "postMoneyValuation": post_money,
        "impliedValuation": implied,
        "useOfFunds": [],
    }
