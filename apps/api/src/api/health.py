"""Service health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from .companies import FixtureIndexError, FixtureRepository

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    version: str
    workerAvailable: bool


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> JSONResponse:
    """Report whether the read-only fixture index can be safely served."""
    repository: FixtureRepository = request.app.state.fixture_repository
    try:
        repository.load_index()
    except FixtureIndexError:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "version": "v1", "workerAvailable": False},
        )
    return JSONResponse(content={"status": "ok", "version": "v1", "workerAvailable": False})
