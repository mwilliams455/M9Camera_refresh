#!/usr/bin/env python3
"""LOCALSUBJECTSURVIVAL1A research-only protective morphology probe.

Reads an M9 *_M9_PRIMARY.json and asks whether the finished JPEG contains a
compact central bright subject that survives inside a much darker global field.
This is a protective veto candidate for ZERO_INTENT_COLLAPSE research only.
No capture, renderer, TC20, or exposure mutation is permitted.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, Optional

LOCAL_Q95_MIN_Y = 220.0
LOCAL_MINUS_GLOBAL_Q95_MIN_Y = 80.0

def get_path(obj: Dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def extract_direct_rendered_luma(primary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for candidate in (
        get_path(primary, "renderer", "directRenderedLuma"),
        get_path(primary, "renderer", "renderMeterDiagnostic", "directRenderedLuma"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return None

def f(value: Any) -> Optional[float]:
    try: return float(value)
    except (TypeError, ValueError): return None

def evaluate(primary: Dict[str, Any]) -> Dict[str, Any]:
    drl = extract_direct_rendered_luma(primary) or {}
    global_q95 = f(get_path(drl, "global", "q95"))
    center_q95 = f(get_path(drl, "center50", "q95"))
    middle_q95 = f(get_path(drl, "middleCenter33", "q95"))
    vals = [x for x in (center_q95, middle_q95) if x is not None]
    local_q95 = max(vals) if vals else None
    concentration = local_q95 - global_q95 if local_q95 is not None and global_q95 is not None else None
    checks = {
        "local_q95_ge_220": local_q95 is not None and local_q95 >= LOCAL_Q95_MIN_Y,
        "local_minus_global_q95_ge_80": concentration is not None and concentration >= LOCAL_MINUS_GLOBAL_Q95_MIN_Y,
    }
    guard = all(checks.values())
    return {
        "schema": "m9edgeplacementbestfit1a.localsubjectsurvival1a.research.v1",
        "mode": "offline_protective_probe_only_no_capture_or_pixel_mutation",
        "liveLiftEnabled": False,
        "protectZeroIntentLiftCandidate": guard,
        "checks": checks,
        "features": {
            "globalQ95": global_q95,
            "centerQ95": center_q95,
            "middleCenterQ95": middle_q95,
            "localQ95": local_q95,
            "localMinusGlobalQ95": concentration,
        },
        "thresholdStatus": "provisional_falsification_seed_not_frozen_not_live",
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("primary_json", type=Path)
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()
    primary = json.loads(args.primary_json.read_text(encoding="utf-8"))
    result = evaluate(primary)
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
