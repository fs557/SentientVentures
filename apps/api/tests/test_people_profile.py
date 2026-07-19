from __future__ import annotations

import asyncio
import builtins
import sqlite3
import pytest
from pathlib import Path
from fastapi import FastAPI
import httpx

from src.main import create_app


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "companies"


@pytest.fixture
def app() -> FastAPI:
    return create_app(fixtures_root=FIXTURES)


async def _get(app: FastAPI, path: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


def _request(app: FastAPI, path: str) -> httpx.Response:
    return asyncio.run(_get(app, path))


def test_db_seeding_and_table_exist(app: FastAPI) -> None:
    # Check that database is initialized correctly
    import os
    
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    
    assert path.is_file()
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        # Check if table founder_scores exists
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='founder_scores'")
        assert cursor.fetchone() is not None
        
        # Check if seeds are inserted
        count = db.execute("SELECT COUNT(*) FROM founder_scores").fetchone()[0]
        assert count > 0


def test_get_person_profile_success(app: FastAPI) -> None:
    # Akshat Tandon user_id
    user_id = "02887d15-7eac-40f7-836d-4a7a23031b5a"
    res = _request(app, f"/api/v1/people/{user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user_id
    assert "Akshat" in data["name"]
    assert data["activeFounderScore"] == 75.0  # Most recent score
    assert len(data["projects"]) > 0


def test_get_person_scores_success(app: FastAPI) -> None:
    user_id = "02887d15-7eac-40f7-836d-4a7a23031b5a"
    res = _request(app, f"/api/v1/people/{user_id}/scores")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Check chronological ordering
    assert data[0]["timestamp"] < data[1]["timestamp"] < data[2]["timestamp"]
    assert data[0]["score"] == 20.0
    assert data[2]["score"] == 75.0


def test_get_person_network_success(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def import_without_networkx(name: str, *args: object, **kwargs: object) -> object:
        if name == "networkx" or name.startswith("networkx."):
            raise ModuleNotFoundError("No module named 'networkx'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_networkx)
    user_id = "02887d15-7eac-40f7-836d-4a7a23031b5a"
    res = _request(app, f"/api/v1/people/{user_id}/network")
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"directed", "multigraph", "graph", "nodes", "edges"}
    assert data["directed"] is False
    assert data["multigraph"] is False
    assert data["graph"] == {}
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    
    # Root node must be present
    node_ids = {n["id"] for n in data["nodes"]}
    assert user_id in node_ids


def test_person_profile_not_found(app: FastAPI) -> None:
    # Random UUID not in DB
    user_id = "00000000-0000-0000-0000-000000000000"
    res = _request(app, f"/api/v1/people/{user_id}")
    assert res.status_code == 404


def test_person_profile_invalid_id_format(app: FastAPI) -> None:
    # Non-uuid string
    user_id = "not-a-uuid"
    res = _request(app, f"/api/v1/people/{user_id}")
    assert res.status_code == 422


def test_get_people_map_data_success(app: FastAPI) -> None:
    res = _request(app, "/api/v1/people/map-data")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Every item must have lat, lng, score, id, name
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "lat" in item
        assert "lng" in item
        assert "score" in item
        assert isinstance(item["lat"], float)
        assert isinstance(item["lng"], float)
        assert isinstance(item["score"], float)

