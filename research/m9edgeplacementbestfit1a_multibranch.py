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
  D. BRIGHT_LOWKEY_BROAD   - coherent low-key morphology corroborated by actual
                             finished body + upper-body opening.

BRIGHT_LOWKEY_BROAD is eligibility evidence only. It does not choose treatment
strength and must not be copied into live camera code.

Thresholds are provisional falsification seeds, not production constants.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


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

# BRIGHT_LOWKEY_OPENING1A retained research seed.
D_INTENT_MAX_EV = 0.10
D_STRUCTURAL_LOWKEY_SCORE_MIN = 0.60
D_TC20_GAIN_MIN = 1.50
D_FINISHED_GLOBAL_MEDIAN_MIN_Y = 75.0

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


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_log2_ratio(numer: Optional[float], denom: Optional[float]) -> Optional[float]:
    if numer is None or denom is None:
        return None
    numer = float(numer)
    denom = float(denom)
    if numer <= 0.0 or denom <= 0.0:
        return None
    return math.log2(max(numer, EPS) / max(denom, EPS))


def walk_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    """Yield dictionaries recursively without assuming one diagnostic nesting."""
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def first_dict_with_keys(root: Any, *keys: str) -> Optional[Dict[str, Any]]:
    for node in walk_dicts(root):
        if all(key in node for key in keys):
            return node
    return None


def first_value_for_key(root: Any, key: str) -> Any:
    for node in walk_dicts(root):
        if key in node:
            return node[key]
    return None


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


def extract_preview_global(capture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct = get_path(capture, "subjectMotion", "previewLuma", "global")
    if isinstance(direct, dict):
        return direct
    for node in walk_dicts(capture):
        schema = node.get("schema")
        if isinstance(schema, str) and schema.startswith("m9cam.previewluma"):
            global_node = node.get("global")
            if isinstance(global_node, dict):
                return global_node
    return None


def extract_finished_global(primary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct_candidates = [
        get_path(primary, "renderer", "directRenderedLuma", "global"),
        get_path(primary, "renderer", "renderMeterDiagnostic", "directRenderedLuma", "global"),
    ]
    for candidate in direct_candidates:
        if isinstance(candidate, dict):
            return candidate
    for node in walk_dicts(primary):
        schema = node.get("schema")
        if isinstance(schema, str) and schema.startswith("m9cam.renderedluma"):
            global_node = node.get("global")
            if isinstance(global_node, dict):
                return global_node
    return None


def extract_tc20(primary: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Find the TC20 decision dictionary by its distinctive gain triplet."""
    node = first_dict_with_keys(primary, "gain", "baseMedianGain", "tc20GuardGain")
    if not isinstance(node, dict):
        return {
            "gain": None,
            "baseMedianGain": None,
            "tc20GuardGain": None,
        }
    return {
        "gain": safe_float(node.get("gain")),
        "baseMedianGain": safe_float(node.get("baseMedianGain")),
        "tc20GuardGain": safe_float(node.get("tc20GuardGain")),
    }


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

    preview_global = extract_preview_global(capture) or {}
    finished_global = extract_finished_global(primary) or {}
    preview_global_median = safe_float(preview_global.get("median"))
    preview_global_q95 = safe_float(preview_global.get("q95"))
    finished_global_median = safe_float(finished_global.get("median"))
    finished_global_q95 = safe_float(finished_global.get("q95"))
    median_shift_ev = safe_log2_ratio(finished_global_median, preview_global_median)
    q95_shift_ev = safe_log2_ratio(finished_global_q95, preview_global_q95)

    tc20 = extract_tc20(primary)
    structural_lowkey_score = safe_float(first_value_for_key(capture, "structuralLowKeyScore"))

    broad_positive = bool(
        median_shift_ev is not None
        and q95_shift_ev is not None
        and median_shift_ev > 0.0
        and q95_shift_ev > 0.0
    )

    return {
        "achievedIntentEv": safe_float(intent),
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
        # BRIGHT research features.
        "structuralLowKeyScore": structural_lowkey_score,
        "tc20Gain": tc20.get("gain"),
        "tc20BaseMedianGain": tc20.get("baseMedianGain"),
        "tc20GuardGain": tc20.get("tc20GuardGain"),
        "previewGlobalMedianY": preview_global_median,
        "previewGlobalQ95Y": preview_global_q95,
        "finishedGlobalMedianY": finished_global_median,
        "finishedGlobalQ95Y": finished_global_q95,
        "brightMedianShiftEv": median_shift_ev,
        "brightQ95ShiftEv": q95_shift_ev,
        "brightBroadOpeningMinEv": (
            min(median_shift_ev, q95_shift_ev) if broad_positive else None
        ),
    }


def le(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) <= threshold


def lt(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) < threshold


def gt(value: Optional[float], threshold: float) -> bool:
    return value is not None and float(value) > threshold


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

    bright_lowkey_checks = {
        "intent_lt_0p10": lt(intent, D_INTENT_MAX_EV),
        "structural_lowkey_score_ge_0p60": ge(
            features.get("structuralLowKeyScore"),
            D_STRUCTURAL_LOWKEY_SCORE_MIN,
        ),
        "tc20_gain_ge_1p50": ge(features.get("tc20Gain"), D_TC20_GAIN_MIN),
        "finished_global_median_ge_75": ge(
            features.get("finishedGlobalMedianY"),
            D_FINISHED_GLOBAL_MEDIAN_MIN_Y,
        ),
    }
    bright_lowkey = all(bright_lowkey_checks.values())

    bright_broad_checks = {
        "median_shift_gt_0": gt(features.get("brightMedianShiftEv"), 0.0),
        "q95_shift_gt_0": gt(features.get("brightQ95ShiftEv"), 0.0),
    }
    bright_broad = all(bright_broad_checks.values())
    branch_d = bright_lowkey and bright_broad

    # Preserve the established DARK branch priority. BRIGHT is appended only as
    # an offline research branch and cannot mutate capture or rendered pixels.
    if branch_a:
        selector = "DARK_INTENT"
    elif branch_b:
        selector = "DARK_ZERO_INTENT"
    elif branch_c:
        selector = "DARK_FOREGROUND"
    elif branch_d:
        selector = "BRIGHT_LOWKEY_BROAD"
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
            "BRIGHT_LOWKEY_OPENING": {
                "candidate": bright_lowkey,
                "checks": bright_lowkey_checks,
                "meaning": "structural eligibility only; not mandatory treatment",
            },
            "BRIGHT_BROADOPENING": {
                "candidate": bright_broad,
                "checks": bright_broad_checks,
                "broadOpeningMinEv": features.get("brightBroadOpeningMinEv"),
                "meaning": "renderer-response corroboration only; not severity",
            },
            "BRIGHT_LOWKEY_BROAD": {
                "candidate": branch_d,
                "checks": {
                    "lowkey_opening": bright_lowkey,
                    "broad_opening": bright_broad,
                },
                "meaning": "research treatment eligibility; severity/HOLD remains separate",
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
