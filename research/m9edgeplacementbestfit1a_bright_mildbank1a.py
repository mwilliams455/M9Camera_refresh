#!/usr/bin/env python3
"""
M9 EDGEPLACEMENT BESTFIT1A — BRIGHT MILD BANK1A

Research-only exact-pixel JPEG treatment harness.

Generates independently blinded Frozen / RGB015 / RGB025 / RGB035 variants
using the established RGB-ratio-preserving 0.85-pivot BRIGHT density operator.
No live renderer, capture, TC20, curve02, colour science or JPEG policy change.

Review outputs are lossless PNGs from one decoded frozen JPEG so the comparison
is not confounded by differing JPEG recompression histories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from pathlib import Path

import numpy as np
from PIL import Image

PIVOT = 0.85
BANK = {
    "FROZEN": 0.00,
    "RGB015": 0.15,
    "RGB025": 0.25,
    "RGB035": 0.35,
}
LABELS = ("A", "B", "C", "D")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_luma8(rgb: np.ndarray) -> np.ndarray:
    a = rgb.astype(np.float32)
    return (
        4899.0 * a[..., 0]
        + 9617.0 * a[..., 1]
        + 1868.0 * a[..., 2]
    ) / 16384.0


def rgb_pivot(rgb_u8: np.ndarray, strength: float) -> np.ndarray:
    if strength == 0.0:
        return rgb_u8.copy()
    rgb = rgb_u8.astype(np.float32)
    yn = exact_luma8(rgb_u8) / 255.0
    weight = np.clip(1.0 - yn / PIVOT, 0.0, 1.0)
    scale = np.exp2(-strength * weight)
    out = rgb * scale[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def metrics(rgb_u8: np.ndarray) -> dict:
    y = exact_luma8(rgb_u8).astype(np.float64)
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
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("M9_BRIGHT_MILDBANK1A"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    key = {}
    manifest = {
        "schema": "m9edgeplacementbestfit1a.bright.mildbank1a.research.v1",
        "mode": "offline_exact_pixel_no_live_mutation",
        "pivot": PIVOT,
        "bank": BANK,
        "frames": {},
    }
    rng = secrets.SystemRandom()

    for source in args.sources:
        source = source.resolve()
        frame = source.stem
        frame_dir = args.out / frame
        frame_dir.mkdir(parents=True, exist_ok=True)
        arr = np.asarray(Image.open(source).convert("RGB"), dtype=np.uint8)

        treatments = list(BANK)
        rng.shuffle(treatments)
        mapping = dict(zip(LABELS, treatments))
        key[frame] = mapping

        rec = {
            "source": str(source),
            "sourceSha256": sha256_file(source),
            "variants": {},
        }
        for label in LABELS:
            treatment = mapping[label]
            out = rgb_pivot(arr, BANK[treatment])
            path = frame_dir / f"{label}.png"
            Image.fromarray(out, "RGB").save(path, format="PNG", optimize=True)
            rec["variants"][label] = {
                "treatmentHidden": True,
                "file": str(path.relative_to(args.out)),
                "metrics": metrics(out),
            }
        manifest["frames"][frame] = rec

    (args.out / "DECODE_KEY.json").write_text(
        json.dumps(key, indent=2, sort_keys=True), encoding="utf-8"
    )
    (args.out / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
