#!/usr/bin/env python3
"""M9 BRIGHT MILDRESPONSE1A — exact JPEG response-envelope probe.

Research-only. This tool does NOT choose a treatment, mutate capture exposure,
change TC20, alter the renderer, or authorize any live camera behavior.

It applies the reconstructed 0.85-pivot RGB-ratio-preserving BRIGHT operator
at a research bank of strengths and reports finished-image response relative to
Frozen. It also marks whether each candidate falls inside the *observed* mild
response envelope from the exact prospective 173828/181559 review.

Observed prospective mild envelope (falsification probe only):
  - maximum median drop <= 9.0 Y
  - maximum increase in fraction(Y <= 64) <= 0.09
  - maximum q95 drop <= 8.0 Y
  - bright >=224 fraction must not increase by more than 0.002

These are NOT production thresholds. They are intentionally labelled observed
bounds so later prospective activations can falsify them rather than being
silently fit into them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image

PIVOT = 0.85
STRENGTHS = (0.0, 0.15, 0.25, 0.35, 0.50, 0.75)

# Observed exact prospective mild-response bounds. Research-only.
MAX_MEDIAN_DROP_Y = 9.0
MAX_DARK_LE64_INCREASE = 0.09
MAX_Q95_DROP_Y = 8.0
MAX_BRIGHT_GE224_INCREASE = 0.002


def bt601_y8(arr_u8: np.ndarray) -> np.ndarray:
    rgb = arr_u8.astype(np.float32)
    return (
        4899.0 * rgb[..., 0]
        + 9617.0 * rgb[..., 1]
        + 1868.0 * rgb[..., 2]
    ) / 16384.0


def apply_rgb_pivot(arr_u8: np.ndarray, strength: float) -> np.ndarray:
    if strength == 0.0:
        return arr_u8.copy()
    rgb = arr_u8.astype(np.float32)
    y = bt601_y8(arr_u8) / 255.0
    w = np.clip(1.0 - y / PIVOT, 0.0, 1.0)
    scale = np.exp2(-float(strength) * w)
    out = rgb * scale[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def metrics(arr_u8: np.ndarray) -> Dict[str, float]:
    y = bt601_y8(arr_u8).astype(np.float64)
    q50, q90, q95, q99 = np.percentile(y, [50, 90, 95, 99])
    return {
        "meanY": float(np.mean(y)),
        "medianY": float(q50),
        "q90Y": float(q90),
        "q95Y": float(q95),
        "q99Y": float(q99),
        "darkFractionLE64": float(np.mean(y <= 64.0)),
        "brightFractionGE224": float(np.mean(y >= 224.0)),
    }


def response(base: Dict[str, float], cand: Dict[str, float]) -> Dict[str, float]:
    return {
        "medianDropY": base["medianY"] - cand["medianY"],
        "q95DropY": base["q95Y"] - cand["q95Y"],
        "q99DropY": base["q99Y"] - cand["q99Y"],
        "darkFractionLE64Increase": cand["darkFractionLE64"] - base["darkFractionLE64"],
        "brightFractionGE224Increase": cand["brightFractionGE224"] - base["brightFractionGE224"],
    }


def in_observed_mild_envelope(r: Dict[str, float]) -> bool:
    return (
        r["medianDropY"] <= MAX_MEDIAN_DROP_Y
        and r["darkFractionLE64Increase"] <= MAX_DARK_LE64_INCREASE
        and r["q95DropY"] <= MAX_Q95_DROP_Y
        and r["brightFractionGE224Increase"] <= MAX_BRIGHT_GE224_INCREASE
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jpeg", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    arr = np.asarray(Image.open(args.jpeg).convert("RGB"), dtype=np.uint8)
    frozen = metrics(arr)
    rows = []
    for strength in STRENGTHS:
        candidate_arr = apply_rgb_pivot(arr, strength)
        m = metrics(candidate_arr)
        r = response(frozen, m)
        rows.append({
            "strength": strength,
            "variant": "FROZEN" if strength == 0.0 else f"RGB{int(round(strength * 100)):03d}",
            "metrics": m,
            "responseVsFrozen": r,
            "insideObservedProspectiveMildEnvelope": in_observed_mild_envelope(r),
        })

    result = {
        "schema": "m9edgeplacementbestfit1a.bright_mildresponse1a.research.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "operator": {
            "pivot": PIVOT,
            "luma": "exact_bt601_q14_(4899R+9617G+1868B)/16384",
            "rgbRatiosPreserved": True,
        },
        "envelopeStatus": "observed_two_frame_prospective_probe_not_production_threshold",
        "observedMildEnvelope": {
            "maxMedianDropY": MAX_MEDIAN_DROP_Y,
            "maxDarkFractionLE64Increase": MAX_DARK_LE64_INCREASE,
            "maxQ95DropY": MAX_Q95_DROP_Y,
            "maxBrightFractionGE224Increase": MAX_BRIGHT_GE224_INCREASE,
        },
        "source": str(args.jpeg),
        "frozenMetrics": frozen,
        "rows": rows,
        "warning": (
            "Envelope membership is descriptive only. It must not be used as "
            "automatic treatment selection or live-camera authority."
        ),
    }

    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
