#!/usr/bin/env python3
"""Validate deterministic evaluation fixtures without exposing raw source material."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.core.markdown import parse_evaluation_document
from src.core.integrity import fixture_sha256
from src.core.registry import CATEGORIES
from src.core.scoring import category_scores, overall_score


def _valid_investment_terms(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "amount", "currency", "equityPercentage", "preMoneyValuation",
        "postMoneyValuation", "impliedValuation", "useOfFunds",
    }:
        return False
    monetary = ("amount", "preMoneyValuation", "postMoneyValuation", "impliedValuation")
    if any(not isinstance(value[key], (int, float)) or isinstance(value[key], bool)
           or not math.isfinite(value[key]) or value[key] < 0 for key in monetary):
        return False
    equity = value["equityPercentage"]
    if (not isinstance(equity, (int, float)) or isinstance(equity, bool)
            or not math.isfinite(equity) or not 0 <= equity <= 100):
        return False
    if (not isinstance(value["currency"], str) or len(value["currency"]) != 3
            or not value["currency"].isalpha() or value["currency"] != value["currency"].upper()):
        return False
    funds = value["useOfFunds"]
    return isinstance(funds, list) and all(isinstance(item, str) and item.strip() for item in funds)


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    company_roots = sorted(path for path in root.iterdir() if path.is_dir())
    if len(company_roots) != 2:
        return [f"expected exactly two company directories, found {len(company_roots)}"]
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        failures.append("fixture manifest.json is missing")
    else:
        try:
            expected_hashes = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            actual_hashes = {
                str(path.relative_to(root)): fixture_sha256(path)
                for company in company_roots for path in company.rglob("*") if path.is_file()
            }
            if expected_hashes != dict(sorted(actual_hashes.items())):
                failures.append("fixture output hashes do not match manifest.json; regenerate fixtures")
        except (OSError, ValueError, KeyError, TypeError):
            failures.append("fixture manifest.json is malformed")
    for company in company_roots:
        documents = {}
        for category in CATEGORIES:
            file_path = company / "evaluation" / f"{company.name}_{category}.md"
            if not file_path.is_file():
                failures.append(f"{company.name}: missing {category} evaluation")
                continue
            result = parse_evaluation_document(file_path.read_text(encoding="utf-8"), company.name, category)
            if not result.is_valid:
                failures.extend(f"{company.name}/{category}: {issue.code} {issue.path}" for issue in result.errors)
            elif result.document:
                documents[category] = result.document.items
        metadata_path = company / "metadata.json"
        if not metadata_path.is_file():
            failures.append(f"{company.name}: metadata.json is missing")
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("state") != "ready": failures.append(f"{company.name}: metadata is not ready")
        terms = metadata.get("investment")
        if not _valid_investment_terms(terms):
            failures.append(f"{company.name}: investment terms are malformed")
        elif terms["amount"] != 100000:
            failures.append(f"{company.name}: example investment amount must be 100000")
        elif (terms["postMoneyValuation"] != terms["preMoneyValuation"] + terms["amount"]
              or terms["impliedValuation"] != terms["postMoneyValuation"]
              or terms["postMoneyValuation"] == 0
              or terms["equityPercentage"] != terms["amount"] / terms["postMoneyValuation"] * 100):
            failures.append(f"{company.name}: investment terms are internally inconsistent")
        if len(documents) == len(CATEGORIES):
            scores = category_scores(documents)
            if scores.get("home") is not None: failures.append(f"{company.name}: Home score must be unavailable")
            if metadata.get("category_scores") != scores: failures.append(f"{company.name}: category scores are not derived from artifacts")
            if metadata.get("overall_score") != overall_score(scores): failures.append(f"{company.name}: overall score is not derived from artifacts")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT / "tests/fixtures/companies")
    args = parser.parse_args()
    failures = validate(args.root)
    if failures:
        print("Evaluation validation failed:", *failures, sep="\n- ")
        return 1
    print("Validated two companies with five complete v1 evaluation documents each.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
