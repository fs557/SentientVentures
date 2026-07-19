"""Native-first, provenance-preserving PDF text extraction."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any


class PdfExtractionError(RuntimeError):
    """A PDF cannot safely be used by the processing pipeline."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page: int
    text: str
    method: str
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentExtraction:
    document_id: str
    page_count: int
    pages: tuple[ExtractedPage, ...]
    native_pages: tuple[int, ...]
    ocr_pages: tuple[int, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page_count": self.page_count,
            "pages": [
                {"page": item.page, "text": item.text, "method": item.method, "warning": item.warning}
                for item in self.pages
            ],
            "native_pages": list(self.native_pages),
            "ocr_pages": list(self.ocr_pages),
            "warnings": list(self.warnings),
        }


def _env_enabled() -> bool:
    return os.getenv("SV_OCR_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _threshold() -> int:
    raw = os.getenv("SV_OCR_TEXT_THRESHOLD", "40")
    try:
        value = int(raw)
    except ValueError:
        return 40
    return max(0, min(value, 10_000))


def _bound(name: str, default: int, *, minimum: int = 1, maximum: int = 100_000_000) -> int:
    """Read a defensive processing bound without making bad env values unsafe."""
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def ocr_available() -> bool:
    """Return false rather than leaking host details when Tesseract is absent."""
    if not _env_enabled():
        return False
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
    except (ImportError, OSError, RuntimeError):
        return False
    return True


def extract_pdf(
    path: Path,
    document_id: str,
    *,
    text_threshold: int | None = None,
    enable_ocr: bool | None = None,
) -> DocumentExtraction:
    """Extract native text first; OCR only pages with insufficient native text."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - declared environment dependency
        raise PdfExtractionError("PDF_ENGINE_UNAVAILABLE", "PDF extraction is unavailable") from exc

    threshold = _threshold() if text_threshold is None else max(0, text_threshold)
    may_ocr = _env_enabled() if enable_ocr is None else enable_ocr
    max_pages = _bound("SV_MAX_PDF_PAGES", 100, maximum=10_000)
    max_dimension = _bound("SV_MAX_PDF_PAGE_DIMENSION_POINTS", 14_400)
    max_text_bytes = _bound("SV_MAX_PDF_TEXT_BYTES", 5 * 1024 * 1024)
    max_ocr_pages = _bound("SV_MAX_OCR_PAGES", 20, minimum=0, maximum=10_000)
    max_ocr_pixels = _bound("SV_MAX_OCR_PIXELS", 16_000_000)
    try:
        document = fitz.open(path)
    except (fitz.FileDataError, OSError, RuntimeError) as exc:
        raise PdfExtractionError("CORRUPT_PDF", "Uploaded PDF cannot be read") from exc
    try:
        if document.needs_pass:
            raise PdfExtractionError("ENCRYPTED_PDF", "Encrypted PDFs are not supported")
        page_count = document.page_count
        if page_count < 1:
            raise PdfExtractionError("CORRUPT_PDF", "PDF has no pages")
        if page_count > max_pages:
            raise PdfExtractionError("PDF_PAGE_LIMIT_EXCEEDED", "PDF has too many pages")
        pages: list[ExtractedPage] = []
        native_pages: list[int] = []
        ocr_pages: list[int] = []
        warnings: list[str] = []
        ocr_ready = may_ocr and ocr_available()
        extracted_text_bytes = 0
        ocr_attempts = 0
        for number in range(1, page_count + 1):
            page = document.load_page(number - 1)
            rect = page.rect
            if rect.width <= 0 or rect.height <= 0 or rect.width > max_dimension or rect.height > max_dimension:
                raise PdfExtractionError("PDF_PAGE_DIMENSIONS_EXCEEDED", "PDF page dimensions exceed the configured limit")
            native_text = page.get_text("text").strip()
            extracted_text_bytes += len(native_text.encode("utf-8"))
            if extracted_text_bytes > max_text_bytes:
                raise PdfExtractionError("PDF_TEXT_LIMIT_EXCEEDED", "Extracted PDF text exceeds the configured limit")
            if len(native_text) >= threshold:
                pages.append(ExtractedPage(number, native_text, "native"))
                native_pages.append(number)
                continue
            if not may_ocr:
                warning = f"OCR_DISABLED:p{number}"
                pages.append(ExtractedPage(number, native_text, "native", warning))
                native_pages.append(number)
                warnings.append(warning)
                continue
            if not ocr_ready:
                warning = f"OCR_UNAVAILABLE:p{number}"
                pages.append(ExtractedPage(number, native_text, "native", warning))
                native_pages.append(number)
                warnings.append(warning)
                continue
            if ocr_attempts >= max_ocr_pages:
                raise PdfExtractionError("OCR_PAGE_LIMIT_EXCEEDED", "PDF requires OCR on too many pages")
            ocr_attempts += 1
            try:
                # At 2x rasterization, projected pixels are determined by the
                # page rectangle.  Check before get_pixmap allocates an image.
                projected_width = int(rect.width * 2 + 0.999999)
                projected_height = int(rect.height * 2 + 0.999999)
                if projected_width * projected_height > max_ocr_pixels:
                    raise PdfExtractionError("OCR_IMAGE_LIMIT_EXCEEDED", "OCR image exceeds the configured limit")
                import pytesseract
                from PIL import Image

                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                ocr_text = pytesseract.image_to_string(image).strip()
            except PdfExtractionError:
                raise
            except (OSError, RuntimeError) as exc:
                warning = f"OCR_FAILED:p{number}"
                pages.append(ExtractedPage(number, native_text, "native", warning))
                native_pages.append(number)
                warnings.append(warning)
                continue
            final_text = ocr_text or native_text
            extracted_text_bytes += len(ocr_text.encode("utf-8"))
            if extracted_text_bytes > max_text_bytes:
                raise PdfExtractionError("PDF_TEXT_LIMIT_EXCEEDED", "Extracted PDF text exceeds the configured limit")
            pages.append(ExtractedPage(number, final_text, "ocr"))
            ocr_pages.append(number)
        return DocumentExtraction(document_id, page_count, tuple(pages), tuple(native_pages), tuple(ocr_pages), tuple(warnings))
    finally:
        document.close()
