"""Focused Phase 4 extraction, facts, and in-process worker tests."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

fitz = pytest.importorskip("fitz")

from src.core.facts import FactRecord, extract_facts, investment_terms
from src.core.pdf_extract import PdfExtractionError, extract_pdf
from src.core.submissions import PendingDocument, SubmissionRepository
from src.providers.council import DeterministicFakeProvider
from src.workers.queue import ProcessingWorker


def _pdf(path: Path, text: str = "Revenue: EUR 1m\nInvestment requested: EUR 500k", *, pages: int = 1, width: float = 595, height: float = 842) -> None:
    document = fitz.open()
    for _ in range(pages):
        page = document.new_page(width=width, height=height)
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_native_extraction_preserves_page_provenance(tmp_path: Path) -> None:
    path = tmp_path / "native.pdf"
    _pdf(path)
    result = extract_pdf(path, "doc_native", enable_ocr=False)
    assert result.native_pages == (1,)
    assert result.ocr_pages == ()
    assert result.pages[0].page == 1
    assert "Revenue" in result.pages[0].text


def test_corrupt_and_encrypted_pdfs_fail_safely(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-not-a-real-pdf")
    with pytest.raises(PdfExtractionError, match="cannot be read") as corrupt_error:
        extract_pdf(corrupt, "doc_bad")
    assert corrupt_error.value.code == "CORRUPT_PDF"

    plain = tmp_path / "plain.pdf"
    encrypted = tmp_path / "encrypted.pdf"
    _pdf(plain)
    document = fitz.open(plain)
    document.save(encrypted, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    with pytest.raises(PdfExtractionError, match="Encrypted") as encrypted_error:
        extract_pdf(encrypted, "doc_encrypted")
    assert encrypted_error.value.code == "ENCRYPTED_PDF"


def test_low_text_ocr_unavailable_is_observable_without_invented_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "scanned.pdf"
    _pdf(path, "")
    monkeypatch.setattr("src.core.pdf_extract.ocr_available", lambda: False)
    result = extract_pdf(path, "doc_scan", text_threshold=20, enable_ocr=True)
    assert result.ocr_pages == ()
    assert result.pages[0].text == ""
    assert result.pages[0].warning == "OCR_UNAVAILABLE:p1"
    assert "OCR_UNAVAILABLE:p1" in result.warnings


def test_pdf_processing_bounds_reject_many_small_pages_dimensions_text_and_ocr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    many_pages = tmp_path / "many-pages.pdf"
    _pdf(many_pages, "", pages=3)
    monkeypatch.setenv("SV_MAX_PDF_PAGES", "2")
    with pytest.raises(PdfExtractionError, match="too many pages") as error:
        extract_pdf(many_pages, "doc_many", enable_ocr=False)
    assert error.value.code == "PDF_PAGE_LIMIT_EXCEEDED"

    oversized = tmp_path / "oversized.pdf"
    _pdf(oversized, "", width=1000, height=1000)
    monkeypatch.setenv("SV_MAX_PDF_PAGES", "10")
    monkeypatch.setenv("SV_MAX_PDF_PAGE_DIMENSION_POINTS", "500")
    with pytest.raises(PdfExtractionError, match="dimensions") as error:
        extract_pdf(oversized, "doc_large", enable_ocr=False)
    assert error.value.code == "PDF_PAGE_DIMENSIONS_EXCEEDED"

    text_heavy = tmp_path / "text-heavy.pdf"
    _pdf(text_heavy, "A" * 200)
    monkeypatch.setenv("SV_MAX_PDF_PAGE_DIMENSION_POINTS", "2000")
    monkeypatch.setenv("SV_MAX_PDF_TEXT_BYTES", "50")
    with pytest.raises(PdfExtractionError, match="text") as error:
        extract_pdf(text_heavy, "doc_text", enable_ocr=False)
    assert error.value.code == "PDF_TEXT_LIMIT_EXCEEDED"

    monkeypatch.setenv("SV_MAX_PDF_TEXT_BYTES", "10000")
    monkeypatch.setenv("SV_MAX_OCR_PAGES", "0")
    monkeypatch.setattr("src.core.pdf_extract.ocr_available", lambda: True)
    with pytest.raises(PdfExtractionError, match="OCR") as error:
        extract_pdf(many_pages, "doc_ocr", enable_ocr=True)
    assert error.value.code == "OCR_PAGE_LIMIT_EXCEEDED"


def test_ocr_pixel_limit_is_checked_before_pixmap_allocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "scan.pdf"
    _pdf(path, "", width=100, height=100)
    monkeypatch.setenv("SV_MAX_OCR_PIXELS", "1")
    monkeypatch.setattr("src.core.pdf_extract.ocr_available", lambda: True)
    with pytest.raises(PdfExtractionError) as error:
        extract_pdf(path, "doc_scan", text_threshold=1, enable_ocr=True)
    assert error.value.code == "OCR_IMAGE_LIMIT_EXCEEDED"


def test_fact_records_have_document_provenance_and_explicit_missing_information(tmp_path: Path) -> None:
    path = tmp_path / "deck.pdf"
    _pdf(path)
    extraction = extract_pdf(path, "doc_deck", enable_ocr=False)
    facts = extract_facts({"display_name": "Aster Labs", "submission": {"founder_name": "Ada Founder"}}, [extraction])
    revenue = next(item for item in facts if item.field == "financial.current_revenue")
    assert revenue.status == "fact"
    assert revenue.evidence[0]["documentId"] == "doc_deck"
    assert revenue.evidence[0]["page"] == 1
    missing = next(item for item in facts if item.field == "investment.equity_offered")
    assert missing.status == "missing_information"
    assert missing.value is None and not missing.evidence and missing.missing_reason


def test_investment_terms_accept_us_and_german_grouping() -> None:
    def fact(identifier: str, field: str, value: str) -> FactRecord:
        subject = "investment" if field.startswith("investment.") else "company"
        return FactRecord(identifier, subject, field, value, "fact", (
            {"kind": "fact", "documentId": "doc_550e8400-e29b-41d4-a716-446655440000", "page": 1, "text": value},
        ), ("doc_550e8400-e29b-41d4-a716-446655440000",))  # type: ignore[arg-type]

    terms = investment_terms([
        fact("amount", "investment.requested", "EUR 100.000"),
        fact("equity", "investment.equity_offered", "1%"),
        fact("valuation", "company.valuation", "EUR 9,900,000"),
    ])
    assert terms == {
        "amount": 100000.0, "currency": "EUR", "equityPercentage": 1.0,
        "preMoneyValuation": 9900000.0, "postMoneyValuation": 10000000.0,
        "impliedValuation": 10000000.0, "useOfFunds": [],
    }


def test_worker_persists_stage_artifacts_and_marks_corrupt_documents_failed(tmp_path: Path) -> None:
    repository = SubmissionRepository(tmp_path / "companies")
    upload = repository.create_temp_path()
    _pdf(upload)
    response, _ = repository.persist_submission(
        request_hash="test", idempotency_key=str(uuid4()), company_name="Worker Labs", founder_name="Ada Founder",
        founder_email="ada@example.test", linkedin_url="https://linkedin.example.test/ada", github_url=None,
        website_url=None, documents=[PendingDocument("pitch_deck", "deck.pdf", "application/pdf", upload, upload.stat().st_size, "a" * 64)],
    )
    slug = response["company"]["slug"]
    worker = ProcessingWorker(repository)
    worker._process_sync(slug)
    job = repository.get_job(slug)
    assert job["state"] == "running" and job["stage"] == "council_preparing" and job["progress"] == 55
    root = tmp_path / "companies" / slug / "extracted"
    assert (root / "document-text.json").exists()
    assert (root / "document-index.json").exists()
    assert (root / "company-facts.json").exists()
    metadata = json.loads((tmp_path / "companies" / slug / "metadata.json").read_text())
    assert metadata["source_documents"][0]["extraction"]["native_pages"] == [1]

    bad = repository.create_temp_path()
    bad.write_bytes(b"%PDF-corrupt")
    bad_response, _ = repository.persist_submission(
        request_hash="bad", idempotency_key=str(uuid4()), company_name="Broken Labs", founder_name="Ada Founder",
        founder_email="ada@example.test", linkedin_url="https://linkedin.example.test/ada", github_url=None,
        website_url=None, documents=[PendingDocument("pitch_deck", "bad.pdf", "application/pdf", bad, bad.stat().st_size, "b" * 64)],
    )
    worker._process_sync(bad_response["company"]["slug"])
    failed = repository.get_job(bad_response["company"]["slug"])
    assert failed["state"] == "failed"
    assert failed["error"] == {"code": "CORRUPT_PDF", "message": "Document processing could not be completed"}


def test_deterministic_provider_pipeline_reaches_ready(tmp_path: Path) -> None:
    repository = SubmissionRepository(tmp_path / "companies")
    upload = repository.create_temp_path()
    _pdf(upload)
    response, _ = repository.persist_submission(
        request_hash="ready", idempotency_key=str(uuid4()), company_name="Ready Labs", founder_name="Ada Founder",
        founder_email="ada@example.test", linkedin_url="https://linkedin.example.test/ada", github_url=None,
        website_url=None, documents=[PendingDocument("pitch_deck", "deck.pdf", "application/pdf", upload, upload.stat().st_size, "c" * 64)],
    )
    worker = ProcessingWorker(repository, DeterministicFakeProvider())
    worker._process_sync(str(response["company"]["slug"]))
    assert repository.get_job(str(response["company"]["slug"]))["state"] == "ready"
