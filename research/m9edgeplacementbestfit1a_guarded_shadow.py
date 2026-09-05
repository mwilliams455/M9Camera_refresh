#!/usr/bin/env python3
"""BESTFIT1A shadow evaluator with LOCALSUBJECTSURVIVAL1A.

The canonical BESTFIT1A selector result is preserved unchanged. A second
research-only shadow result shows what would happen if LOCALSUBJECTSURVIVAL1A
were used solely as a protective veto for DARK_ZERO_INTENT.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import m9edgeplacementbestfit1a_multibranch as bestfit
import m9edgeplacementbestfit1a_localsubjectsurvival1a as survival


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture_json", type=Path)
    ap.add_argument("primary_json", type=Path)
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()

    capture = bestfit.load_json(args.capture_json)
    primary = bestfit.load_json(args.primary_json)
    canonical = bestfit.evaluate(bestfit.extract_features(capture, primary))
    guard = survival.evaluate(primary)

    canonical_selector = canonical.get("selector", "HOLD")
    guard_active = bool(guard.get("protectZeroIntentLiftCandidate"))
    if canonical_selector == "DARK_ZERO_INTENT" and guard_active:
        shadow_selector = "HOLD_LOCAL_SUBJECT_SURVIVAL"
    else:
        shadow_selector = canonical_selector

    result = {
        "schema": "m9edgeplacementbestfit1a.guardedshadow.research.v1",
        "mode": "offline_shadow_comparison_only_no_capture_or_pixel_mutation",
        "liveLiftEnabled": False,
        "canonicalSelectorUnchanged": canonical_selector,
        "shadowSelectorWithLocalSubjectSurvival": shadow_selector,
        "protectiveGuard": guard,
        "canonicalResult": canonical,
        "thresholdStatus": "provisional_falsification_seed_not_frozen_not_live",
    }
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
