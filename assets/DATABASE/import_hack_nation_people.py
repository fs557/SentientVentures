#!/usr/bin/env python3
"""Load an export_hack_nation_people.py JSON export into SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.core.location_coordinates import (  # noqa: E402
    ensure_location_coordinates,
    sync_people_location_pairs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a Hack-Nation public-directory JSON export into SQLite.")
    parser.add_argument("input", type=Path, help="JSON file created by export_hack_nation_people.py")
    parser.add_argument("--database", default="hack_nation_people.sqlite", type=Path)
    args = parser.parse_args()

    export = json.loads(args.input.read_text(encoding="utf-8"))
    roster = export["roster_response"].get("data", {})
    people = roster.get("people", [])
    profiles = export.get("profiles", [])
    projects_response = export.get("projects_response", {})
    projects = projects_response.get("data", projects_response)
    if not isinstance(projects, list):
        raise ValueError("Unexpected projects export: expected a list in projects_response.data")
    contributions = roster.get("contributionsByUserId", {})

    db = sqlite3.connect(args.database)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS exports (
            exported_at TEXT PRIMARY KEY,
            source_people_url TEXT NOT NULL,
            source_profiles_url TEXT NOT NULL,
            source_projects_url TEXT
        );
        CREATE TABLE IF NOT EXISTS people (
            user_id TEXT PRIMARY KEY,
            roster_json TEXT NOT NULL,
            profile_json TEXT,
            contributions_json TEXT,
            exported_at TEXT NOT NULL REFERENCES exports(exported_at)
        );
        CREATE INDEX IF NOT EXISTS people_exported_at_idx ON people(exported_at);
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            title TEXT,
            owner_id TEXT,
            project_json TEXT NOT NULL,
            exported_at TEXT NOT NULL REFERENCES exports(exported_at)
        );
        CREATE INDEX IF NOT EXISTS projects_owner_id_idx ON projects(owner_id);
        CREATE TABLE IF NOT EXISTS project_people (
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            user_id TEXT NOT NULL REFERENCES people(user_id),
            relationship TEXT NOT NULL,
            exported_at TEXT NOT NULL REFERENCES exports(exported_at),
            PRIMARY KEY (project_id, user_id, relationship)
        );
        """
    )
    ensure_location_coordinates(db)
    # Backward-compatible upgrade for databases created by older script versions.
    export_columns = {row[1] for row in db.execute("PRAGMA table_info(exports)")}
    if "source_projects_url" not in export_columns:
        db.execute("ALTER TABLE exports ADD COLUMN source_projects_url TEXT")
    exported_at = export["exported_at"]
    db.execute(
        "INSERT OR REPLACE INTO exports (exported_at, source_people_url, source_profiles_url, source_projects_url) VALUES (?, ?, ?, ?)",
        (exported_at, export["source"]["people"], export["source"]["profiles"], export["source"].get("projects")),
    )
    by_id = {profile.get("user_id"): profile for profile in profiles if profile.get("user_id")}
    people_ids = {person.get("user_id") for person in people}
    for person in people:
        user_id = person.get("user_id")
        if not user_id:
            continue
        db.execute(
            """INSERT INTO people (user_id, roster_json, profile_json, contributions_json, exported_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 roster_json=excluded.roster_json, profile_json=excluded.profile_json,
                 contributions_json=excluded.contributions_json, exported_at=excluded.exported_at""",
            (
                user_id,
                json.dumps(person, ensure_ascii=False),
                json.dumps(by_id[user_id], ensure_ascii=False) if user_id in by_id else None,
                json.dumps(contributions.get(user_id), ensure_ascii=False),
                exported_at,
            ),
        )
    sync_people_location_pairs(db)
    for project in projects:
        project_id = project.get("id")
        if not project_id:
            continue
        db.execute(
            """INSERT INTO projects (project_id, title, owner_id, project_json, exported_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(project_id) DO UPDATE SET title=excluded.title, owner_id=excluded.owner_id,
               project_json=excluded.project_json, exported_at=excluded.exported_at""",
            (project_id, project.get("title"), project.get("ownerId"), json.dumps(project, ensure_ascii=False), exported_at),
        )
        related = [(project.get("ownerId"), "owner")]
        related.extend((member.get("userId"), member.get("role") or "contributor") for member in project.get("team", []) if isinstance(member, dict))
        for user_id, relationship in related:
            if user_id in people_ids:
                db.execute(
                    "INSERT OR REPLACE INTO project_people VALUES (?, ?, ?, ?)",
                    (project_id, user_id, relationship, exported_at),
                )
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    project_count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    db.close()
    print(f"Imported {len(people)} people, {len(profiles)} profiles, and {len(projects)} projects; database now has {count} people and {project_count} projects.")


if __name__ == "__main__":
    main()
