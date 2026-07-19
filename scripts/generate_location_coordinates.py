#!/usr/bin/env python3
"""Build the reviewed location seed from the people DB and GeoNames cities500.

The application never calls a geocoder.  Maintainers download ``cities500.zip``
from https://download.geonames.org/export/dump/ and run this script explicitly.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.core.location_coordinates import normalize_location_component  # noqa: E402


COUNTRY_CODES = {
    "afghanistan": "AF", "albania": "AL", "argentina": "AR", "armenia": "AM",
    "australia": "AU", "austria": "AT", "bangladesh": "BD", "belgium": "BE",
    "bolivia": "BO", "brazil": "BR", "canada": "CA", "colombia": "CO",
    "congo (democratic republic)": "CD", "cyprus": "CY", "denmark": "DK",
    "egypt": "EG", "england": "GB", "ethiopia": "ET", "finland": "FI",
    "france": "FR", "gambia": "GM", "germany": "DE", "greece": "GR", "hungary": "HU",
    "india": "IN", "indonesia": "ID", "ireland": "IE", "italy": "IT",
    "jordan": "JO", "kenya": "KE", "madagascar": "MG", "malaysia": "MY",
    "maroc": "MA", "mexico": "MX", "méxico": "MX", "morocco": "MA",
    "morroco": "MA", "mroco": "MA", "nepal": "NP", "netherlands": "NL",
    "the netherlands": "NL", "niger": "NE", "nigeria": "NG", "oman": "OM",
    "pakistan": "PK", "peru": "PE", "qatar": "QA", "romania": "RO",
    "russia": "RU", "rwanda": "RW", "saudi arabia": "SA", "singapore": "SG",
    "south africa": "ZA", "south korea": "KR", "spain": "ES", "sri lanka": "LK",
    "sudan": "SD", "sweden": "SE", "switzerland": "CH", "tunisia": "TN",
    "uae": "AE", "uk": "GB", "ukraine": "UA", "united arab emirates": "AE",
    "united kingdom": "GB", "united states": "US", "united states of america": "US",
    "usa": "US", "us": "US",
}

CITY_ALIASES = {
    "banglore": "bengaluru",
    "bengalore": "bengaluru",
    "bhubaneshwar": "bhubaneswar",
    "bhubneshwar": "bhubaneswar",
    "boston, ma": "boston",
    "cdmx": "mexico city",
    "jaipur rajasthan": "jaipur",
    "granville, oh": "granville",
    "haroonabad": "harunabad",
    "hillsborough, new jersey": "hillsborough",
    "karachi, pakistan.": "karachi",
    "lagos state": "lagos",
    "mardan, khyber pakhtunkhwa, pakistan": "mardan",
    "naushahro feroze, sindh, pakistan": "naushahro firoz",
    "new delhi, delhi": "new delhi",
    "new york": "new york city",
    "rabat, rabat-salé-kénitra": "rabat",
    "pucheng": "puchong",
    "são paulo - capital": "são paulo",
    "yaba": "lagos",
}

CITY_ADMIN1 = {
    "boston, ma": "MA",
    "granville, oh": "OH",
    "hillsborough, new jersey": "NJ",
}


def repair_mojibake(value: str) -> str:
    """Repair the UTF-8-as-Latin-1 strings present in the source export."""

    repaired = value
    for _ in range(2):
        if not any(marker in repaired for marker in ("Ã", "Ä", "Å", "Â", "�")):
            break
        try:
            candidate = repaired.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == repaired:
            break
        repaired = candidate
    return unicodedata.normalize("NFC", repaired)


def load_location_pairs(database: Path) -> dict[tuple[str, str], tuple[str, str]]:
    pairs: dict[tuple[str, str], tuple[str, str]] = {}
    with sqlite3.connect(database) as db:
        for (profile_json,) in db.execute("SELECT profile_json FROM people"):
            profile = json.loads(profile_json or "{}")
            city = profile.get("city")
            country = profile.get("country")
            if not isinstance(city, str) or not city.strip() or not isinstance(country, str) or not country.strip():
                continue
            city = " ".join(city.split())
            country = " ".join(country.split())
            key = (normalize_location_component(city), normalize_location_component(country))
            pairs.setdefault(key, (city, country))
    return pairs


def load_geonames(
    archive: Path,
) -> tuple[
    dict[tuple[str, str], list[dict[str, object]]],
    dict[tuple[str, str], list[dict[str, object]]],
]:
    canonical_index: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    alternate_index: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    with zipfile.ZipFile(archive) as zipped:
        dump_name = next(name for name in zipped.namelist() if name.endswith(".txt"))
        with zipped.open(dump_name) as raw:
            for encoded_line in raw:
                fields = encoded_line.decode("utf-8").rstrip("\n").split("\t")
                if len(fields) < 19:
                    continue
                record = {
                    "geoname_id": int(fields[0]), "name": fields[1],
                    "latitude": float(fields[4]), "longitude": float(fields[5]),
                    "country_code": fields[8], "admin1": fields[10],
                    "population": int(fields[14] or 0),
                }
                canonical_names = {fields[1], fields[2]}
                for name in canonical_names:
                    if name:
                        canonical_index[(fields[8], normalize_location_component(name))].append(record)
                for name in fields[3].split(",") if fields[3] else []:
                    if name and name not in canonical_names:
                        alternate_index[(fields[8], normalize_location_component(name))].append(record)
    return canonical_index, alternate_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "assets" / "DATABASE" / "hack_nation_people.sqlite")
    parser.add_argument("--geonames-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "DATABASE" / "location_coordinates.csv")
    args = parser.parse_args()

    pairs = load_location_pairs(args.database)
    canonical_index, alternate_index = load_geonames(args.geonames_zip)
    fieldnames = [
        "city_key", "country_key", "city", "country", "latitude", "longitude",
        "status", "source", "geoname_id", "match_name", "notes",
    ]
    rows = []
    resolved = 0
    for (city_key, country_key), (city, country) in sorted(pairs.items()):
        country_code = COUNTRY_CODES.get(normalize_location_component(repair_mojibake(country)))
        repaired_city = normalize_location_component(repair_mojibake(city))
        query_city = CITY_ALIASES.get(repaired_city, repaired_city)
        required_admin1 = CITY_ADMIN1.get(repaired_city)
        matches = canonical_index.get((country_code or "", query_city), [])
        match_kind = "canonical/ascii"
        if required_admin1:
            matches = [match for match in matches if match["admin1"] == required_admin1]
        if not matches:
            alternate_matches = alternate_index.get((country_code or "", query_city), [])
            if required_admin1:
                alternate_matches = [
                    match for match in alternate_matches if match["admin1"] == required_admin1
                ]
            by_id = {int(match["geoname_id"]): match for match in alternate_matches}
            matches = list(by_id.values()) if len(by_id) == 1 else []
            match_kind = "unambiguous alternate-name"
        best = max(
            matches,
            key=lambda item: (int(item["population"]), -int(item["geoname_id"])),
        ) if matches else None
        row = {
            "city_key": city_key, "country_key": country_key, "city": city, "country": country,
            "latitude": "", "longitude": "", "status": "unresolved",
            "source": "GeoNames cities500", "geoname_id": "", "match_name": "",
            "notes": "No exact city/country match; review required",
        }
        if best:
            row.update({
                "latitude": best["latitude"], "longitude": best["longitude"],
                "status": "resolved", "geoname_id": best["geoname_id"],
                "match_name": best["name"],
                "notes": f"{match_kind} match"
                + (f" constrained to admin1={required_admin1}" if required_admin1 else ""),
            })
            resolved += 1
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} location pairs: {resolved} resolved, {len(rows) - resolved} unresolved")


if __name__ == "__main__":
    main()
