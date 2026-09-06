#!/usr/bin/env python3
"""Research-only exact JPEG BRIGHT mild-zone probe.

Applies the reconstructed M9 BRIGHT RGB-pivot operator to a frozen JPEG and
reports finished-luma metrics for Frozen / RGB015 / RGB025 / RGB035.

This tool is diagnostic only. It does not mutate capture exposure, TC20,
renderer code, DNG output, or any live camera path.

The provisional 74..77 Y median band is an empirical natural-mild probe from
only two prospective September-5 frames. It is NOT a production normalization
target and must not be used as a universal selector.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image

PIVOT = 0.85
STRENGTHS = (
    ("FROZEN", 0.00),
    ("RGB015", 0.15),
    ("RGB025", 0.25),
    ("RGB035", 0.35),
)

# Research-only prospective natural-mild observation. Not live/frozen.
MILD_MEDIAN_MIN_Y = 74.0
MILD_MEDIAN_MAX_Y = 77.0


def exact_bt601_y8(rgb: np.ndarray) -> np.ndarray:
    rgbf = rgb.astype(np.float64)
    return (
        4899.0 * rgbf[..., 0]
        + 9617.0 * rgbf[..., 1]
        + 1868.0 * rgbf[..., 2]
    ) / 16384.0


def rgb_pivot(rgb: np.ndarray, strength: float) -> np.ndarray:
    if strength <= 0.0:
        return rgb.copy()
    y8 = exact_bt601_y8(rgb)
    yn = y8 / 255.0
    weight = np.clip(1.0 - yn / PIVOT, 0.0, 1.0)
    scale = np.exp2(-strength * weight)
    out = rgb.astype(np.float64) * scale[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def metrics(rgb: np.ndarray) -> dict:
    y = exact_bt601_y8(rgb)
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jpeg", type=Path)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    frozen = np.asarray(Image.open(args.jpeg).convert("RGB"), dtype=np.uint8)
    rows = []
    for name, strength in STRENGTHS:
        rendered = rgb_pivot(frozen, strength)
        m = metrics(rendered)
        rows.append({
            "variant": name,
            "strengthEv": strength,
            **m,
            "insideProvisionalNaturalMildMedianBand": (
                MILD_MEDIAN_MIN_Y <= m["medianY"] <= MILD_MEDIAN_MAX_Y
            ),
        })

    result = {
        "schema": "m9edgeplacementbestfit1a.bright_mildzone_probe.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "source": str(args.jpeg),
        "pivot": PIVOT,
        "luma": "BT601_Q14_4899_9617_1868",
        "provisionalNaturalMildMedianBandY": [
            MILD_MEDIAN_MIN_Y,
            MILD_MEDIAN_MAX_Y,
        ],
        "thresholdStatus": "two_frame_prospective_observation_not_frozen_not_live",
        "warning": (
            "Do not normalize arbitrary frames to this median band. "
            "Eligibility and severity remain separate research problems."
        ),
        "variants": rows,
    }

    print(json.dumps(result, indent=2))

    if args.json:
        args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
