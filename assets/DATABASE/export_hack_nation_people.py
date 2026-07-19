#!/usr/bin/env python3
"""Export the public Hack-Nation people directory to a JSON file.

Only use this for information that the site intentionally exposes publicly.
The output contains the unmodified public API responses plus an ISO-8601
timestamp, so it can be re-imported or audited later.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://projects.hack-nation.ai/.netlify/functions"
PEOPLE_URL = f"{BASE}/bff-public-people-v2"
PROFILES_URL = f"{BASE}/bff-public-profiles-v2"
PROJECTS_URL = f"{BASE}/bff-projects-public-v2"


def get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "public-directory-export/1.0"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (HTTPError, URLError) as error:
            if attempt == 3:
                raise
            delay = 1.0 * (2**attempt)
            print(f"Request failed ({error}); retrying in {delay:.0f}s")
            time.sleep(delay)
    raise AssertionError("unreachable")


def get_all_projects() -> tuple[list[dict], list[dict]]:
    """Follow the public endpoint's offset pagination (it caps pages at 100)."""
    projects: list[dict] = []
    pages: list[dict] = []
    offset = 0
    while True:
        try:
            response = get_json(f"{PROJECTS_URL}?{urlencode({'limit': 100, 'offset': offset})}")
        except (HTTPError, URLError) as error:
            # The public backend currently returns 502 after its last page
            # instead of an empty page. Preserve all successfully read pages.
            print(f"Project pagination stopped at offset {offset}: {error}")
            break
        page = response.get("data", response)
        if not isinstance(page, list):
            raise ValueError("Unexpected projects API response: expected a list in data")
        pages.append(response)
        projects.extend(page)
        if len(page) < 100:
            break
        offset += len(page)
    return projects, pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Export public Hack-Nation people and profile records.")
    parser.add_argument("--output", default="hack_nation_people_raw.json", type=Path)
    parser.add_argument("--batch-size", default=100, type=int, help="Profiles requested per API call (1-250).")
    parser.add_argument("--pause", default=0.1, type=float, help="Seconds between profile batches.")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 250:
        parser.error("--batch-size must be between 1 and 250")

    roster_response = get_json(f"{PEOPLE_URL}?{urlencode({'limit': 5000})}")
    roster = roster_response.get("data", {})
    people = roster.get("people", [])
    user_ids = [person["user_id"] for person in people if person.get("user_id")]

    profiles: list[dict] = []
    for start in range(0, len(user_ids), args.batch_size):
        batch = user_ids[start : start + args.batch_size]
        query = urlencode({"userIds": batch, "limit": len(batch)}, doseq=True)
        response = get_json(f"{PROFILES_URL}?{query}")
        profiles.extend(response.get("data", []))
        print(f"Fetched {min(start + len(batch), len(user_ids))}/{len(user_ids)} profiles")
        if start + len(batch) < len(user_ids):
            time.sleep(args.pause)

    # The people endpoint contains only project id/title references.  Request
    # every public-project page, then ensure each profile-linked project is
    # present even if the general listing has changed during this export.
    projects, project_pages = get_all_projects()
    project_ids = {project.get("id") for project in projects}
    linked_ids = {
        contribution.get("id")
        for entries in roster.get("contributionsByUserId", {}).values()
        for contribution in (entries or [])
        if isinstance(contribution, dict) and contribution.get("id")
    }
    for project_id in sorted(linked_ids - project_ids):
        response = get_json(f"{PROJECTS_URL}?{urlencode({'id': project_id})}")
        project = response.get("data", response)
        if isinstance(project, dict) and project.get("id"):
            projects.append(project)

    projects_response = {"data": projects, "pages": project_pages}

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": {"people": PEOPLE_URL, "profiles": PROFILES_URL, "projects": PROJECTS_URL},
        "roster_response": roster_response,
        "profiles": profiles,
        "projects_response": projects_response,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(people)} people, {len(profiles)} full profiles, and {len(projects)} projects to {args.output}")


if __name__ == "__main__":
    main()
