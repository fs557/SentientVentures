from __future__ import annotations

import asyncio
import csv
import json
import sqlite3
import subprocess
import sys
import unicodedata
import uuid
from contextlib import closing
from pathlib import Path

import httpx
import pytest

from src.core.location_coordinates import (
    ensure_location_coordinates,
    normalize_location_component,
    sync_people_location_pairs,
)
from src.main import create_app


ROOT = Path(__file__).resolve().parents[3]
DATABASE = ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite"
SEED = ROOT / "assets" / "DATABASE" / "location_coordinates.csv"
FIXTURES = ROOT / "tests" / "fixtures" / "companies"


def _seed_rows() -> list[dict[str, str]]:
    with SEED.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_normalization_is_unicode_stable_and_platform_independent() -> None:
    decomposed = unicodedata.normalize("NFD", "Zürich")
    assert normalize_location_component(f"  {decomposed}\t") == "zürich"
    assert normalize_location_component("New   York\r\nCity") == "new york city"


def test_seed_is_complete_idempotent_and_coordinate_checked() -> None:
    db = sqlite3.connect(":memory:")
    first_count = ensure_location_coordinates(db, SEED)
    second_count = ensure_location_coordinates(db, SEED)
    stored_count = db.execute("SELECT COUNT(*) FROM location_coordinates").fetchone()[0]
    assert first_count == second_count == stored_count

    source_pairs: set[tuple[str, str]] = set()
    with sqlite3.connect(DATABASE) as source:
        for (profile_json,) in source.execute("SELECT profile_json FROM people"):
            profile = json.loads(profile_json or "{}")
            city, country = profile.get("city"), profile.get("country")
            if isinstance(city, str) and city.strip() and isinstance(country, str) and country.strip():
                source_pairs.add((normalize_location_component(city), normalize_location_component(country)))
    stored_pairs = set(db.execute("SELECT city_key, country_key FROM location_coordinates"))
    assert stored_pairs == source_pairs

    for status, latitude, longitude, source, geoname_id in db.execute(
        "SELECT status, latitude, longitude, source, geoname_id FROM location_coordinates"
    ):
        assert source
        if status == "resolved":
            assert -90 <= latitude <= 90
            assert -180 <= longitude <= 180
            assert geoname_id is not None
        else:
            assert latitude is None and longitude is None


def test_database_rejects_resolved_location_with_null_coordinates() -> None:
    db = sqlite3.connect(":memory:")
    ensure_location_coordinates(db, SEED)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO location_coordinates (
                city_key, country_key, city, country, latitude, longitude,
                status, source
            ) VALUES ('invalid', 'test', 'Invalid', 'Test', NULL, NULL, 'resolved', 'test')
            """
        )


def test_new_import_location_is_added_as_unresolved_without_overwriting_seed() -> None:
    db = sqlite3.connect(":memory:")
    ensure_location_coordinates(db, SEED)
    db.execute("CREATE TABLE people (profile_json TEXT)")
    db.execute(
        "INSERT INTO people VALUES (?)",
        (json.dumps({"city": "  Novel   City ", "country": " Testland "}),),
    )
    db.execute(
        "INSERT INTO people VALUES (?)",
        (json.dumps({"city": "Munich", "country": "Germany"}),),
    )
    assert sync_people_location_pairs(db) == 1
    assert sync_people_location_pairs(db) == 0
    novel = db.execute(
        "SELECT city, country, status, latitude, longitude, source FROM location_coordinates "
        "WHERE city_key = 'novel city' AND country_key = 'testland'"
    ).fetchone()
    assert novel == ("Novel City", "Testland", "unresolved", None, None, "people import")
    assert db.execute(
        "SELECT status, geoname_id FROM location_coordinates "
        "WHERE city_key = 'munich' AND country_key = 'germany'"
    ).fetchone() == ("resolved", 2867714)


@pytest.mark.parametrize(
    ("city", "country", "expected"),
    [
        ("Seattle", "United States", (47.60621, -122.33207, "5809844")),
        ("Lima", "Peru", (-12.04318, -77.02824, "3936456")),
        ("Munich", "Germany", (48.13743, 11.57549, "2867714")),
    ],
)
def test_reviewed_seed_has_known_geonames_coordinates(
    city: str, country: str, expected: tuple[float, float, str]
) -> None:
    row = next(
        row for row in _seed_rows()
        if row["city_key"] == normalize_location_component(city)
        and row["country_key"] == normalize_location_component(country)
    )
    assert (float(row["latitude"]), float(row["longitude"]), row["geoname_id"]) == expected


@pytest.mark.parametrize(
    ("city", "country", "canonical_name"),
    [
        ("Apex", "United States", "Apex"),
        ("Granville, OH", "United States of America", "Granville"),
        ("Visakhapatnam", "India", "Visakhapatnam"),
    ],
)
def test_matcher_does_not_accept_unrelated_alternate_name(
    city: str, country: str, canonical_name: str
) -> None:
    row = next(
        row for row in _seed_rows()
        if row["city_key"] == normalize_location_component(city)
        and row["country_key"] == normalize_location_component(country)
    )
    assert row["status"] == "unresolved" or row["match_name"] == canonical_name


async def _map_data() -> list[dict[str, object]]:
    app = create_app(fixtures_root=FIXTURES)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/people/map-data")
    assert response.status_code == 200
    return response.json()


def test_map_uses_exact_shared_city_points_and_omits_unmappable_people() -> None:
    data = asyncio.run(_map_data())
    munich_points = {
        (item["lat"], item["lng"])
        for item in data
        if normalize_location_component(str(item["city"])) == "munich"
        and normalize_location_component(str(item["country"])) == "germany"
    }
    assert munich_points == {(48.13743, 11.57549)}

    with sqlite3.connect(DATABASE) as db:
        expected_ids: set[str] = set()
        excluded_ids: set[str] = set()
        statuses = {
            (city_key, country_key): status
            for city_key, country_key, status in db.execute(
                "SELECT city_key, country_key, status FROM location_coordinates"
            )
        }
        for user_id, profile_json in db.execute("SELECT user_id, profile_json FROM people"):
            profile = json.loads(profile_json or "{}")
            city, country = profile.get("city"), profile.get("country")
            if isinstance(city, str) and city.strip() and isinstance(country, str) and country.strip():
                key = (normalize_location_component(city), normalize_location_component(country))
                target = expected_ids if statuses.get(key) == "resolved" else excluded_ids
            else:
                target = excluded_ids
            target.add(user_id)
    actual_ids = {str(item["id"]) for item in data}
    assert actual_ids == expected_ids
    assert actual_ids.isdisjoint(excluded_ids)


def test_importer_bootstraps_location_table_idempotently() -> None:
    database = ROOT / "tmp" / f"people-import-{uuid.uuid4().hex}.sqlite"
    database.parent.mkdir(exist_ok=True)
    command = [
        sys.executable,
        str(ROOT / "assets" / "DATABASE" / "import_hack_nation_people.py"),
        str(ROOT / "assets" / "DATABASE" / "hack_nation_people_raw.json"),
        "--database",
        str(database),
    ]
    try:
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT COUNT(*) FROM location_coordinates").fetchone()[0] == len(_seed_rows())
    finally:
        database.unlink(missing_ok=True)


def test_init_db_reports_coordinate_seed_failure_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.api import people as people_api

    database = ROOT / "tmp" / f"people-init-{uuid.uuid4().hex}.sqlite"
    database.parent.mkdir(exist_ok=True)
    sqlite3.connect(database).close()
    monkeypatch.setenv("SV_PEOPLE_DATABASE", str(database))

    def fail_seed(_db: sqlite3.Connection) -> int:
        raise ValueError("bad coordinate row")

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(people_api, "ensure_location_coordinates", fail_seed)
    monkeypatch.setattr(people_api.sqlite3, "connect", lambda _path: FakeConnection())
    try:
        with pytest.raises(RuntimeError, match="Failed to initialize people database.*bad coordinate row"):
            people_api.init_db()
    finally:
        database.unlink(missing_ok=True)
