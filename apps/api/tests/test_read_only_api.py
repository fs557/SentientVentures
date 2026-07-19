"""Read-only v1 API contract tests for the deterministic fixtures."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil

import httpx
from fastapi import FastAPI
from jsonschema import Draft202012Validator, FormatChecker, RefResolver
import pytest

from src.main import create_app
from src.core.integrity import fixture_sha256


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "companies"
SCHEMA_ROOT = ROOT / "packages" / "contracts" / "schema"


@pytest.fixture
def app() -> FastAPI:
    return create_app(fixtures_root=FIXTURES)


def _assert_error_envelope(response: httpx.Response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()["error"]
    assert body["code"] == code
    assert body["details"]
    assert body["requestId"]
    assert response.headers["X-Request-Id"] == body["requestId"]


async def _get(app: FastAPI, path: str, *, params: dict[str, int] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, params=params)



def _request(app: FastAPI, path: str, *, params: dict[str, int] | None = None) -> httpx.Response:
    return asyncio.run(_get(app, path, params=params))


def _refresh_manifest(root: Path) -> None:
    files = {
        str(path.relative_to(root)): fixture_sha256(path)
        for path in sorted(root.rglob("*")) if path.is_file() and path.name != "manifest.json"
    }
    (root / "manifest.json").write_text(
        json.dumps({"generator": "v1", "files": files}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validator(schema_name: str, definition: str) -> Draft202012Validator:
    schema_path = SCHEMA_ROOT / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    common = json.loads((SCHEMA_ROOT / "common.v1.json").read_text(encoding="utf-8"))
    schema["$ref"] = f"#/$defs/{definition}"
    return Draft202012Validator(
        schema,
        resolver=RefResolver(
            base_uri=schema["$id"],
            referrer=schema,
            store={schema["$id"]: schema, common["$id"]: common},
        ),
        format_checker=FormatChecker(),
    )


def test_health_and_company_list_match_the_v1_contract(app: FastAPI) -> None:
    service_index = _request(app, "/")
    assert service_index.status_code == 200
    assert service_index.json() == {
        "status": "ok",
        "version": "v1",
        "endpoints": {"health": "/health", "api": "/api/v1", "docs": "/docs"},
    }

    health = _request(app, "/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": "v1", "workerAvailable": False}
    assert health.headers["X-Request-Id"]

    response = _request(app, "/api/v1/companies", params={"limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["registryVersion"] == 1
    assert len(payload["companies"]) == 1
    summary = payload["companies"][0]
    assert set(summary) == {"slug", "company", "stage", "submissionDate", "overallScore", "categoryScores"}
    assert set(summary["categoryScores"]) == {"home", "idea", "market", "financial", "management"}
    assert not list(_validator("api.v1.json", "companiesList").iter_errors(payload))


def test_aggregate_and_category_reads_are_company_isolated(app: FastAPI) -> None:
    aether = _request(app, "/api/v1/companies/aether-robotics")
    harbor = _request(app, "/api/v1/companies/harborloop")
    assert aether.status_code == harbor.status_code == 200

    aether_payload = aether.json()
    harbor_payload = harbor.json()
    assert aether_payload["slug"] == "aether-robotics"
    assert harbor_payload["slug"] == "harborloop"
    assert set(aether_payload["categories"]) == {"home", "idea", "market", "financial", "management"}
    assert all(document["slug"] == "aether-robotics" for document in aether_payload["categories"].values())
    assert all(document["slug"] == "harborloop" for document in harbor_payload["categories"].values())

    category = _request(app, "/api/v1/companies/aether-robotics/categories/market")
    assert category.status_code == 200
    assert category.json() == aether_payload["categories"]["market"]
    assert category.json()["company"] != harbor_payload["company"]
    assert not list(_validator("evaluation.v1.json", "companyEvaluation").iter_errors(aether_payload))
    assert not list(_validator("evaluation.v1.json", "evaluationDocument").iter_errors(category.json()))


def test_aggregate_reads_populated_investment_terms_from_isolated_metadata(app: FastAPI) -> None:
    aether = _request(app, "/api/v1/companies/aether-robotics").json()["investment"]
    harbor = _request(app, "/api/v1/companies/harborloop").json()["investment"]
    assert aether == {
        "amount": 100000.0, "currency": "EUR", "equityPercentage": 1.0,
        "preMoneyValuation": 9900000.0, "postMoneyValuation": 10000000.0,
        "impliedValuation": 10000000.0,
        "useOfFunds": ["robot fleet validation", "industrial software integrations", "enterprise sales"],
    }
    assert harbor["amount"] == 100000.0
    assert harbor["equityPercentage"] == 4.0
    assert harbor != aether


def test_missing_investment_metadata_remains_backward_compatible(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    del metadata["investment"]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    assert response.status_code == 200
    assert response.json()["investment"] == {
        "amount": None, "currency": None, "equityPercentage": None,
        "preMoneyValuation": None, "postMoneyValuation": None,
        "impliedValuation": None, "useOfFunds": [],
    }


def test_present_all_null_empty_investment_terms_remain_contract_valid(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["investment"] = {
        "amount": None, "currency": None, "equityPercentage": None,
        "preMoneyValuation": None, "postMoneyValuation": None,
        "impliedValuation": None, "useOfFunds": [],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    assert response.status_code == 200
    assert response.json()["investment"] == metadata["investment"]


def test_partial_investment_terms_remain_contract_valid(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["investment"] = {
        "amount": 100000, "currency": "EUR", "equityPercentage": None,
        "preMoneyValuation": None, "postMoneyValuation": None,
        "impliedValuation": None, "useOfFunds": [],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    assert response.status_code == 200
    assert response.json()["investment"] == metadata["investment"]


@pytest.mark.parametrize("field, value", [("amount", True), ("currency", "eur"), ("equityPercentage", 101), ("useOfFunds", [""])])
def test_malformed_present_investment_metadata_fails_closed(tmp_path: Path, field: str, value: object) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["investment"][field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    _assert_error_envelope(response, 500, "INDEX_INVALID")


@pytest.mark.parametrize("field, value", [("postMoneyValuation", 12500001), ("equityPercentage", 21)])
def test_inconsistent_present_investment_metadata_fails_closed(tmp_path: Path, field: str, value: object) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["investment"][field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    _assert_error_envelope(response, 500, "INDEX_INVALID")


def test_partial_terms_with_nonpositive_post_money_and_equity_fail_closed(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    metadata_path = copied_fixtures / "aether-robotics" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["investment"].update({
        "amount": 100, "preMoneyValuation": None, "postMoneyValuation": 0,
        "equityPercentage": 20,
    })
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_manifest(copied_fixtures)

    response = _request(create_app(fixtures_root=copied_fixtures), "/api/v1/companies/aether-robotics")
    _assert_error_envelope(response, 500, "INDEX_INVALID")


@pytest.mark.parametrize(
    ("path", "status_code", "code"),
    [
        ("/api/v1/companies?limit=0", 422, "VALIDATION_ERROR"),
        ("/api/v1/companies/INVALID", 422, "VALIDATION_ERROR"),
        ("/api/v1/companies/aether-robotics/categories/unknown", 422, "VALIDATION_ERROR"),
        ("/api/v1/companies/missing-company", 404, "NOT_FOUND"),
    ],
)
def test_invalid_requests_use_the_error_envelope(
    app: FastAPI, path: str, status_code: int, code: str
) -> None:
    _assert_error_envelope(_request(app, path), status_code, code)


def test_fixture_integrity_failure_is_not_served(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    evaluation = copied_fixtures / "aether-robotics" / "evaluation" / "aether-robotics_idea.md"
    evaluation.write_text(evaluation.read_text(encoding="utf-8") + "\nTampered", encoding="utf-8")

    app = create_app(fixtures_root=copied_fixtures)
    health = _request(app, "/health")
    assert health.status_code == 503
    assert health.json() == {"status": "unavailable", "version": "v1", "workerAvailable": False}

    response = _request(app, "/api/v1/companies")
    _assert_error_envelope(response, 500, "INDEX_INVALID")
    assert "Tampered" not in response.text


def test_fixture_integrity_accepts_windows_line_endings_for_text_artifacts(tmp_path: Path) -> None:
    copied_fixtures = tmp_path / "companies"
    shutil.copytree(FIXTURES, copied_fixtures)
    evaluation = copied_fixtures / "aether-robotics" / "evaluation" / "aether-robotics_idea.md"
    evaluation.write_bytes(evaluation.read_bytes().replace(b"\n", b"\r\n"))

    app = create_app(fixtures_root=copied_fixtures)
    health = _request(app, "/health")
    assert health.status_code == 200
    assert _request(app, "/api/v1/companies").status_code == 200


def test_cors_allows_only_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SV_ALLOWED_ORIGINS", "http://dashboard.example.test")
    app = create_app(fixtures_root=FIXTURES)
    allowed = _request(
        app,
        "/api/v1/companies",
        params=None,
    )
    # A normal request has no Origin. The preflight checks are performed below.
    assert allowed.status_code == 200

    async def preflight(origin: str) -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.options(
                "/api/v1/companies",
                headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
            )

    configured = asyncio.run(preflight("http://dashboard.example.test"))
    assert configured.status_code == 200
    assert configured.headers["Access-Control-Allow-Origin"] == "http://dashboard.example.test"
    assert "Access-Control-Allow-Credentials" not in configured.headers

    blocked = asyncio.run(preflight("http://untrusted.example.test"))
    assert blocked.status_code == 400
    assert "Access-Control-Allow-Origin" not in blocked.headers
