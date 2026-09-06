#!/usr/bin/env python3
"""LOWKEY_BOUNDARYBAND1A research classifier.

Read-only overlay for BRIGHT_LOWKEY_OPENING1A. It does not change the existing
0.60 selector. Frames that satisfy intent/gain/finished-body requirements but
fall in 0.50 <= structuralLowKeyScore < 0.60 are labelled BOUNDARY_HOLD so they
can be collected prospectively while remaining Frozen.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import importlib.util

STRONG_MIN = 0.60
BOUNDARY_MIN = 0.50


def load_auditor(path: Path):
    spec = importlib.util.spec_from_file_location("lowkey_audit1a", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load cohort auditor")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify(row):
    intent_ok = row.get("achievedIntentEv") is not None and row["achievedIntentEv"] < 0.10
    gain_ok = row.get("tc20Gain") is not None and row["tc20Gain"] >= 1.50
    body_ok = row.get("finishedGlobalMedianY") is not None and row["finishedGlobalMedianY"] >= 75.0
    score = row.get("structuralLowKeyScore")
    base_ok = intent_ok and gain_ok and body_ok and score is not None
    if not base_ok:
        return "OFF"
    if score >= STRONG_MIN:
        return "STRONG_CANDIDATE"
    if score >= BOUNDARY_MIN:
        return "BOUNDARY_HOLD"
    return "OFF"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--auditor", type=Path,
                    default=Path(__file__).with_name("m9edgeplacementbestfit1a_bright_lowkey_cohort_audit1a.py"))
    args = ap.parse_args()
    audit = load_auditor(args.auditor).audit(args.root)
    rows = []
    for row in audit["rows"]:
        r = dict(row)
        r["boundaryBandState"] = classify(r)
        rows.append(r)
    strong = [r["frame"] for r in rows if r["boundaryBandState"] == "STRONG_CANDIDATE"]
    boundary = [r["frame"] for r in rows if r["boundaryBandState"] == "BOUNDARY_HOLD"]
    print(json.dumps({
        "schema": "m9edgeplacementbestfit1a.bright_lowkey_boundaryband1a.research.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "selectorUnchanged": True,
        "strongThreshold": STRONG_MIN,
        "boundaryThreshold": BOUNDARY_MIN,
        "strongCandidates": strong,
        "boundaryHold": boundary,
        "rows": rows,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
