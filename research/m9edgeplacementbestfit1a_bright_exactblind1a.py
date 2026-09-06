#!/usr/bin/env python3
"""Research-only exact-pixel BRIGHT RGB-pivot blind-set generator.

Generates independent A/B/C/D blind sets for Frozen/RGB035/RGB050/RGB075
from decoded frozen JPEG pixels. Review outputs are lossless PNG so the
comparison is not confounded by JPEG re-encoding differences.

No live APK/capture/renderer mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

PIVOT = 0.85
STRENGTHS = {"FROZEN": 0.0, "RGB035": 0.35, "RGB050": 0.50, "RGB075": 0.75}
LABELS = ("A", "B", "C", "D")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rgb_pivot(arr_u8: np.ndarray, strength: float) -> np.ndarray:
    if strength == 0:
        return arr_u8.copy()
    rgb = arr_u8.astype(np.float32)
    y8 = (4899.0 * rgb[..., 0] + 9617.0 * rgb[..., 1] + 1868.0 * rgb[..., 2]) / 16384.0
    yn = y8 / 255.0
    weight = np.clip(1.0 - yn / PIVOT, 0.0, 1.0)
    scale = np.exp2(-float(strength) * weight)
    out = rgb * scale[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def luma_metrics(arr_u8: np.ndarray) -> dict:
    rgb = arr_u8.astype(np.float64)
    y = (4899.0 * rgb[..., 0] + 9617.0 * rgb[..., 1] + 1868.0 * rgb[..., 2]) / 16384.0
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


def make_contact_sheet(frame_dir: Path) -> None:
    cells = []
    for label in LABELS:
        im = Image.open(frame_dir / f"{label}.png").convert("RGB")
        thumb = ImageOps.contain(im, (760, 760), Image.Resampling.LANCZOS)
        cell = Image.new("RGB", (800, 820), "black")
        x = (800 - thumb.width) // 2
        y = (780 - thumb.height) // 2
        cell.paste(thumb, (x, y))
        ImageDraw.Draw(cell).text((18, 786), label, fill="white")
        cells.append(cell)
    sheet = Image.new("RGB", (1604, 1644), "white")
    for im, pos in zip(cells, ((0, 0), (804, 0), (0, 824), (804, 824))):
        sheet.paste(im, pos)
    sheet.save(frame_dir / "CONTACT_SHEET.png", optimize=True)


def process(source: Path, root: Path, decode: dict, manifest: dict) -> None:
    stem = source.stem.replace("(1)", "")
    frame_dir = root / stem
    frame_dir.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(Image.open(source).convert("RGB"), dtype=np.uint8)

    order = list(STRENGTHS)
    secrets.SystemRandom().shuffle(order)
    mapping = dict(zip(LABELS, order))
    decode[stem] = mapping

    info = {"source": source.name, "sha256": sha256_file(source), "blindVariants": {}}
    for label in LABELS:
        treatment = mapping[label]
        out = rgb_pivot(arr, STRENGTHS[treatment])
        Image.fromarray(out, "RGB").save(frame_dir / f"{label}.png", optimize=True)
        info["blindVariants"][label] = {
            "treatmentHidden": True,
            "metrics": luma_metrics(out),
        }
    make_contact_sheet(frame_dir)
    manifest["frames"][stem] = info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("-o", "--output", default="M9_BRIGHT_PROSPECTIVE_EXACT1A")
    args = ap.parse_args()

    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    decode = {}
    manifest = {
        "schema": "m9edgeplacementbestfit1a.bright.exactblind.v1",
        "mode": "research_only_no_capture_or_live_renderer_mutation",
        "pivot": PIVOT,
        "strengths": STRENGTHS,
        "luma": "BT601_Q14_(4899R+9617G+1868B)/16384",
        "frames": {},
    }

    for src in args.sources:
        process(Path(src).resolve(), root, decode, manifest)

    (root / "DECODE_KEY.json").write_text(json.dumps(decode, indent=2), encoding="utf-8")
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zip_path = root.parent / f"{root.name}_BLIND.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "DECODE_KEY.json":
                z.write(path, path.relative_to(root.parent))
    print(zip_path)


if __name__ == "__main__":
    main()
