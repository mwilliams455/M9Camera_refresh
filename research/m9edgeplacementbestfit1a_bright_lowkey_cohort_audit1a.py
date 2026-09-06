#!/usr/bin/env python3
"""M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY COHORT AUDIT1A.

Research-only prospective falsification tool. It pairs frozen capture metadata
(*_M9.json) with matching PRIMARY metadata (*_M9_PRIMARY.json), evaluates the
existing BRIGHT_LOWKEY_OPENING1A seed unchanged, and emits one row per frame
plus an activation/rejection summary.

It MUST NOT mutate capture exposure, TC20, renderer pixels, DNGs, JPEGs, curve02,
colour science, or any live camera path.

Current provisional seed (unchanged):

    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND tc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75

Thresholds are falsification seeds, not production constants.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

INTENT_MAX_EV = 0.10
LOWKEY_SCORE_MIN = 0.60
TC20_GAIN_MIN = 1.50
FINISHED_MEDIAN_MIN_Y = 75.0


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"top-level JSON is not an object: {path}")
    return obj


def get_path(obj: Dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def capture_stem(path: Path) -> str:
    name = path.name
    suffix = "_M9.json"
    if not name.endswith(suffix) or name.endswith("_M9_PRIMARY.json"):
        raise ValueError(f"not a capture M9 JSON: {path}")
    return name[:-len(suffix)]


def primary_path_for(capture_path: Path) -> Path:
    return capture_path.with_name(capture_stem(capture_path) + "_M9_PRIMARY.json")


def iter_capture_jsons(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*_M9.json")):
        if not path.name.endswith("_M9_PRIMARY.json"):
            yield path


def extract(capture: Dict[str, Any], primary: Dict[str, Any]) -> Dict[str, Any]:
    renderer = get_path(primary, "renderer")
    if not isinstance(renderer, dict):
        renderer = {}

    direct = renderer.get("directRenderedLuma")
    if not isinstance(direct, dict):
        direct = get_path(renderer, "renderMeterDiagnostic", "directRenderedLuma")
    if not isinstance(direct, dict):
        direct = {}

    global_finished = direct.get("global")
    if not isinstance(global_finished, dict):
        global_finished = {}

    positive_body = get_path(capture, "m9SceneExposureDiagnostic", "positiveBodyPressure")
    if not isinstance(positive_body, dict):
        positive_body = {}

    preview_global = get_path(capture, "subjectMotion", "previewLuma", "global")
    if not isinstance(preview_global, dict):
        preview_global = {}
    preview_center = get_path(capture, "subjectMotion", "previewLuma", "center50")
    if not isinstance(preview_center, dict):
        preview_center = {}

    intent = first_not_none(
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPhotonOnlyEv"),
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPreviewEv"),
    )

    return {
        "achievedIntentEv": as_float(intent),
        "structuralLowKeyScore": as_float(positive_body.get("structuralLowKeyScore")),
        "structuralLowKeyAttenuation": as_float(positive_body.get("structuralLowKeyAttenuation")),
        "previewGlobalMedianY": as_float(preview_global.get("median")),
        "previewGlobalQ95Y": as_float(preview_global.get("q95")),
        "previewCenterMedianY": as_float(preview_center.get("median")),
        "previewCenterMinusGlobalMedianY": as_float(preview_center.get("medianMinusGlobalMedian")),
        "tc20Gain": as_float(renderer.get("gain")),
        "baseMedianGain": as_float(renderer.get("baseMedianGain")),
        "tc20GuardGain": as_float(renderer.get("tc20GuardGain")),
        "rawHardClipFraction": as_float(renderer.get("rawHardClipFraction")),
        "renderNearWhiteFraction": as_float(renderer.get("renderNearWhiteFraction")),
        "finishedGlobalMeanY": as_float(global_finished.get("mean")),
        "finishedGlobalMedianY": as_float(global_finished.get("median")),
        "finishedGlobalQ95Y": as_float(global_finished.get("q95")),
        "finishedGlobalQ99Y": as_float(global_finished.get("q99")),
        "finishedDarkFractionLE64": as_float(global_finished.get("darkFractionLE64")),
        "finishedBrightFractionGE224": as_float(global_finished.get("brightFractionGE224")),
    }


def evaluate(features: Dict[str, Any]) -> Dict[str, Any]:
    intent = features.get("achievedIntentEv")
    score = features.get("structuralLowKeyScore")
    gain = features.get("tc20Gain")
    median = features.get("finishedGlobalMedianY")

    checks = {
        "intentLt0p10": intent is not None and intent < INTENT_MAX_EV,
        "structuralLowKeyScoreGe0p60": score is not None and score >= LOWKEY_SCORE_MIN,
        "tc20GainGe1p50": gain is not None and gain >= TC20_GAIN_MIN,
        "finishedGlobalMedianGe75": median is not None and median >= FINISHED_MEDIAN_MIN_Y,
    }
    candidate = all(checks.values())

    missing = []
    if intent is None:
        missing.append("intent")
    if score is None:
        missing.append("score")
    if gain is None:
        missing.append("gain")
    if median is None:
        missing.append("finished_median")

    if candidate:
        reason = "ON"
    elif missing:
        reason = "MISSING_" + "+".join(missing)
    else:
        failed = []
        if not checks["intentLt0p10"]:
            failed.append("INTENT")
        if not checks["structuralLowKeyScoreGe0p60"]:
            failed.append("SCORE")
        if not checks["tc20GainGe1p50"]:
            failed.append("GAIN")
        if not checks["finishedGlobalMedianGe75"]:
            failed.append("BODY")
        reason = "OFF_" + "+".join(failed)

    return {"candidate": candidate, "checks": checks, "reason": reason}


def audit(root: Path) -> Dict[str, Any]:
    rows = []
    unpaired = []
    for capture_path in iter_capture_jsons(root):
        primary_path = primary_path_for(capture_path)
        stem = capture_stem(capture_path)
        if not primary_path.exists():
            unpaired.append({"frame": stem, "capture": str(capture_path), "missing": str(primary_path)})
            continue

        capture = load_json(capture_path)
        primary = load_json(primary_path)
        features = extract(capture, primary)
        decision = evaluate(features)
        rows.append({
            "frame": stem,
            "captureJson": str(capture_path),
            "primaryJson": str(primary_path),
            **features,
            **decision["checks"],
            "candidate": decision["candidate"],
            "reason": decision["reason"],
        })

    reason_counts = Counter(row["reason"] for row in rows)
    activations = [row["frame"] for row in rows if row["candidate"]]
    return {
        "schema": "m9edgeplacementbestfit1a.bright_lowkey_cohort_audit1a.research.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "thresholdStatus": "provisional_falsification_seed_not_frozen_not_live",
        "seed": {
            "achievedIntentEvLt": INTENT_MAX_EV,
            "structuralLowKeyScoreGe": LOWKEY_SCORE_MIN,
            "tc20GainGe": TC20_GAIN_MIN,
            "finishedGlobalMedianYGe": FINISHED_MEDIAN_MIN_Y,
        },
        "summary": {
            "pairedFrames": len(rows),
            "unpairedFrames": len(unpaired),
            "activationCount": len(activations),
            "activations": activations,
            "reasonCounts": dict(sorted(reason_counts.items())),
        },
        "unpaired": unpaired,
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Folder containing prospective M9 JSON/PRIMARY pairs")
    ap.add_argument("--json", dest="json_out", type=Path)
    ap.add_argument("--csv", dest="csv_out", type=Path)
    ap.add_argument("--only-activations", action="store_true")
    args = ap.parse_args()

    result = audit(args.root)
    printable = result.copy()
    if args.only_activations:
        printable["rows"] = [row for row in result["rows"] if row["candidate"]]
    print(json.dumps(printable, indent=2, sort_keys=True))

    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    if args.csv_out:
        write_csv(args.csv_out, result["rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
