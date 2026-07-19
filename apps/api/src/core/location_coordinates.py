"""Deterministic, offline city-coordinate seed support."""

from __future__ import annotations

import csv
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_LOCATION_SEED = ROOT / "assets" / "DATABASE" / "location_coordinates.csv"


LOCATION_TABLE_SQL = """
    CREATE TABLE location_coordinates (
        city_key TEXT NOT NULL,
        country_key TEXT NOT NULL,
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        status TEXT NOT NULL CHECK (status IN ('resolved', 'unresolved')),
        source TEXT NOT NULL,
        geoname_id INTEGER,
        match_name TEXT,
        notes TEXT,
        PRIMARY KEY (city_key, country_key),
        CHECK (
            (status = 'resolved' AND latitude IS NOT NULL AND longitude IS NOT NULL
                AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
            OR
            (status = 'unresolved' AND latitude IS NULL AND longitude IS NULL)
        )
    )
"""


def normalize_location_component(value: str) -> str:
    """Return the stable key used for city and country joins."""

    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def ensure_location_coordinates(
    db: sqlite3.Connection,
    seed_path: Path = DEFAULT_LOCATION_SEED,
) -> int:
    """Create the lookup table and idempotently upsert its reviewed CSV seed."""

    existing_sql_row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'location_coordinates'"
    ).fetchone()
    if existing_sql_row is None:
        db.execute(LOCATION_TABLE_SQL)
    elif "latitude IS NOT NULL" not in (existing_sql_row[0] or ""):
        db.execute("ALTER TABLE location_coordinates RENAME TO location_coordinates_legacy")
        db.execute(LOCATION_TABLE_SQL)
        db.execute("""
            INSERT INTO location_coordinates
            SELECT * FROM location_coordinates_legacy
        """)
        db.execute("DROP TABLE location_coordinates_legacy")
    if not seed_path.is_file():
        return 0

    upserted = 0
    with seed_path.open("r", encoding="utf-8-sig", newline="") as seed_file:
        reader = csv.DictReader(seed_file)
        required = {
            "city_key", "country_key", "city", "country", "latitude",
            "longitude", "status", "source", "geoname_id", "match_name", "notes",
        }
        if not reader.fieldnames or required.difference(reader.fieldnames):
            missing = ", ".join(sorted(required.difference(reader.fieldnames or [])))
            raise ValueError(f"Location seed is missing required columns: {missing}")

        for line_number, row in enumerate(reader, start=2):
            city = row["city"]
            country = row["country"]
            city_key = normalize_location_component(row["city_key"])
            country_key = normalize_location_component(row["country_key"])
            if not city_key or not country_key:
                raise ValueError(f"Location seed line {line_number} has an empty key")
            if city_key != normalize_location_component(city) or country_key != normalize_location_component(country):
                raise ValueError(f"Location seed line {line_number} has non-canonical keys")

            status = row["status"].strip().casefold()
            source = row["source"].strip()
            if status not in {"resolved", "unresolved"} or not source:
                raise ValueError(f"Location seed line {line_number} has invalid status/source")
            latitude = float(row["latitude"]) if row["latitude"].strip() else None
            longitude = float(row["longitude"]) if row["longitude"].strip() else None
            geoname_id = int(row["geoname_id"]) if row["geoname_id"].strip() else None
            if status == "resolved":
                if latitude is None or longitude is None:
                    raise ValueError(f"Resolved location seed line {line_number} lacks coordinates")
                if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                    raise ValueError(f"Location seed line {line_number} has out-of-range coordinates")
            elif latitude is not None or longitude is not None:
                raise ValueError(f"Unresolved location seed line {line_number} has coordinates")

            db.execute(
                """
                INSERT INTO location_coordinates (
                    city_key, country_key, city, country, latitude, longitude,
                    status, source, geoname_id, match_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(city_key, country_key) DO UPDATE SET
                    city=excluded.city, country=excluded.country,
                    latitude=excluded.latitude, longitude=excluded.longitude,
                    status=excluded.status, source=excluded.source,
                    geoname_id=excluded.geoname_id,
                    match_name=excluded.match_name, notes=excluded.notes
                """,
                (
                    city_key, country_key, city, country, latitude, longitude,
                    status, source, geoname_id, row["match_name"].strip() or None,
                    row["notes"].strip() or None,
                ),
            )
            upserted += 1
    return upserted


def sync_people_location_pairs(db: sqlite3.Connection) -> int:
    """Record newly imported complete locations for explicit later review."""

    import json

    inserted = 0
    for (profile_json,) in db.execute("SELECT profile_json FROM people"):
        try:
            profile = json.loads(profile_json or "{}")
        except (TypeError, ValueError):
            continue
        city = profile.get("city")
        country = profile.get("country")
        if not isinstance(city, str) or not city.strip() or not isinstance(country, str) or not country.strip():
            continue
        city = " ".join(city.split())
        country = " ".join(country.split())
        cursor = db.execute(
            """
            INSERT INTO location_coordinates (
                city_key, country_key, city, country, latitude, longitude,
                status, source, geoname_id, match_name, notes
            ) VALUES (?, ?, ?, ?, NULL, NULL, 'unresolved', 'people import', NULL, NULL,
                'New location from people import; review required')
            ON CONFLICT(city_key, country_key) DO NOTHING
            """,
            (
                normalize_location_component(city), normalize_location_component(country),
                city, country,
            ),
        )
        inserted += cursor.rowcount
    return inserted
