"""Submission and job-status endpoints for the local founder portal."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import re
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import UploadFile
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ..core.submissions import PendingDocument, SubmissionRepository, SubmissionStorageError, request_digest

router = APIRouter(prefix="/api/v1", tags=["submissions"])

_EMAIL = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,63}$")
_PLAIN_TEXT = re.compile(r"^[^\x00-\x1f\x7f]{2,120}$")
_ALLOWED_FIELDS = frozenset({
    "company_name", "founder_name", "founder_email", "pitch_deck", "cv", "linkedin_url", "github_url",
    "website_url", "supporting_documents",
})


def _upload_limit(name: str, default: int) -> int:
    """Use a safe default when local configuration is absent or malformed."""
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, 1), 1024 * 1024 * 1024)


def _limits() -> tuple[int, int]:
    file_limit = _upload_limit("SV_MAX_FILE_BYTES", 25 * 1024 * 1024)
    aggregate_limit = _upload_limit("SV_MAX_AGGREGATE_FILE_BYTES", 75 * 1024 * 1024)
    return file_limit, aggregate_limit


class SubmissionBodyLimitMiddleware:
    """Bound submission bytes before Starlette's multipart parser sees them."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/v1/submissions":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        transfer_encoding = headers.get(b"transfer-encoding", b"").lower()
        _, limit = _limits()
        if b"chunked" in transfer_encoding or raw_length is None:
            await self._reject(send, 411, "LENGTH_REQUIRED", "Content-Length is required for uploads", "content_length")
            return
        try:
            declared = int(raw_length)
        except ValueError:
            await self._reject(send, 400, "MALFORMED_MULTIPART", "Content-Length is invalid", "content_length")
            return
        if declared < 0:
            await self._reject(send, 400, "MALFORMED_MULTIPART", "Content-Length is invalid", "content_length")
            return
        if declared > limit:
            await self._reject(send, 413, "PAYLOAD_TOO_LARGE", "Upload exceeds the configured aggregate size limit", "content_length")
            return

        messages: list[Message] = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    await self._reject(send, 413, "PAYLOAD_TOO_LARGE", "Upload exceeds the configured aggregate size limit", "body_size")
                    return
                if not message.get("more_body", False):
                    break
        message_index = 0

        async def replay_receive() -> Message:
            nonlocal message_index
            if message_index < len(messages):
                message = messages[message_index]
                message_index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Send, status: int, code: str, message: str, detail_code: str) -> None:
        request_id = str(uuid4())
        body = JSONResponse(
            status_code=status,
            content={"error": {"code": code, "message": message,
                               "details": [{"path": "/", "code": detail_code, "message": message}],
                               "requestId": request_id}},
        ).body
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii")),
                                (b"x-request-id", request_id.encode("ascii"))]})
        await send({"type": "http.response.body", "body": body})


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobStatusModel(_Model):
    id: str
    companySlug: str
    state: str
    stage: str
    progress: int
    attempt: int
    repairCount: int
    updatedAt: str
    error: dict[str, object] | None
    retryAllowed: bool


class RetryResponseModel(_Model):
    id: str
    state: str
    attempt: int
    statusUrl: str


class ApiProblem(Exception):
    def __init__(self, status_code: int, code: str, message: str, *, path: str = "/", detail_code: str | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.path = path
        self.detail_code = detail_code or code


def _repository(request: Request) -> SubmissionRepository:
    repository = getattr(request.app.state, "submission_repository", None)
    if not isinstance(repository, SubmissionRepository):
        raise ApiProblem(503, "STORAGE_UNAVAILABLE", "Submission storage is unavailable")
    return repository


def _idempotency_key(value: str | None) -> str:
    if value is None:
        raise ApiProblem(422, "VALIDATION_ERROR", "An Idempotency-Key header is required", path="/headers/Idempotency-Key", detail_code="missing")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ApiProblem(422, "VALIDATION_ERROR", "Idempotency-Key must be a UUID", path="/headers/Idempotency-Key", detail_code="uuid") from exc


def _one_text(form: Any, name: str, *, required: bool = False) -> str | None:
    values = form.getlist(name)
    if len(values) > 1:
        raise ApiProblem(422, "VALIDATION_ERROR", "Duplicate form field", path=f"/{name}", detail_code="duplicate")
    if not values:
        if required:
            raise ApiProblem(422, "VALIDATION_ERROR", "Required form field is missing", path=f"/{name}", detail_code="missing")
        return None
    value = values[0]
    if not isinstance(value, str):
        raise ApiProblem(422, "VALIDATION_ERROR", "Expected a text field", path=f"/{name}", detail_code="type")
    return value.strip()


def _validate_text(name: str, value: str) -> str:
    if not _PLAIN_TEXT.fullmatch(value):
        raise ApiProblem(422, "VALIDATION_ERROR", "Text must be 2 to 120 plain characters", path=f"/{name}", detail_code="length")
    return value


def _validate_url(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or any(character.isspace() for character in value):
        raise ApiProblem(422, "VALIDATION_ERROR", "URL must use HTTPS", path=f"/{name}", detail_code="url")
    return value


async def _stage_pdf(upload: UploadFile, role: str, repository: SubmissionRepository, total: int, *, file_limit: int, aggregate_limit: int) -> PendingDocument:
    filename = upload.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise ApiProblem(415, "UNSUPPORTED_MEDIA_TYPE", "Documents must use a .pdf filename", path=f"/{role}", detail_code="extension")
    if upload.content_type != "application/pdf":
        raise ApiProblem(415, "UNSUPPORTED_MEDIA_TYPE", "Documents must declare application/pdf", path=f"/{role}", detail_code="content_type")
    temporary = repository.create_temp_path()
    digest = sha256()
    size = 0
    prefix = b""
    try:
        with temporary.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > file_limit or total + size > aggregate_limit:
                    raise ApiProblem(413, "PAYLOAD_TOO_LARGE", "Document upload exceeds the configured size limit", path=f"/{role}", detail_code="size")
                if len(prefix) < 5:
                    prefix += chunk[: 5 - len(prefix)]
                digest.update(chunk)
                handle.write(chunk)
        if prefix != b"%PDF-":
            raise ApiProblem(415, "UNSUPPORTED_MEDIA_TYPE", "Document does not have a PDF signature", path=f"/{role}", detail_code="magic")
        return PendingDocument(role, filename, upload.content_type, temporary, size, digest.hexdigest())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


async def _close_uploads(form: Any) -> None:
    """Release multipart spooled files even when validation rejects the envelope."""
    closed: set[int] = set()
    for _, value in form.multi_items():
        if isinstance(value, UploadFile) and id(value) not in closed:
            closed.add(id(value))
            await value.close()


@router.post("/submissions", status_code=202)
async def create_submission(
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    key = _idempotency_key(idempotency_key)
    repository = _repository(request)
    file_limit, aggregate_limit = _limits()
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise ApiProblem(400, "MALFORMED_MULTIPART", "Content-Length is invalid", detail_code="content_length") from exc
        if declared_length < 0:
            raise ApiProblem(400, "MALFORMED_MULTIPART", "Content-Length is invalid", detail_code="content_length")
        if declared_length > aggregate_limit:
            raise ApiProblem(413, "PAYLOAD_TOO_LARGE", "Upload exceeds the configured aggregate size limit", detail_code="content_length")
    try:
        # Restrict parser work before application-level validation.  The
        # streaming stage below remains authoritative for file/aggregate bytes.
        # Starlette versions used by this project expose file/field limits here;
        # byte limits are enforced by Content-Length and the streaming stage.
        form = await request.form(max_files=6, max_fields=8)
    except Exception as exc:
        raise ApiProblem(400, "MALFORMED_MULTIPART", "Multipart form data could not be read") from exc
    pending: list[PendingDocument] = []
    try:
        unknown = set(form.keys()) - _ALLOWED_FIELDS
        if unknown:
            raise ApiProblem(422, "VALIDATION_ERROR", "Unexpected form field", path="/", detail_code="unexpected")
        company_name = _validate_text("company_name", _one_text(form, "company_name", required=True) or "")
        founder_name = _validate_text("founder_name", _one_text(form, "founder_name", required=True) or "")
        founder_email = _one_text(form, "founder_email", required=True) or ""
        if not _EMAIL.fullmatch(founder_email):
            raise ApiProblem(422, "VALIDATION_ERROR", "Founder email is invalid", path="/founder_email", detail_code="email")
        linkedin_url = _validate_url("linkedin_url", _one_text(form, "linkedin_url"))
        github_url = _validate_url("github_url", _one_text(form, "github_url"))
        website_url = _validate_url("website_url", _one_text(form, "website_url"))
        pitch = form.getlist("pitch_deck")
        cv = form.getlist("cv")
        supporting = form.getlist("supporting_documents")
        if len(pitch) != 1 or not isinstance(pitch[0], UploadFile):
            raise ApiProblem(422, "VALIDATION_ERROR", "Exactly one pitch deck PDF is required", path="/pitch_deck", detail_code="required")
        if len(cv) > 1 or any(not isinstance(item, UploadFile) for item in cv):
            raise ApiProblem(422, "VALIDATION_ERROR", "At most one CV PDF is allowed", path="/cv", detail_code="count")
        if bool(cv) == bool(linkedin_url):
            raise ApiProblem(422, "VALIDATION_ERROR", "Provide exactly one of CV or LinkedIn URL", path="/cv", detail_code="cv_or_linkedin")
        if len(supporting) > 4 or any(not isinstance(item, UploadFile) for item in supporting):
            raise ApiProblem(422, "VALIDATION_ERROR", "At most four supporting PDFs are allowed", path="/supporting_documents", detail_code="count")
        pending.append(await _stage_pdf(pitch[0], "pitch_deck", repository, 0, file_limit=file_limit, aggregate_limit=aggregate_limit))
        total = pending[0].size_bytes
        if cv:
            pending.append(await _stage_pdf(cv[0], "cv", repository, total, file_limit=file_limit, aggregate_limit=aggregate_limit))
            total += pending[-1].size_bytes
        for item in supporting:
            pending.append(await _stage_pdf(item, "supporting", repository, total, file_limit=file_limit, aggregate_limit=aggregate_limit))
            total += pending[-1].size_bytes
        digest = request_digest(
            {"company_name": company_name, "founder_name": founder_name, "founder_email": founder_email,
             "linkedin_url": linkedin_url, "github_url": github_url, "website_url": website_url}, pending,
        )
        response, _replayed = repository.persist_submission(
            request_hash=digest, idempotency_key=key, company_name=company_name, founder_name=founder_name,
            founder_email=founder_email, linkedin_url=linkedin_url, github_url=github_url, website_url=website_url,
            documents=pending,
        )
        worker = getattr(request.app.state, "processing_worker", None)
        if worker is not None and not _replayed:
            await worker.enqueue(str(response["company"]["slug"]))
    except SubmissionStorageError as exc:
        if str(exc) == "IDEMPOTENCY_CONFLICT":
            raise ApiProblem(409, "IDEMPOTENCY_CONFLICT", "Idempotency key was already used for a different submission") from exc
        raise ApiProblem(503, "STORAGE_UNAVAILABLE", "Submission storage is unavailable") from exc
    finally:
        for document in pending:
            document.temporary_path.unlink(missing_ok=True)
        await _close_uploads(form)
    return JSONResponse(status_code=202, content=response)


@router.get("/jobs/{slug}", response_model=JobStatusModel)
def job_status(slug: str, request: Request) -> dict[str, object]:
    try:
        return _repository(request).get_job(slug)
    except SubmissionStorageError as exc:
        raise ApiProblem(404, "NOT_FOUND", "Job was not found") from exc


@router.post("/jobs/{slug}/retry", response_model=RetryResponseModel, status_code=202)
async def retry_job(
    slug: str,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    key = _idempotency_key(idempotency_key)
    try:
        job, replayed = _repository(request).retry_job(slug, key)
    except SubmissionStorageError as exc:
        if str(exc) == "RETRY_NOT_ALLOWED":
            raise ApiProblem(409, "RETRY_NOT_ALLOWED", "This job cannot be retried") from exc
        raise ApiProblem(404, "NOT_FOUND", "Job was not found") from exc
    worker = getattr(request.app.state, "processing_worker", None)
    if worker is not None and not replayed:
        await worker.enqueue(slug)
    return {"id": job["id"], "state": job["state"], "attempt": job["attempt"], "statusUrl": f"/api/v1/jobs/{slug}"}
