"""Read-only people and project directory backed by the local export."""
from __future__ import annotations
import json, os, sqlite3
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
router = APIRouter(prefix="/api/v1", tags=["people"])
_ROOT = Path(__file__).resolve().parents[4]
class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")
class PersonProjectModel(_Model):
    id: str
    title: str | None
    relationship: str
    completed: bool
class PersonModel(_Model):
    id: str
    name: str
    firstName: str | None
    lastName: str | None
    avatarUrl: str | None
    tagline: str | None
    university: str | None
    fieldOfStudy: str | None
    professionalSituation: str | None
    country: str | None
    city: str | None
    projects: list[PersonProjectModel]
class PeopleSearchModel(_Model):
    people: list[PersonModel]
def _json(value: str | None) -> dict[str, Any]:
    try: parsed = json.loads(value or "{}")
    except (TypeError, ValueError): return {}
    return parsed if isinstance(parsed, dict) else {}
def _completed(project: dict[str, Any]) -> bool:
    review = project.get("review")
    return isinstance(review, dict) and (review.get("status") == "approved" or review.get("pending") is False)
@router.get("/people/search", response_model=PeopleSearchModel)
def search_people(q: str = Query(min_length=2, max_length=120), limit: int = Query(default=8, ge=1, le=20)) -> dict[str, Any]:
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file(): return {"people": []}
    pattern = f"%{q.strip().lower()}%"
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            rows = db.execute("""SELECT user_id, roster_json, profile_json FROM people WHERE lower(json_extract(roster_json, '$.first_name')) LIKE ? OR lower(json_extract(roster_json, '$.last_name')) LIKE ? OR lower(json_extract(roster_json, '$.display_name')) LIKE ? ORDER BY json_extract(roster_json, '$.last_name'), json_extract(roster_json, '$.first_name') LIMIT ?""", (pattern, pattern, pattern, limit)).fetchall()
            people = []
            for user_id, roster_json, profile_json in rows:
                person = {**_json(roster_json), **_json(profile_json)}
                first = (person.get("first_name") or "").strip() or None; last = (person.get("last_name") or "").strip() or None
                projects = []
                for project_id, relationship, project_json in db.execute("""SELECT pp.project_id, pp.relationship, p.project_json FROM project_people pp JOIN projects p ON p.project_id = pp.project_id WHERE pp.user_id = ? ORDER BY p.title COLLATE NOCASE""", (user_id,)):
                    project = _json(project_json); projects.append({"id": project_id, "title": project.get("title"), "relationship": relationship, "completed": _completed(project)})
                people.append({"id": user_id, "name": " ".join(part for part in (first, last) if part) or person.get("display_name") or "Unknown person", "firstName": first, "lastName": last, "avatarUrl": person.get("avatar_url"), "tagline": person.get("tagline"), "university": person.get("university"), "fieldOfStudy": person.get("field_of_study"), "professionalSituation": person.get("professional_situation"), "country": person.get("country"), "city": person.get("city"), "projects": projects})
            return {"people": people}
    except (sqlite3.Error, OSError) as exc: raise HTTPException(status_code=500, detail="People directory is unavailable") from exc

