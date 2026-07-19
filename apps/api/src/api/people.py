"""Read-only people and project directory backed by the local export."""
from __future__ import annotations
import json, os, sqlite3
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
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


def extract_founder_names(text: str) -> list[str]:
    if not text:
        return []
    import re
    clean = re.sub(r'(the founding team is|the founders are|founders are|founder is|co-founders|co-founder|founding team)', '', text, flags=re.IGNORECASE)
    parts = re.split(r'\band\b|\b&\b|,|\bor\b', clean, flags=re.IGNORECASE)
    names = []
    for p in parts:
        p = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()]', '', p).strip()
        if len(p) >= 2:
            names.append(p)
    return names


def filter_rows(rows: list, name: str) -> list[dict]:
    res = []
    lower_name = name.lower()
    for user_id, roster_json, profile_json in rows:
        roster = _json(roster_json or "{}")
        profile = _json(profile_json or "{}")
        first = (roster.get("first_name") or "").strip()
        last = (roster.get("last_name") or "").strip()
        disp = (roster.get("display_name") or "").strip()
        reconstructed = " ".join(p for p in (first, last) if p) or disp or "Unknown"
        if lower_name in reconstructed.lower() or reconstructed.lower() in lower_name:
            res.append({
                "user_id": user_id,
                "name": reconstructed,
                "roster": roster,
                "profile": profile
            })
    return res


def find_user_by_name(db, name: str) -> dict | None:
    pattern = f"%{name.strip().lower()}%"
    rows = db.execute("""SELECT user_id, roster_json, profile_json FROM people WHERE lower(json_extract(roster_json, '$.first_name')) LIKE ? OR lower(json_extract(roster_json, '$.last_name')) LIKE ? OR lower(json_extract(roster_json, '$.display_name')) LIKE ?""", (pattern, pattern, pattern)).fetchall()
    matched = filter_rows(rows, name)
    if matched:
        return matched[0]
    first_token = name.split()[0]
    if len(first_token) >= 2:
        pattern = f"%{first_token.lower()}%"
        rows = db.execute("""SELECT user_id, roster_json, profile_json FROM people WHERE lower(json_extract(roster_json, '$.first_name')) LIKE ? OR lower(json_extract(roster_json, '$.last_name')) LIKE ? OR lower(json_extract(roster_json, '$.display_name')) LIKE ?""", (pattern, pattern, pattern)).fetchall()
        matched = filter_rows(rows, name)
        if matched:
            return matched[0]
    return None


@router.get("/people/network")
def get_people_network(company_slug: str, request: Request) -> dict[str, Any]:
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file():
        return {"nodes": [], "links": []}

    try:
        company_repo = request.app.state.company_repository
        company = company_repo.get_company(company_slug)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Company not found") from exc

    home = company.categories.get("home")
    if not home:
        return {"nodes": [], "links": []}

    founders_text = ""
    # home is a dict where items is a list of dicts (converted to contract dict)
    home_dict = company.categories["home"]
    items = home_dict.get("items", []) if isinstance(home_dict, dict) else getattr(home_dict, "items", [])
    for item in items:
        # item can be a dict or a pydantic model
        item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if item_id == "home.founders":
            founders_text = item.get("assessment") if isinstance(item, dict) else getattr(item, "assessment", "")
            break

    founder_names = extract_founder_names(founders_text)
    if not founder_names:
        return {"nodes": [], "links": []}

    import networkx as nx
    from networkx.readwrite import json_graph

    G = nx.Graph()

    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            founders_db = []
            for name in founder_names:
                founder_user = find_user_by_name(db, name)
                if founder_user:
                    founders_db.append(founder_user)

            for f in founders_db:
                f_id = f["user_id"]
                G.add_node(f_id, label=f["name"], type="founder")

                # University
                uni = f["profile"].get("university") or f["roster"].get("university")
                if uni and uni.lower() not in ("others", "none", ""):
                    G.add_node(uni, label=uni, type="university")
                    G.add_edge(f_id, uni, relationship="studied_at")

                    # Classmates (limit to 5)
                    classmates = db.execute("""
                        SELECT user_id, roster_json FROM people
                        WHERE (json_extract(profile_json, '$.university') = ?
                           OR json_extract(roster_json, '$.university') = ?)
                          AND user_id != ? LIMIT 5
                    """, (uni, uni, f_id)).fetchall()
                    for c_id, c_roster_json in classmates:
                        c_roster = _json(c_roster_json)
                        c_first = (c_roster.get("first_name") or "").strip()
                        c_last = (c_roster.get("last_name") or "").strip()
                        c_name = " ".join(part for part in (c_first, c_last) if part) or c_roster.get("display_name") or "Alumni"
                        G.add_node(c_id, label=c_name, type="person")
                        G.add_edge(c_id, uni, relationship="studied_at")

                # Projects
                projects = db.execute("""
                    SELECT p.project_id, p.title, p.project_json, pp.relationship
                    FROM project_people pp
                    JOIN projects p ON p.project_id = pp.project_id
                    WHERE pp.user_id = ?
                """, (f_id,)).fetchall()
                for p_id, p_title, p_json_str, rel in projects:
                    G.add_node(p_id, label=p_title or "Untitled Project", type="project")
                    G.add_edge(f_id, p_id, relationship=rel)

                    # Teammates
                    teammates = db.execute("""
                        SELECT pp.user_id, pp.relationship, json_extract(pe.roster_json, '$.display_name'), json_extract(pe.roster_json, '$.first_name'), json_extract(pe.roster_json, '$.last_name')
                        FROM project_people pp
                        JOIN people pe ON pe.user_id = pp.user_id
                        WHERE pp.project_id = ? AND pp.user_id != ?
                    """, (p_id, f_id)).fetchall()
                    for t_id, t_rel, t_disp, t_first, t_last in teammates:
                        t_name = " ".join(part for part in (t_first, t_last) if part) or t_disp or "Teammate"
                        G.add_node(t_id, label=t_name, type="person")
                        G.add_edge(t_id, p_id, relationship=t_rel)

                    # Hackathon
                    p_json = _json(p_json_str)
                    event_title = p_json.get("eventTitle")
                    if event_title:
                        G.add_node(event_title, label=event_title, type="hackathon")
                        G.add_edge(p_id, event_title, relationship="part_of_event")

                        # Other hackathon projects (limit to 5)
                        other_projs = db.execute("""
                            SELECT project_id, title FROM projects
                            WHERE json_extract(project_json, '$.eventTitle') = ?
                              AND project_id != ? LIMIT 5
                        """, (event_title, p_id)).fetchall()
                        for op_id, op_title in other_projs:
                            G.add_node(op_id, label=op_title or "Hackathon Project", type="project")
                            G.add_edge(op_id, event_title, relationship="part_of_event")

            # Convert networkx graph to D3 JSON format
            graph_data = json_graph.node_link_data(G)
            return graph_data
    except (sqlite3.Error, OSError) as exc:
        raise HTTPException(status_code=500, detail="Database error during network generation") from exc


class HistoricalScoreModel(BaseModel):
    timestamp: str
    score: float


class DetailedPersonModel(BaseModel):
    id: str
    name: str
    firstName: str | None = None
    lastName: str | None = None
    avatarUrl: str | None = None
    tagline: str | None = None
    university: str | None = None
    fieldOfStudy: str | None = None
    academicDegree: str | None = None
    graduationYear: str | None = None
    professionalSituation: str | None = None
    country: str | None = None
    city: str | None = None
    nationality: str | None = None
    githubUrl: str | None = None
    linkedinUrl: str | None = None
    careerOpportunities: str | None = None
    passionHobby: str | None = None
    activeFounderScore: float | None = None
    projects: list[PersonProjectModel]


class NetworkNodeModel(BaseModel):
    id: str
    label: str
    type: str


class NetworkEdgeModel(BaseModel):
    source: str
    target: str
    relationship: str | None = None


class PersonNetworkModel(BaseModel):
    directed: bool
    multigraph: bool
    graph: dict[str, Any]
    nodes: list[NetworkNodeModel]
    edges: list[NetworkEdgeModel]


@router.get("/people/{user_id}", response_model=DetailedPersonModel)
def get_person_profile(user_id: str) -> dict[str, Any]:
    import re
    if not re.match(r"^[a-f0-9-]{36}$", user_id, re.IGNORECASE):
        raise HTTPException(status_code=422, detail="Invalid user_id format")
    
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="People directory is unavailable")
        
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            row = db.execute("SELECT roster_json, profile_json FROM people WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Person not found")
            
            roster = _json(row[0])
            profile = _json(row[1])
            person = {**roster, **profile}
            
            # Active founder score (most recent)
            score_row = db.execute("SELECT score FROM founder_scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,)).fetchone()
            active_score = score_row[0] if score_row else 0.0
            
            first = (person.get("first_name") or "").strip() or None
            last = (person.get("last_name") or "").strip() or None
            
            projects = []
            for project_id, relationship, project_json in db.execute("""
                SELECT pp.project_id, pp.relationship, p.project_json 
                FROM project_people pp 
                JOIN projects p ON p.project_id = pp.project_id 
                WHERE pp.user_id = ? 
                ORDER BY p.title COLLATE NOCASE
            """, (user_id,)):
                project = _json(project_json)
                projects.append({
                    "id": project_id,
                    "title": project.get("title"),
                    "relationship": relationship,
                    "completed": _completed(project)
                })
                
            return {
                "id": user_id,
                "name": " ".join(part for part in (first, last) if part) or person.get("display_name") or "Unknown person",
                "firstName": first,
                "lastName": last,
                "avatarUrl": person.get("avatar_url"),
                "tagline": person.get("tagline"),
                "university": person.get("university"),
                "fieldOfStudy": person.get("field_of_study"),
                "academicDegree": person.get("academic_degree"),
                "graduationYear": person.get("graduation_year"),
                "professionalSituation": person.get("professional_situation"),
                "country": person.get("country"),
                "city": person.get("city"),
                "nationality": person.get("nationality"),
                "githubUrl": person.get("github_url"),
                "linkedinUrl": person.get("linkedin_url"),
                "careerOpportunities": person.get("career_opportunities"),
                "passionHobby": person.get("passion_hobby"),
                "activeFounderScore": active_score,
                "projects": projects
            }
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.get("/people/{user_id}/scores", response_model=list[HistoricalScoreModel])
def get_person_scores(user_id: str) -> list[dict[str, Any]]:
    import re
    if not re.match(r"^[a-f0-9-]{36}$", user_id, re.IGNORECASE):
        raise HTTPException(status_code=422, detail="Invalid user_id format")
        
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file():
        return []
        
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            rows = db.execute("SELECT timestamp, score FROM founder_scores WHERE user_id = ? ORDER BY timestamp ASC", (user_id,)).fetchall()
            return [{"timestamp": r[0], "score": r[1]} for r in rows]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.get("/people/{user_id}/network", response_model=PersonNetworkModel)
def get_person_network(user_id: str) -> dict[str, Any]:
    import re
    if not re.match(r"^[a-f0-9-]{36}$", user_id, re.IGNORECASE):
        raise HTTPException(status_code=422, detail="Invalid user_id format")
        
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file():
        return {"directed": False, "multigraph": False, "graph": {}, "nodes": [], "edges": []}
        
    import networkx as nx
    from networkx.readwrite import json_graph
    
    G = nx.Graph()
    
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            row = db.execute("SELECT roster_json, profile_json FROM people WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Person not found")
                
            roster = _json(row[0])
            profile = _json(row[1])
            person = {**roster, **profile}
            first = (person.get("first_name") or "").strip()
            last = (person.get("last_name") or "").strip()
            name = " ".join(part for part in (first, last) if part) or person.get("display_name") or "Center Person"
            
            # Root Node
            G.add_node(user_id, label=name, type="founder")
            
            # University
            uni = person.get("university")
            if uni and uni.lower() not in ("others", "none", ""):
                G.add_node(uni, label=uni, type="university")
                G.add_edge(user_id, uni, relationship="studied_at")
                
                # Classmates (limit to 5)
                classmates = db.execute("""
                    SELECT user_id, roster_json FROM people
                    WHERE (json_extract(profile_json, '$.university') = ?
                       OR json_extract(roster_json, '$.university') = ?)
                      AND user_id != ? LIMIT 5
                """, (uni, uni, user_id)).fetchall()
                for c_id, c_roster_json in classmates:
                    c_roster = _json(c_roster_json)
                    c_first = (c_roster.get("first_name") or "").strip()
                    c_last = (c_roster.get("last_name") or "").strip()
                    c_name = " ".join(part for part in (c_first, c_last) if part) or c_roster.get("display_name") or "Alumni"
                    G.add_node(c_id, label=c_name, type="person")
                    G.add_edge(c_id, uni, relationship="studied_at")
                    
            # Projects
            projects = db.execute("""
                SELECT p.project_id, p.title, p.project_json, pp.relationship
                FROM project_people pp
                JOIN projects p ON p.project_id = pp.project_id
                WHERE pp.user_id = ?
            """, (user_id,)).fetchall()
            for p_id, p_title, p_json_str, rel in projects:
                G.add_node(p_id, label=p_title or "Untitled Project", type="project")
                G.add_edge(user_id, p_id, relationship=rel)
                
                # Teammates
                teammates = db.execute("""
                    SELECT pp.user_id, pp.relationship, json_extract(pe.roster_json, '$.display_name'), json_extract(pe.roster_json, '$.first_name'), json_extract(pe.roster_json, '$.last_name')
                    FROM project_people pp
                    JOIN people pe ON pe.user_id = pp.user_id
                    WHERE pp.project_id = ? AND pp.user_id != ?
                """, (p_id, user_id)).fetchall()
                for t_id, t_rel, t_disp, t_first, t_last in teammates:
                    t_name = " ".join(part for part in (t_first, t_last) if part) or t_disp or "Teammate"
                    G.add_node(t_id, label=t_name, type="person")
                    G.add_edge(t_id, p_id, relationship=t_rel)
                    
                # Hackathon
                p_json = _json(p_json_str)
                event_title = p_json.get("eventTitle")
                if event_title:
                    G.add_node(event_title, label=event_title, type="hackathon")
                    G.add_edge(p_id, event_title, relationship="part_of_event")
                    
                    # Other hackathon projects (limit to 5)
                    other_projs = db.execute("""
                        SELECT project_id, title FROM projects
                        WHERE json_extract(project_json, '$.eventTitle') = ?
                          AND project_id != ? LIMIT 5
                    """, (event_title, p_id)).fetchall()
                    for op_id, op_title in other_projs:
                        G.add_node(op_id, label=op_title or "Hackathon Project", type="project")
                        G.add_edge(op_id, event_title, relationship="part_of_event")
                        
            return json_graph.node_link_data(G)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc


def init_db() -> None:
    configured = os.getenv("SV_PEOPLE_DATABASE")
    path = (Path(configured) if configured else _ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite").resolve()
    if not path.is_file():
        return
    try:
        with sqlite3.connect(path.as_posix()) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS founder_scores (
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    score REAL NOT NULL,
                    PRIMARY KEY (user_id, timestamp),
                    FOREIGN KEY (user_id) REFERENCES people(user_id) ON DELETE CASCADE
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS founder_scores_user_id_idx ON founder_scores(user_id)")
            
            # Check if empty
            cursor = db.execute("SELECT COUNT(*) FROM founder_scores")
            count = cursor.fetchone()[0]
            if count == 0:
                seed_data = [
                    # Akshat Tandon
                    ("02887d15-7eac-40f7-836d-4a7a23031b5a", "2026-01-15T09:00:00Z", 20.0),
                    ("02887d15-7eac-40f7-836d-4a7a23031b5a", "2026-03-20T12:00:00Z", 45.0),
                    ("02887d15-7eac-40f7-836d-4a7a23031b5a", "2026-06-15T15:00:00Z", 75.0),
                    # Binhui Shao
                    ("363138b8-d565-429f-9f06-f18e8bd1f848", "2026-01-15T09:00:00Z", 25.0),
                    ("363138b8-d565-429f-9f06-f18e8bd1f848", "2026-04-01T14:30:00Z", 55.0),
                    ("363138b8-d565-429f-9f06-f18e8bd1f848", "2026-06-18T10:00:00Z", 80.0),
                    # Ayoub Azmal
                    ("d3c69d34-7956-4fdb-b893-409cee5836d6", "2026-01-01T10:00:00Z", 15.0),
                    ("d3c69d34-7956-4fdb-b893-409cee5836d6", "2026-02-15T18:00:00Z", 35.0),
                    ("d3c69d34-7956-4fdb-b893-409cee5836d6", "2026-05-10T12:00:00Z", 60.0),
                    ("d3c69d34-7956-4fdb-b893-409cee5836d6", "2026-07-01T11:00:00Z", 92.0),
                    # Nico Suter
                    ("7b592d6e-2613-4c0b-9400-f3962c03e621", "2026-01-10T08:00:00Z", 30.0),
                    ("7b592d6e-2613-4c0b-9400-f3962c03e621", "2026-05-05T13:00:00Z", 65.0),
                    # Moad Larabi
                    ("a5b1263b-7e12-4a24-8616-6877413e5051", "2026-01-20T10:00:00Z", 10.0),
                    ("a5b1263b-7e12-4a24-8616-6877413e5051", "2026-03-10T11:00:00Z", 38.0),
                    ("a5b1263b-7e12-4a24-8616-6877413e5051", "2026-06-05T14:00:00Z", 62.0),
                    # Elsa Nisa
                    ("adf92aaa-2b96-4753-97c5-53665fe7ad5c", "2026-01-25T09:00:00Z", 40.0),
                    ("adf92aaa-2b96-4753-97c5-53665fe7ad5c", "2026-04-12T13:00:00Z", 70.0),
                    ("adf92aaa-2b96-4753-97c5-53665fe7ad5c", "2026-07-01T15:00:00Z", 88.0),
                ]
                db.executemany("INSERT INTO founder_scores (user_id, timestamp, score) VALUES (?, ?, ?)", seed_data)
                db.commit()
    except Exception as exc:
        print(f"Error seeding founder_scores: {exc}")



