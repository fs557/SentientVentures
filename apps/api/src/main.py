"""FastAPI application for the local SentientVentures service."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.companies import CompanyRepository, FixtureRepository, LiveCompanyRepository, router as companies_router
from .api.people import router as people_router
from .api.health import router as health_router
from .api.submissions import ApiProblem, SubmissionBodyLimitMiddleware, router as submissions_router
from .core.submissions import SubmissionRepository
from .providers.council import configured_provider
from .workers.queue import ProcessingWorker

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPOSITORY_ROOT / ".env", override=False)
_FIXTURES_ROOT = _REPOSITORY_ROOT / "tests" / "fixtures" / "companies"
_DEFAULT_ALLOWED_ORIGINS = ("http://localhost:8080", "http://localhost:8081")


def _allowed_origins() -> tuple[str, ...]:
    configured = os.getenv("SV_ALLOWED_ORIGINS")
    if configured is None:
        return _DEFAULT_ALLOWED_ORIGINS
    return tuple(origin.strip() for origin in configured.split(",") if origin.strip() and origin.strip() != "*")


def _data_root() -> Path:
    """Return a local data root; relative overrides stay inside this repository."""
    configured = os.getenv("SV_DATA_ROOT")
    if configured is None:
        return _REPOSITORY_ROOT / "data" / "companies"
    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate.resolve()
    return (_REPOSITORY_ROOT / candidate).resolve()


def _error_response(request: Request, status_code: int, code: str, message: str, details: list[dict[str, str]]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details, "requestId": request.state.request_id}},
    )


def create_app(*, fixtures_root: Path | None = None, data_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="SentientVentures API", version="v1")
    app.state.fixture_repository = FixtureRepository(fixtures_root or _FIXTURES_ROOT)
    app.state.submission_repository = SubmissionRepository(
        data_root or _data_root(), reserved_slugs=app.state.fixture_repository.reserved_slugs()
    )
    app.state.company_repository = CompanyRepository(
        app.state.fixture_repository, LiveCompanyRepository(app.state.submission_repository.root)
    )
    app.state.processing_worker = ProcessingWorker(app.state.submission_repository, configured_provider())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_allowed_origins()),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Demo-Reset-Token"],
    )
    app.add_middleware(SubmissionBodyLimitMiddleware)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: object) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"path": "/" + "/".join(str(value) for value in error["loc"]), "code": error["type"], "message": error["msg"]}
            for error in exc.errors()
        ]
        return _error_response(request, 422, "VALIDATION_ERROR", "Request validation failed", details)

    @app.exception_handler(ApiProblem)
    async def api_problem(request: Request, exc: ApiProblem) -> JSONResponse:
        return _error_response(
            request, exc.status_code, exc.code, exc.message,
            [{"path": exc.path, "code": exc.detail_code, "message": exc.message}],
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_code = exc.status_code
        code = {404: "NOT_FOUND", 422: "VALIDATION_ERROR", 500: "INDEX_INVALID"}.get(status_code, "HTTP_ERROR")
        message = str(exc.detail) if isinstance(exc.detail, str) else "Request failed"
        return _error_response(request, status_code, code, message, [{"path": "/", "code": code, "message": message}])

    app.include_router(health_router)
    app.include_router(companies_router)
    app.include_router(people_router)
    app.include_router(submissions_router)

    @app.on_event("startup")
    async def start_processing_worker() -> None:
        await app.state.processing_worker.start()

    @app.on_event("shutdown")
    async def stop_processing_worker() -> None:
        await app.state.processing_worker.stop()
    return app


app = create_app()
