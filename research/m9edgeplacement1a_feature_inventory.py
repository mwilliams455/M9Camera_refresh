#!/usr/bin/env python3
"""Inventory EDGEPLACEMENT feature availability by label and diagnostic cohort.

Research-only. This tool does not search for a classifier and does not modify
capture, TC20, rendering, or JPEG pixels. It answers a narrower question:

    Which photographic features are actually present across GOOD, BOUNDARY,
    BRIGHT_FAIL and DARK_FAIL rows, and across which build/schema cohorts?

This is especially important because the frozen renderer stayed stable while
scene/render diagnostics evolved between field generations. A feature present
only in the newer failure build must not look artificially specific merely
because older GOOD controls contain blanks.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

LABELS = ("GOOD", "BOUNDARY", "BRIGHT_FAIL", "DARK_FAIL")
META = {
    "captureKey", "label", "labelNotes", "researchLabel", "researchM9ness",
    "researchNotes", "m9ness", "m9nessNotes", "sources", "sourceCount",
    "tc20Binding", "darkTailProbe", "brightLowKeyProbe",
    "cohortBuildVersion", "cohortInstrumentation", "cohortSceneSchema",
    "cohortRenderMeterSchema", "cohortRendererSchema", "cohortSchemaKey",
    "cohortKey", "cohortMetadataSourceCount",
}


def num(v: Any) -> float | None:
    try:
        if v is None or isinstance(v, bool) or v == "":
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def label_of(row: dict[str, str]) -> str:
    return (row.get("researchLabel") or row.get("label") or "").strip().upper()


def cohort_of(row: dict[str, str]) -> str:
    return (
        (row.get("cohortKey") or "").strip()
        or (row.get("cohortSchemaKey") or "").strip()
        or "UNSPECIFIED"
    )


def family(feature: str) -> str:
    if feature.startswith("capture"):
        return "capture"
    if feature.startswith("preview"):
        return "preview"
    if feature in {
        "structuralLowKeyScore", "lowKeyMedianEvidence",
        "lowKeyDarkBodyEvidence", "spatialAxisSeparationScore",
        "mfmAchievedIntentEv",
    }:
        return "scene_structure"
    if feature.startswith("tc20") or feature in {
        "baseMedianGain", "guardMarginAboveBaseEv",
    }:
        return "tc20"
    if feature.startswith("raw"):
        return "raw"
    if feature.startswith("render"):
        if feature in {
            "renderRgbChannelClipFraction", "renderNearWhiteFraction",
        }:
            return "renderer_legacy"
        return "render_meter"
    return "other"


def numeric_features(rows: list[dict[str, str]]) -> list[str]:
    keys = sorted({k for r in rows for k in r} - META)
    out = []
    for key in keys:
        if any(num(r.get(key)) is not None for r in rows):
            out.append(key)
    return out


def coverage(rows: list[dict[str, str]], feature: str, predicate) -> tuple[int, int, float | None]:
    cohort = [r for r in rows if predicate(r)]
    total = len(cohort)
    present = sum(num(r.get(feature)) is not None for r in cohort)
    return present, total, (present / total if total else None)


def label_inventory(rows: list[dict[str, str]], features: list[str]) -> list[dict[str, Any]]:
    out = []
    for feature in features:
        rec: dict[str, Any] = {"feature": feature, "family": family(feature)}
        active_labels = 0
        min_fraction = 1.0
        for label in LABELS:
            p, n, frac = coverage(rows, feature, lambda r, lab=label: label_of(r) == lab)
            rec[f"{label}_present"] = p
            rec[f"{label}_total"] = n
            rec[f"{label}_coverage"] = "" if frac is None else frac
            if n:
                active_labels += 1
                min_fraction = min(min_fraction, frac or 0.0)
        rec["representedLabelCount"] = active_labels
        rec["minimumRepresentedLabelCoverage"] = min_fraction if active_labels else ""
        out.append(rec)
    return out


def cohort_inventory(rows: list[dict[str, str]], features: list[str]) -> list[dict[str, Any]]:
    cohorts = sorted({cohort_of(r) for r in rows})
    out = []
    for feature in features:
        for cohort in cohorts:
            subset = [r for r in rows if cohort_of(r) == cohort]
            present = sum(num(r.get(feature)) is not None for r in subset)
            labels = sorted({label_of(r) for r in subset if label_of(r)})
            out.append({
                "feature": feature,
                "family": family(feature),
                "cohort": cohort,
                "present": present,
                "total": len(subset),
                "coverage": present / len(subset) if subset else "",
                "labelsPresent": " | ".join(labels),
            })
    return out


def feature_status(rows: list[dict[str, str]], feature: str, portable_min: float) -> str:
    represented = []
    for label in LABELS:
        p, n, frac = coverage(rows, feature, lambda r, lab=label: label_of(r) == lab)
        if n:
            represented.append((label, p, n, frac or 0.0))
    cohorts = sorted({cohort_of(r) for r in rows})
    cohort_fracs = []
    for cohort in cohorts:
        p, n, frac = coverage(rows, feature, lambda r, c=cohort: cohort_of(r) == c)
        if n:
            cohort_fracs.append((cohort, p, n, frac or 0.0))

    if not represented:
        return "NO_LABELLED_DATA"
    if len(cohort_fracs) >= 2 and all(frac >= portable_min for _, _, _, frac in cohort_fracs):
        return "PORTABLE_CANDIDATE"
    if len(cohort_fracs) >= 2 and any(frac == 0 for _, _, _, frac in cohort_fracs):
        return "COHORT_SPECIFIC"
    if len(cohort_fracs) == 1:
        return "SINGLE_COHORT_ONLY"
    return "PARTIAL_COVERAGE"


def self_test() -> None:
    rows = [
        {"researchLabel":"GOOD", "cohortKey":"old", "previewGlobalMedian":"80", "renderLiftNeedEvidence":""},
        {"researchLabel":"BOUNDARY", "cohortKey":"old", "previewGlobalMedian":"50", "renderLiftNeedEvidence":""},
        {"researchLabel":"GOOD", "cohortKey":"new", "previewGlobalMedian":"90", "renderLiftNeedEvidence":"0.1"},
        {"researchLabel":"BRIGHT_FAIL", "cohortKey":"new", "previewGlobalMedian":"95", "renderLiftNeedEvidence":"0.2"},
    ]
    assert feature_status(rows, "previewGlobalMedian", .8) == "PORTABLE_CANDIDATE"
    assert feature_status(rows, "renderLiftNeedEvidence", .8) == "COHORT_SPECIFIC"
    print("M9EDGEPLACEMENT1A feature-inventory self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, help="cohort-augmented edge feature CSV")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS"))
    ap.add_argument("--portable-min", type=float, default=0.80)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.features:
        ap.error("--features required unless --self-test")
    if not 0 <= a.portable_min <= 1:
        ap.error("--portable-min must be between 0 and 1")

    rows = read_csv(a.features)
    features = numeric_features(rows)
    by_label = label_inventory(rows, features)
    by_cohort = cohort_inventory(rows, features)
    status_rows = [
        {"feature": f, "family": family(f), "status": feature_status(rows, f, a.portable_min)}
        for f in features
    ]

    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "feature_coverage_by_label.csv", by_label)
    write_csv(a.out / "feature_coverage_by_cohort.csv", by_cohort)
    write_csv(a.out / "feature_portability_status.csv", status_rows)

    summary = {
        "schema": "m9edgeplacement1a.featureinventory.v1",
        "mode": "research_only_no_classifier_authority",
        "recordCount": len(rows),
        "featureCount": len(features),
        "cohortCount": len({cohort_of(r) for r in rows}),
        "labelCounts": {lab: sum(label_of(r) == lab for r in rows) for lab in LABELS},
        "statusCounts": {
            status: sum(r["status"] == status for r in status_rows)
            for status in sorted({r["status"] for r in status_rows})
        },
        "familyCounts": {
            fam: sum(r["family"] == fam for r in status_rows)
            for fam in sorted({r["family"] for r in status_rows})
        },
        "invariant": "PORTABLE_CANDIDATE means coverage compatibility only, never photographic validity or selector approval.",
    }
    (a.out / "feature_inventory_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
