#!/usr/bin/env python3
"""Check compatible-cohort control readiness for M9EDGEPLACEMENT1A.

Research-only. Broad historical controls are useful, but a failure tail from a
newer diagnostic/capture generation must also be challenged by controls from a
compatible build/schema cohort. Otherwise a rule may separate software version
rather than photographic placement.

Cohort priority:
1. exact `cohortKey` attached by m9edgeplacement1a_cohort_metadata.py
   (build + scene schema + render-meter schema + frozen renderer schema);
2. `cohortSchemaKey` when build version is unavailable;
3. capture date parsed from IMG_YYYYMMDD_* only as a conservative fallback.

Cohort identity is an evaluation guard only. It is never a placement feature.
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


def cohort_identity(row: dict[str, str]) -> tuple[str, str]:
    exact = (row.get("cohortKey") or "").strip()
    if exact:
        return "build_schema", exact
    schema = (row.get("cohortSchemaKey") or "").strip()
    if schema:
        return "schema", schema
    date = capture_date(row)
    if date:
        return "date_fallback", date
    return "unknown", ""


def compatible(row: dict[str, str], kind: str, value: str) -> bool:
    rkind, rvalue = cohort_identity(row)
    return bool(value) and rkind == kind and rvalue == value


def short_identity(kind: str, value: str, limit: int = 220) -> str:
    raw = f"{kind}:{value}"
    return raw if len(raw) <= limit else raw[:limit - 3] + "..."


def evaluate(rows: list[dict[str, str]], min_compatible_good: int, min_compatible_boundary: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema": "m9edgeplacement1a.cohortreadiness.v2",
        "mode": "research_only_build_schema_preferred_date_fallback",
        "thresholds": {
            "minimumCompatibleGood": min_compatible_good,
            "minimumCompatibleBoundary": min_compatible_boundary,
            "minimumTargetPerCohort": 2,
        },
        "cohortPriority": ["cohortKey", "cohortSchemaKey", "captureDateFallback"],
        "targets": {},
        "invariant": "Historical controls improve diversity but cannot by themselves validate a rule against a different build/schema cohort.",
    }

    for target in TARGETS:
        target_rows = [r for r in rows if label_of(r) == target]
        identities = sorted({cohort_identity(r) for r in target_rows if cohort_identity(r)[1]})
        results = []
        for kind, value in identities:
            target_n = sum(label_of(r) == target and compatible(r, kind, value) for r in rows)
            good_n = sum(label_of(r) == "GOOD" and compatible(r, kind, value) for r in rows)
            boundary_n = sum(label_of(r) == "BOUNDARY" and compatible(r, kind, value) for r in rows)
            ready = (
                target_n >= 2
                and good_n >= min_compatible_good
                and boundary_n >= min_compatible_boundary
            )
            results.append({
                "cohortKind": kind,
                "cohortIdentity": value,
                "cohortDisplay": short_identity(kind, value),
                "targetN": target_n,
                "compatibleGoodN": good_n,
                "compatibleBoundaryN": boundary_n,
                "ready": ready,
                "missing": {
                    "good": max(0, min_compatible_good - good_n),
                    "boundary": max(0, min_compatible_boundary - boundary_n),
                    "target": max(0, 2 - target_n),
                },
            })

        unknown_target_n = sum(
            label_of(r) == target and cohort_identity(r)[0] == "unknown" for r in rows
        )
        fallback_target_n = sum(
            label_of(r) == target and cohort_identity(r)[0] == "date_fallback" for r in rows
        )
        summary["targets"][target] = {
            "targetN": len(target_rows),
            "cohortResults": results,
            "unknownCohortTargetN": unknown_target_n,
            "dateFallbackTargetN": fallback_target_n,
            "ready": bool(results) and unknown_target_n == 0 and all(r["ready"] for r in results),
            "note": (
                "Every represented target cohort must have compatible GOOD and BOUNDARY controls. "
                "Build/schema identity is preferred; date fallback is provisional only."
            ),
        }
    return summary


def self_test() -> None:
    rows: list[dict[str, str]] = []
    # Many historical GOODs from another build must not validate newer failures.
    for i in range(30):
        rows.append({
            "captureKey": f"IMG_20260902_1200{i:02d}_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=OLD|scene=s1|renderer=r1",
        })
    rows += [
        {
            "captureKey": "IMG_20260904_184927_x",
            "researchLabel": "BRIGHT_FAIL",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_184937_x",
            "researchLabel": "BRIGHT_FAIL",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
    ]
    s = evaluate(rows, 3, 1)
    assert s["targets"]["BRIGHT_FAIL"]["ready"] is False

    # Same-date but wrong-build controls still must not pass.
    rows += [
        {
            "captureKey": "IMG_20260904_100001_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=OTHER|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_100002_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=OTHER|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_100003_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=OTHER|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_100004_x",
            "researchLabel": "BOUNDARY",
            "cohortKey": "build=OTHER|scene=s2|renderer=r1",
        },
    ]
    s = evaluate(rows, 3, 1)
    assert s["targets"]["BRIGHT_FAIL"]["ready"] is False

    # Compatible build/schema controls make the target cohort ready.
    rows += [
        {
            "captureKey": "IMG_20260904_110001_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_110002_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_110003_x",
            "researchLabel": "GOOD",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
        {
            "captureKey": "IMG_20260904_110004_x",
            "researchLabel": "BOUNDARY",
            "cohortKey": "build=NEW|scene=s2|renderer=r1",
        },
    ]
    s = evaluate(rows, 3, 1)
    assert s["targets"]["BRIGHT_FAIL"]["ready"] is True

    # Date fallback still works for old data with no build/schema metadata.
    fallback = [
        {"captureKey": "IMG_20260904_180001_x", "researchLabel": "DARK_FAIL"},
        {"captureKey": "IMG_20260904_180002_x", "researchLabel": "DARK_FAIL"},
        {"captureKey": "IMG_20260904_100001_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100002_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100003_x", "researchLabel": "GOOD"},
        {"captureKey": "IMG_20260904_100004_x", "researchLabel": "BOUNDARY"},
    ]
    s = evaluate(fallback, 3, 1)
    assert s["targets"]["DARK_FAIL"]["ready"] is True
    assert s["targets"]["DARK_FAIL"]["dateFallbackTargetN"] == 2
    print("M9EDGEPLACEMENT1A cohort-readiness self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path,
                    help="cohort-augmented edge feature CSV")
    ap.add_argument("--out", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_RESULTS/cohort_readiness.json"))
    ap.add_argument("--min-compatible-good", type=int, default=10)
    ap.add_argument("--min-compatible-boundary", type=int, default=2)
    # Backward-compatible aliases for the previous date-proxy CLI.
    ap.add_argument("--min-same-date-good", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--min-same-date-boundary", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.features:
        ap.error("--features required unless --self-test")

    min_good = a.min_same_date_good if a.min_same_date_good is not None else a.min_compatible_good
    min_boundary = (
        a.min_same_date_boundary
        if a.min_same_date_boundary is not None
        else a.min_compatible_boundary
    )
    if min_good < 1 or min_boundary < 0:
        ap.error("invalid cohort minima")

    summary = evaluate(read_csv(a.features), min_good, min_boundary)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
