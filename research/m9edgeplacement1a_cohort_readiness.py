#!/usr/bin/env python3
"""Check same-cohort control readiness for M9EDGEPLACEMENT1A.

Research-only. Broad historical controls are useful, but a failure tail from a
newer diagnostic/capture generation must also be challenged by controls from the
same field cohort. Otherwise a rule may separate build/date rather than
photographic placement.

Current practical cohort key is capture date parsed from `IMG_YYYYMMDD_*`.
This is intentionally conservative and can later be strengthened with build or
schema identity once those strings are emitted by the replay harness.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

TARGETS = ("BRIGHT_FAIL", "DARK_FAIL")
DATE_RE = re.compile(r"IMG_(\d{8})_")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def label_of(row: dict[str, str]) -> str:
    return (row.get("researchLabel") or row.get("label") or "").strip().upper()


def capture_date(row: dict[str, str]) -> str:
    key = (row.get("captureKey") or row.get("key") or row.get("frame") or "").strip()
    m = DATE_RE.search(key)
    return m.group(1) if m else ""


def evaluate(rows: list[dict[str, str]], min_same_date_good: int, min_same_date_boundary: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema": "m9edgeplacement1a.cohortreadiness.v1",
        "mode": "research_only_same_capture_date_proxy",
        "thresholds": {
            "minimumSameDateGood": min_same_date_good,
            "minimumSameDateBoundary": min_same_date_boundary,
        },
        "targets": {},
        "invariant": "Historical controls improve diversity but cannot by themselves validate a rule against a newer failure cohort.",
    }

    for target in TARGETS:
        target_rows = [r for r in rows if label_of(r) == target]
        dates = sorted({capture_date(r) for r in target_rows if capture_date(r)})
        date_results = []
        for date in dates:
            good = sum(label_of(r) == "GOOD" and capture_date(r) == date for r in rows)
            boundary = sum(label_of(r) == "BOUNDARY" and capture_date(r) == date for r in rows)
            positives = sum(label_of(r) == target and capture_date(r) == date for r in rows)
            ready = good >= min_same_date_good and boundary >= min_same_date_boundary and positives >= 2
            date_results.append({
                "date": date,
                "targetN": positives,
                "sameDateGoodN": good,
                "sameDateBoundaryN": boundary,
                "ready": ready,
                "missing": {
                    "good": max(0, min_same_date_good - good),
                    "boundary": max(0, min_same_date_boundary - boundary),
                    "target": max(0, 2 - positives),
                },
            })
        summary["targets"][target] = {
            "targetDates": dates,
            "dateResults": date_results,
            "ready": bool(date_results) and all(r["ready"] for r in date_results),
            "note": "No exact target date means not ready; each represented failure date must have same-date GOOD and BOUNDARY controls.",
        }
    return summary


def self_test() -> None:
    rows: list[dict[str, str]] = []
    # Many historical GOODs must not satisfy a newer bright-fail cohort.
    for i in range(30):
        rows.append({"captureKey": f"IMG_20260902_1200{i:02d}_x", "researchLabel": "GOOD"})
    rows += [
        {"captureKey": "IMG_20260904_184927_x", "researchLabel": "BRIGHT_FAIL"},
        {"captureKey": "IMG_20260904_184937_x", "researchLabel": "BRIGHT_FAIL"},
    ]
    s = evaluate(rows, 3, 1)
    assert s["targets"]["BRIGHT_FAIL"]["ready"] is False
    # Add same-date controls; now cohort readiness can pass.
    rows += [
        {"captureKey": "IMG_20260904_100001_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100002_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100003_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100004_x", "researchLabel": "BOUNDARY"},
    ]
    s = evaluate(rows, 3, 1)
    assert s["targets"]["BRIGHT_FAIL"]["ready"] is True
    print("M9EDGEPLACEMENT1A cohort-readiness self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path,
                    help="edge_features_research_labels.csv with exact joined capture keys")
    ap.add_argument("--out", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_RESULTS/cohort_readiness.json"))
    ap.add_argument("--min-same-date-good", type=int, default=10)
    ap.add_argument("--min-same-date-boundary", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.features:
        ap.error("--features required unless --self-test")
    if a.min_same_date_good < 1 or a.min_same_date_boundary < 0:
        ap.error("invalid cohort minima")
    summary = evaluate(read_csv(a.features), a.min_same_date_good, a.min_same_date_boundary)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
