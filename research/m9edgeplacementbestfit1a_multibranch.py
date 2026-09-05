#!/usr/bin/env python3
"""
EDGEPLACEMENTBESTFIT1A research-only multi-branch selector.

This tool reads an M9 capture JSON plus its matching *_M9_PRIMARY.json and
computes descriptive preview->finished placement features. It MUST NOT be used
to mutate capture exposure or renderer pixels.

Candidate branches:
  A. INTENT_COLLAPSE       - preserves the existing Part-3 conjunction.
  B. ZERO_INTENT_COLLAPSE  - broad matched-region retention collapse.
  C. FOREGROUND_COLLAPSE   - lower-field loss while upper/high support survives.

Thresholds are provisional falsification seeds, not production constants.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Optional


# Research-only thresholds. Do not copy into live camera code.
A_INTENT_MIN_EV = 0.10
A_UPPER_LOWER_SHIFT_MIN_EV = 1.50
A_RENDER_CELL_MEDIAN_P75_MAX_Y = 30.0
A_INTEGRAL_RELATIVE_SHIFT_MAX_EV = 0.15

B_INTENT_MAX_EV = 0.10
B_PREVIEW_SCENE_SPREAD_MIN_EV = 1.30
B_PREVIEW_BRIGHT_REGION_FRACTION_MIN = 0.20
B_RENDER_CELL_MEDIAN_P75_MAX_Y = 15.0
B_RENDER_GRID_MEAN_MAX_Y = 30.0
B_REGION_RETENTION_COLLAPSE_MAX_EV = -1.50
B_MIN_COLLAPSED_REGIONS = 3
B_RETENTION_REGIONS = ("center", "lower", "upper", "edge")

C_UPPER_LOWER_SHIFT_MIN_EV = 1.20
C_RENDER_LOWER_MAX_Y = 18.0
C_RENDER_UPPER_MIN_Y = 140.0
C_RENDER_CELL_MEDIAN_P75_MIN_Y = 120.0
C_CENTER_RETENTION_MIN_EV = -1.00

EPS = 1e-9


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def safe_log2_ratio(numer: Optional[float], denom: Optional[float]) -> Optional[float]:
    if numer is None or denom is None:
        return None
    numer = float(numer)
    denom = float(denom)
    if numer <= 0.0 or denom <= 0.0:
        return None
    return math.log2(max(numer, EPS) / max(denom, EPS))


def grid_mean(rows: Any) -> Optional[float]:
    if not isinstance(rows, list) or not rows:
        return None
    vals = []
    for row in rows:
        if not isinstance(row, list):
            return None
        vals.extend(float(v) for v in row if isinstance(v, (int, float)))
    if not vals:
        return None
    return sum(vals) / len(vals)


def extract_preview_grid_rows(capture: Dict[str, Any]) -> Any:
    candidates = [
        get_path(capture, "subjectMotion", "previewLuma", "m10rAeGrid16x22", "rows"),
        get_path(capture, "subjectMotion", "previewLuma", "m10rAeGrid16x22", "grid"),
        get_path(capture, "subjectMotion", "previewLuma", "m10rAeGrid16x22"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate
    return None


def extract_gate(primary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = [
        get_path(primary, "renderer", "directRenderedLuma", "edgePlacementGate1A"),
        get_path(primary, "renderer", "renderMeterDiagnostic", "directRenderedLuma", "edgePlacementGate1A"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return None


def extract_features(capture: Dict[str, Any], primary: Dict[str, Any]) -> Dict[str, Any]:
    mfm = get_path(capture, "m9M10rMfmTest")
    if not isinstance(mfm, dict):
        mfm = {}

    gate = extract_gate(primary)
    if not isinstance(gate, dict):
        gate = {}

    intent = first_not_none(
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPhotonOnlyEv"),
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPreviewEv"),
    )

    preview_rows = extract_preview_grid_rows(capture)
    preview_grid_mean = grid_mean(preview_rows)

    preview_integral = mfm.get("integralY")
    preview_integral_vs_mean_ev = safe_log2_ratio(preview_integral, preview_grid_mean)
    render_integral_vs_mean_ev = gate.get("renderIntegralVsMeanEv")
    integral_relative_shift_ev = None
    if preview_integral_vs_mean_ev is not None and render_integral_vs_mean_ev is not None:
        integral_relative_shift_ev = float(render_integral_vs_mean_ev) - preview_integral_vs_mean_ev

    preview_ul = mfm.get("upperVsLowerEv")
    render_ul = gate.get("renderUpperVsLowerEv")
    upper_lower_shift_ev = None
    if preview_ul is not None and render_ul is not None:
        upper_lower_shift_ev = float(render_ul) - float(preview_ul)

    matched = {
        "center": (mfm.get("center8Y"), gate.get("renderCenter8Y")),
        "lower": (mfm.get("lower12Y"), gate.get("renderLower12Y")),
        "upper": (mfm.get("upper6Y"), gate.get("renderUpper6Y")),
        "edge": (mfm.get("edge16Y"), gate.get("renderEdge16Y")),
        "inner": (mfm.get("inner8Y"), gate.get("renderInner8Y")),
        "integral": (mfm.get("integralY"), gate.get("renderIntegralY")),
    }
    retention_ev = {
        key: safe_log2_ratio(render, preview)
        for key, (preview, render) in matched.items()
    }

    collapsed_regions = [
        region for region in B_RETENTION_REGIONS
        if retention_ev.get(region) is not None
        and retention_ev[region] <= B_REGION_RETENTION_COLLAPSE_MAX_EV
    ]

    return {
        "achievedIntentEv": intent,
        "previewSceneSpreadEv": mfm.get("sceneSpreadEv"),
        "previewBrightRegionFraction": mfm.get("brightRegionFraction"),
        "previewUpperVsLowerEv": preview_ul,
        "renderUpperVsLowerEv": render_ul,
        "upperLowerShiftEv": upper_lower_shift_ev,
        "previewGridMeanY": preview_grid_mean,
        "previewIntegralVsMeanEv": preview_integral_vs_mean_ev,
        "renderIntegralVsMeanEv": render_integral_vs_mean_ev,
        "integralRelativeShiftEv": integral_relative_shift_ev,
        "retentionEv": retention_ev,
        "broadCollapsedRegions": collapsed_regions,
        "broadCollapseCount": len(collapsed_regions),
        "renderGridMeanY": gate.get("renderGridMeanY"),
        "renderLower12Y": gate.get("renderLower12Y"),
        "renderUpper6Y": gate.get("renderUpper6Y"),
        "renderCellMedianP75": gate.get("renderCellMedianP75"),
        "matchedFinishedGeometryAvailable": bool(gate),
    }


def le(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) <= threshold


def lt(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) < threshold


def ge(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) >= threshold


def evaluate(features: Dict[str, Any]) -> Dict[str, Any]:
    intent = features.get("achievedIntentEv")
    p75 = features.get("renderCellMedianP75")
    ul_shift = features.get("upperLowerShiftEv")
    integral_shift = features.get("integralRelativeShiftEv")
    retention = features.get("retentionEv") or {}

    branch_a_checks = {
        "intent_ge_0p10": ge(intent, A_INTENT_MIN_EV),
        "upper_lower_shift_ge_1p50": ge(ul_shift, A_UPPER_LOWER_SHIFT_MIN_EV),
        "render_p75_le_30": le(p75, A_RENDER_CELL_MEDIAN_P75_MAX_Y),
        "integral_relative_shift_le_0p15": le(integral_shift, A_INTEGRAL_RELATIVE_SHIFT_MAX_EV),
    }
    branch_a = all(branch_a_checks.values())

    branch_b_checks = {
        "intent_lt_0p10": lt(intent, B_INTENT_MAX_EV),
        "preview_scene_spread_ge_1p30": ge(
            features.get("previewSceneSpreadEv"),
            B_PREVIEW_SCENE_SPREAD_MIN_EV,
        ),
        "preview_bright_region_fraction_ge_0p20": ge(
            features.get("previewBrightRegionFraction"),
            B_PREVIEW_BRIGHT_REGION_FRACTION_MIN,
        ),
        "render_p75_le_15": le(p75, B_RENDER_CELL_MEDIAN_P75_MAX_Y),
        "render_grid_mean_le_30": le(
            features.get("renderGridMeanY"),
            B_RENDER_GRID_MEAN_MAX_Y,
        ),
        "broad_collapse_count_ge_3": int(features.get("broadCollapseCount") or 0)
        >= B_MIN_COLLAPSED_REGIONS,
    }
    branch_b = all(branch_b_checks.values())

    branch_c_checks = {
        "upper_lower_shift_ge_1p20": ge(ul_shift, C_UPPER_LOWER_SHIFT_MIN_EV),
        "render_lower_le_18": le(features.get("renderLower12Y"), C_RENDER_LOWER_MAX_Y),
        "render_upper_ge_140": ge(features.get("renderUpper6Y"), C_RENDER_UPPER_MIN_Y),
        "render_p75_ge_120": ge(p75, C_RENDER_CELL_MEDIAN_P75_MIN_Y),
        "center_retention_ge_minus_1p00": ge(
            retention.get("center"),
            C_CENTER_RETENTION_MIN_EV,
        ),
    }
    branch_c = all(branch_c_checks.values())

    if branch_a:
        selector = "DARK_INTENT"
    elif branch_b:
        selector = "DARK_ZERO_INTENT"
    elif branch_c:
        selector = "DARK_FOREGROUND"
    else:
        selector = "HOLD"

    return {
        "schema": "m9edgeplacementbestfit1a.research.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "liveLiftEnabled": False,
        "selector": selector,
        "branches": {
            "INTENT_COLLAPSE": {
                "candidate": branch_a,
                "checks": branch_a_checks,
            },
            "ZERO_INTENT_COLLAPSE": {
                "candidate": branch_b,
                "checks": branch_b_checks,
                "collapsedRegions": features.get("broadCollapsedRegions", []),
            },
            "FOREGROUND_COLLAPSE": {
                "candidate": branch_c,
                "checks": branch_c_checks,
            },
        },
        "features": features,
        "thresholdStatus": "provisional_falsification_seed_not_frozen_not_live",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_json", type=Path)
    parser.add_argument("primary_json", type=Path)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    capture = load_json(args.capture_json)
    primary = load_json(args.primary_json)
    result = evaluate(extract_features(capture, primary))
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
