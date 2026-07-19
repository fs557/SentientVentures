"""Focused contract tests for secure v1 submissions and persisted job status."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI
import pytest

from src.main import create_app


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "companies"
PDF = b"%PDF-1.4\nminimal test payload"


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    return create_app(fixtures_root=FIXTURES, data_root=tmp_path / "companies")


async def _post(app: FastAPI, path: str, **kwargs: object) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(path, **kwargs)


async def _get(app: FastAPI, path: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


def _files(*, pitch: tuple[str, bytes, str] = ("deck.pdf", PDF, "application/pdf")) -> dict[str, object]:
    return {"pitch_deck": pitch}


def _data() -> dict[str, str]:
    return {"company_name": "Aster Labs", "founder_name": "Aster Founder", "founder_email": "founder@example.test", "linkedin_url": "https://linkedin.example.test/founder"}


def _submit(app: FastAPI, key: str, *, data: dict[str, str] | None = None, files: dict[str, object] | None = None) -> httpx.Response:
    return asyncio.run(_post(app, "/api/v1/submissions", headers={"Idempotency-Key": key}, data=data or _data(), files=files or _files()))


def test_submission_replays_exact_idempotency_key_and_rejects_conflicts(app: FastAPI) -> None:
    key = str(uuid4())
    first = _submit(app, key)
    replay = _submit(app, key)
    assert first.status_code == replay.status_code == 202
    assert replay.json() == first.json()

    changed = _data()
    changed["company_name"] = "Different Company"
    conflict = _submit(app, key, data=changed)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize(
    ("data", "files", "status", "detail_code"),
    [
        ({**_data(), "linkedin_url": "http://not-secure.example"}, _files(), 422, "url"),
        (_data(), _files(pitch=("deck.txt", PDF, "application/pdf")), 415, "extension"),
        (_data(), _files(pitch=("deck.pdf", b"not a pdf", "application/pdf")), 415, "magic"),
    ],
)
def test_submission_validation_does_not_expose_upload_content(
    app: FastAPI, data: dict[str, str], files: dict[str, object], status: int, detail_code: str
) -> None:
    response = _submit(app, str(uuid4()), data=data, files=files)
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] in {"VALIDATION_ERROR", "UNSUPPORTED_MEDIA_TYPE"}
    assert error["details"][0]["code"] == detail_code
    assert "not a pdf" not in response.text


def test_safe_storage_and_job_retry_transition(app: FastAPI, tmp_path: Path) -> None:
    accepted = _submit(app, str(uuid4()), files=_files(pitch=("../../Deck.PDF", PDF, "application/pdf")))
    assert accepted.status_code == 202
    slug = accepted.json()["company"]["slug"]
    source = tmp_path / "companies" / slug / "source"
    stored = next(source.iterdir())
    assert stored.parent == source
    assert ".." not in stored.name and "/" not in stored.name

    queued = asyncio.run(_get(app, f"/api/v1/jobs/{slug}"))
    assert queued.status_code == 200
    assert queued.json()["state"] == "queued"
    metadata_path = tmp_path / "companies" / slug / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["current_job"].update({"state": "failed", "stage": "extracting", "progress": 10, "retryAllowed": True, "error": {"code": "WORKER_FAILED"}})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    retry_key = str(uuid4())
    retry = asyncio.run(_post(app, f"/api/v1/jobs/{slug}/retry", headers={"Idempotency-Key": retry_key}))
    assert retry.status_code == 202
    assert retry.json()["state"] == "queued"
    assert retry.json()["attempt"] == 2
    replay = asyncio.run(_post(app, f"/api/v1/jobs/{slug}/retry", headers={"Idempotency-Key": retry_key}))
    assert replay.status_code == 202
    assert replay.json() == retry.json()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["current_job"].update({"state": "failed", "stage": "council", "progress": 100, "retryAllowed": True, "error": {"code": "PROVIDER_UNAVAILABLE"}})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    third = asyncio.run(_post(app, f"/api/v1/jobs/{slug}/retry", headers={"Idempotency-Key": str(uuid4())}))
    assert third.status_code == 202
    assert third.json()["attempt"] == 3
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["current_job"].update({"state": "failed", "stage": "council", "progress": 100, "retryAllowed": False, "error": {"code": "PROVIDER_UNAVAILABLE"}})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    exhausted = asyncio.run(_post(app, f"/api/v1/jobs/{slug}/retry", headers={"Idempotency-Key": str(uuid4())}))
    assert exhausted.status_code == 409


def test_submission_cors_never_enables_credentials(app: FastAPI) -> None:
    async def preflight() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.options(
                "/api/v1/submissions",
                headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "POST"},
            )

    response = asyncio.run(preflight())
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_submission_rejects_oversized_declared_multipart_before_parsing(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SV_MAX_FILE_BYTES", "8")
    monkeypatch.setenv("SV_MAX_AGGREGATE_FILE_BYTES", "8")
    response = _submit(app, str(uuid4()))
    assert response.status_code == 413
    assert response.json()["error"]["details"][0]["code"] == "content_length"


def test_submission_reserves_fixture_slug_and_uses_suffix(app: FastAPI) -> None:
    data = _data()
    data["company_name"] = "Aether Robotics"
    response = _submit(app, str(uuid4()), data=data)
    assert response.status_code == 202
    assert response.json()["company"]["slug"] == "aether-robotics-2"


def test_submission_rejects_chunked_upload_before_multipart_parser(app: FastAPI) -> None:
    async def invoke_without_content_length() -> list[dict[str, object]]:
        sent: list[dict[str, object]] = []
        messages = iter([
            {"type": "http.request", "body": b"ignored", "more_body": False},
            {"type": "http.disconnect"},
        ])

        async def receive() -> dict[str, object]:
            return next(messages)

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
                   "scheme": "http", "path": "/api/v1/submissions", "raw_path": b"/api/v1/submissions",
                   "query_string": b"", "headers": [], "client": ("test", 1), "server": ("test", 80)}, receive, send)
        return sent

    sent = asyncio.run(invoke_without_content_length())
    assert sent[0]["status"] == 411
