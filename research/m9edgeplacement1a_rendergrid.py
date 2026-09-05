#!/usr/bin/env python3
"""M9EDGEPLACEMENT1A RENDERGRID1A finished-render spatial evidence extractor.

Research-only. This tool does not modify capture exposure, TC20, the frozen M9
renderer, or JPEG pixels. It compares the existing M10-R-inspired preview spatial
field with the *finished frozen JPEG* using the same recovered 16x22 Integral
weight mask and 4x6 regional topology.

Purpose
-------
Global/center-only RENDERMETER1C evidence is too broad for DARK_FAIL authority.
A valid M9 photograph can have a very low global/center median because its useful
subject is off-center, because the scene is intentionally low-key, or because a
small bright subject sits against a dark field.

RENDERGRID1A asks a narrower question:

    Did the spatial field that existed before rendering keep a comparable
    relationship after the frozen render, or did one part of the field collapse
    relative to another?

The output is diagnostic evidence only. No threshold in this script is a live
selector and no candidate EV is produced.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image

GRID_R = 16
GRID_C = 22
REG_R = 4
REG_C = 6

# Exact recovered M10-R Integral quantity mask at 0x4001349c, sum = 14160.
# It is reused here only as spatial geometry against finished Xiaomi/M9 JPEG Y.
# This does NOT claim M10-R numerical CA9/prepro parity.
INTEGRAL_MASK = np.asarray([
    [0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0],
    [0,0,0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10,0,0,0],
    [0,0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10,0,0],
    [0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10,0],
    [10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10],
    [10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10],
    [10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10],
    [10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10],
    [10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10],
    [10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10],
    [10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10],
    [10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10],
    [0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10,0],
    [0,0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10,0,0],
    [0,0,0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10,0,0,0],
    [0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0],
], dtype=np.float64)

if INTEGRAL_MASK.shape != (GRID_R, GRID_C) or int(INTEGRAL_MASK.sum()) != 14160:
    raise RuntimeError("bad recovered Integral mask")

LABELS = {"GOOD", "BOUNDARY", "BRIGHT_FAIL", "DARK_FAIL"}


def walk_dicts(obj: Any) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_dicts(v)


def capture_key_from_obj(obj: Any, fallback: str) -> str:
    preferred = (
        "dng", "captureIdentity", "sourceDng", "sourceDngName",
        "rawFilename", "rawFileName", "dngFilename", "dngFileName",
    )
    for d in walk_dicts(obj):
        for k in preferred:
            v = d.get(k)
            if isinstance(v, str) and v:
                name = Path(v).name
                if name.lower().endswith(".dng"):
                    return Path(name).stem
    stem = Path(fallback).stem
    stem = re.sub(r"_M9_PRIMARY$", "", stem, flags=re.I)
    stem = re.sub(r"_M9$", "", stem, flags=re.I)
    return stem


def render_key(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"_SAT[234]$", "", stem, flags=re.I)
    return stem


def safe(v: float) -> float:
    return max(float(v), 1.0e-6)


def log2_ratio(a: float, b: float) -> float:
    return math.log2(safe(a) / safe(b))


def weighted_mean(grid: np.ndarray) -> float:
    return float(np.sum(grid * INTEGRAL_MASK) / np.sum(INTEGRAL_MASK))


def regions4x6(grid: np.ndarray) -> np.ndarray:
    if grid.shape != (GRID_R, GRID_C):
        raise ValueError(f"expected {GRID_R}x{GRID_C}, got {grid.shape}")
    out = np.zeros((REG_R, REG_C), dtype=np.float64)
    for rr in range(REG_R):
        r0 = rr * GRID_R // REG_R
        r1 = (rr + 1) * GRID_R // REG_R
        for cc in range(REG_C):
            c0 = cc * GRID_C // REG_C
            c1 = (cc + 1) * GRID_C // REG_C
            out[rr, cc] = float(np.mean(grid[r0:r1, c0:c1]))
    return out


def rect_mean(regions: np.ndarray, r0: int, r1: int, c0: int, c1: int) -> float:
    return float(np.mean(regions[r0:r1, c0:c1]))


def edge_mean(regions: np.ndarray, edge: bool) -> float:
    vals = []
    for y in range(REG_R):
        for x in range(REG_C):
            is_edge = y == 0 or y == REG_R - 1 or x == 0 or x == REG_C - 1
            if is_edge == edge:
                vals.append(float(regions[y, x]))
    return float(np.mean(vals)) if vals else 0.0


def exact_bt601_y(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.int64)
    return ((4899 * x[..., 0] + 9617 * x[..., 1] + 1868 * x[..., 2]) >> 14).astype(np.float64)


def mean_grid(y: np.ndarray, rows: int, cols: int) -> np.ndarray:
    h, w = y.shape
    out = np.zeros((rows, cols), dtype=np.float64)
    for r in range(rows):
        y0 = r * h // rows
        y1 = (r + 1) * h // rows
        for c in range(cols):
            x0 = c * w // cols
            x1 = (c + 1) * w // cols
            out[r, c] = float(np.mean(y[y0:y1, x0:x1]))
    return out


def direct_region_stats(y: np.ndarray) -> dict[str, Any]:
    h, w = y.shape
    med = np.zeros((REG_R, REG_C), dtype=np.float64)
    q95 = np.zeros_like(med)
    dark64 = np.zeros_like(med)
    for r in range(REG_R):
        y0 = r * h // REG_R
        y1 = (r + 1) * h // REG_R
        for c in range(REG_C):
            x0 = c * w // REG_C
            x1 = (c + 1) * w // REG_C
            cell = y[y0:y1, x0:x1]
            med[r, c] = float(np.median(cell))
            q95[r, c] = float(np.quantile(cell, 0.95))
            dark64[r, c] = float(np.mean(cell <= 64.0))
    return {
        "renderCellMedianP25": float(np.quantile(med, 0.25)),
        "renderCellMedianP50": float(np.quantile(med, 0.50)),
        "renderCellMedianP75": float(np.quantile(med, 0.75)),
        "renderCellMedianMax": float(np.max(med)),
        "renderCellQ95P50": float(np.quantile(q95, 0.50)),
        "renderCellQ95P75": float(np.quantile(q95, 0.75)),
        "renderCellQ95Max": float(np.max(q95)),
        "renderCellDark64P50": float(np.quantile(dark64, 0.50)),
        "renderCellDark64P75": float(np.quantile(dark64, 0.75)),
        "renderMedian4x6": " ".join(f"{x:.6f}" for x in med.ravel()),
        "renderQ95_4x6": " ".join(f"{x:.6f}" for x in q95.ravel()),
    }


def read_preview_grid(obj: dict) -> np.ndarray | None:
    subject = obj.get("subjectMotion") if isinstance(obj.get("subjectMotion"), dict) else {}
    pl = subject.get("previewLuma") if isinstance(subject.get("previewLuma"), dict) else {}
    grid = pl.get("m10rAeGrid16x22") if isinstance(pl.get("m10rAeGrid16x22"), dict) else {}
    rows = grid.get("rows")
    if not isinstance(rows, list) or len(rows) != GRID_R:
        return None
    try:
        arr = np.asarray(rows, dtype=np.float64)
    except Exception:
        return None
    if arr.shape != (GRID_R, GRID_C) or not np.isfinite(arr).all():
        return None
    return np.maximum(arr, 0.0)


def achieved_intent(obj: dict) -> float | None:
    audit = obj.get("m9ExposureAudit") if isinstance(obj.get("m9ExposureAudit"), dict) else {}
    derived = audit.get("derived") if isinstance(audit.get("derived"), dict) else {}
    v = derived.get("captureEnergyVsPhotonOnlyEv")
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def m10r_snapshot(obj: dict) -> dict:
    q = obj.get("m9M10rMfmTest")
    return q if isinstance(q, dict) else {}


def build_identity(obj: dict) -> dict[str, str]:
    b = obj.get("m9Build") if isinstance(obj.get("m9Build"), dict) else {}
    sd = obj.get("m9SceneExposureDiagnostic") if isinstance(obj.get("m9SceneExposureDiagnostic"), dict) else {}
    return {
        "buildVersion": str(b.get("version", "")),
        "sceneSchema": str(sd.get("schema", "")),
    }


@dataclass
class JsonRecord:
    key: str
    obj: dict
    source: str


def index_json(root: Path) -> dict[str, JsonRecord]:
    out: dict[str, JsonRecord] = {}
    for p in sorted(root.rglob("*.json")):
        try:
            obj = json.loads(p.read_text(errors="replace"))
        except Exception:
            continue
        candidates: list[dict] = []
        if isinstance(obj, dict):
            candidates.append(obj)
            entries = obj.get("entries")
            if isinstance(entries, list):
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    payload = e.get("payload")
                    if isinstance(payload, dict):
                        candidates.append(payload)
        for cand in candidates:
            if read_preview_grid(cand) is None:
                continue
            key = capture_key_from_obj(cand, p.name)
            # Prefer direct _M9.json capture sidecars over later bundle copies.
            score = 2 if p.name.upper().endswith("_M9.JSON") else 1
            old = out.get(key)
            old_score = 2 if old and old.source.upper().endswith("_M9.JSON") else 1
            if old is None or score > old_score:
                out[key] = JsonRecord(key, cand, str(p))
    return out


def read_labels(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows


def apply_label(key: str, labels: list[dict[str, str]]) -> tuple[str, str, str]:
    hits = [r for r in labels if (r.get("pattern") or "") and (r.get("pattern") or "") in key]
    if not hits:
        return "", "", ""
    labs = {(r.get("label") or "").strip().upper() for r in hits if (r.get("label") or "").strip()}
    if len(labs) > 1:
        raise RuntimeError(f"conflicting labels for {key}: {sorted(labs)}")
    lab = next(iter(labs), "")
    if lab and lab not in LABELS:
        lab = ""
    m9ness = next(((r.get("m9ness") or "").strip() for r in hits if (r.get("m9ness") or "").strip()), "")
    notes = " | ".join((r.get("notes") or "").strip() for r in hits if (r.get("notes") or "").strip())
    return lab, m9ness, notes


def feature_row(key: str, jpg: Path, record: JsonRecord, labels: list[dict[str, str]]) -> dict[str, Any]:
    obj = record.obj
    preview = read_preview_grid(obj)
    if preview is None:
        raise ValueError("preview grid missing")
    rgb = np.asarray(Image.open(jpg).convert("RGB"), dtype=np.uint8)
    y = exact_bt601_y(rgb)
    render_grid = mean_grid(y, GRID_R, GRID_C)

    p_int = weighted_mean(preview)
    r_int = weighted_mean(render_grid)
    p_mean = float(np.mean(preview))
    r_mean = float(np.mean(render_grid))
    p_reg = regions4x6(preview)
    r_reg = regions4x6(render_grid)

    p_center = rect_mean(p_reg, 1, 3, 1, 5)
    r_center = rect_mean(r_reg, 1, 3, 1, 5)
    p_lower = rect_mean(p_reg, 2, 4, 0, 6)
    r_lower = rect_mean(r_reg, 2, 4, 0, 6)
    p_upper = rect_mean(p_reg, 0, 1, 0, 6)
    r_upper = rect_mean(r_reg, 0, 1, 0, 6)
    p_edge = edge_mean(p_reg, True)
    r_edge = edge_mean(r_reg, True)
    p_inner = edge_mean(p_reg, False)
    r_inner = edge_mean(r_reg, False)

    snap = m10r_snapshot(obj)
    label, m9ness, label_notes = apply_label(key, labels)
    out: dict[str, Any] = {
        "captureKey": key,
        "renderFile": str(jpg),
        "jsonSource": record.source,
        "label": label,
        "m9ness": m9ness,
        "labelNotes": label_notes,
        **build_identity(obj),
        "achievedIntentEv": achieved_intent(obj),
        "previewIntegralY": p_int,
        "savedPreviewIntegralY": snap.get("integralY"),
        "previewIntegralParityErrorY": (
            p_int - float(snap.get("integralY"))
            if snap.get("integralY") is not None else None
        ),
        "renderIntegralY": r_int,
        "previewGridMeanY": p_mean,
        "renderGridMeanY": r_mean,
        "previewIntegralVsMeanEv": log2_ratio(p_int, p_mean),
        "renderIntegralVsMeanEv": log2_ratio(r_int, r_mean),
        "integralRelativeShiftEv": log2_ratio(r_int, r_mean) - log2_ratio(p_int, p_mean),
        "integralRetentionEv": log2_ratio(r_int, p_int),
        "meanRetentionEv": log2_ratio(r_mean, p_mean),
        "weightedVsMeanRetentionEv": log2_ratio(r_int, p_int) - log2_ratio(r_mean, p_mean),
        "previewRegionalMedianY": float(np.median(p_reg)),
        "renderRegionalMedianY": float(np.median(r_reg)),
        "previewCenter8Y": p_center,
        "renderCenter8Y": r_center,
        "centerRetentionEv": log2_ratio(r_center, p_center),
        "previewLower12Y": p_lower,
        "renderLower12Y": r_lower,
        "lowerRetentionEv": log2_ratio(r_lower, p_lower),
        "previewUpper6Y": p_upper,
        "renderUpper6Y": r_upper,
        "upperRetentionEv": log2_ratio(r_upper, p_upper),
        "previewEdge16Y": p_edge,
        "renderEdge16Y": r_edge,
        "edgeRetentionEv": log2_ratio(r_edge, p_edge),
        "previewInner8Y": p_inner,
        "renderInner8Y": r_inner,
        "innerRetentionEv": log2_ratio(r_inner, p_inner),
        "previewUpperVsLowerEv": log2_ratio(p_upper, p_lower),
        "renderUpperVsLowerEv": log2_ratio(r_upper, r_lower),
        "upperLowerShiftEv": log2_ratio(r_upper, r_lower) - log2_ratio(p_upper, p_lower),
        "previewCenterOverIntegralEv": log2_ratio(p_center, p_int),
        "renderCenterOverIntegralEv": log2_ratio(r_center, r_int),
        "centerOverIntegralShiftEv": log2_ratio(r_center, r_int) - log2_ratio(p_center, p_int),
        "previewInnerVsEdgeEv": log2_ratio(p_inner, p_edge),
        "renderInnerVsEdgeEv": log2_ratio(r_inner, r_edge),
        "innerVsEdgeShiftEv": log2_ratio(r_inner, r_edge) - log2_ratio(p_inner, p_edge),
        "previewRegions4x6": " ".join(f"{x:.6f}" for x in p_reg.ravel()),
        "renderMeanRegions4x6": " ".join(f"{x:.6f}" for x in r_reg.ravel()),
    }
    out.update(direct_region_stats(y))
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def self_test() -> None:
    # Confirm exact mask geometry and 4x6 partitioning.
    assert int(INTEGRAL_MASK.sum()) == 14160
    g = np.arange(GRID_R * GRID_C, dtype=np.float64).reshape(GRID_R, GRID_C)
    r = regions4x6(g)
    assert r.shape == (4, 6)
    assert abs(r[0, 0] - np.mean(g[0:4, 0:3])) < 1e-12
    assert abs(r[0, 1] - np.mean(g[0:4, 3:7])) < 1e-12
    assert abs(r[-1, -1] - np.mean(g[12:16, 18:22])) < 1e-12

    # Synthetic render: upper half is bright, lower half dark. The exact BT.601
    # grid must preserve that direction and yield positive upper/lower EV.
    rgb = np.zeros((160, 220, 3), dtype=np.uint8)
    rgb[:80, :, :] = 200
    rgb[80:, :, :] = 20
    y = exact_bt601_y(rgb)
    rg = mean_grid(y, GRID_R, GRID_C)
    rr = regions4x6(rg)
    assert rect_mean(rr, 0, 1, 0, 6) > rect_mean(rr, 2, 4, 0, 6)
    assert log2_ratio(rect_mean(rr, 0, 1, 0, 6), rect_mean(rr, 2, 4, 0, 6)) > 2.0
    print("M9EDGEPLACEMENT1A RENDERGRID1A self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("render_root", type=Path, nargs="?", help="directory containing frozen rendered JPEGs")
    ap.add_argument("--json-root", type=Path, help="directory containing matching M9 JSON sidecars/bundles")
    ap.add_argument("--labels", type=Path, default=None, help="optional pattern,label,m9ness,notes CSV")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RENDERGRID"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        self_test()
        return
    if not a.render_root or not a.json_root:
        ap.error("render_root and --json-root are required unless --self-test")

    json_index = index_json(a.json_root)
    labels = read_labels(a.labels)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for jpg in sorted(list(a.render_root.rglob("*.jpg")) + list(a.render_root.rglob("*.jpeg"))):
        key = render_key(jpg)
        if key in seen:
            # Multiple SAT variants or duplicate exports must not silently become
            # repeated votes. Keep the first deterministic path and report others.
            skipped.append({"captureKey": key, "renderFile": str(jpg), "reason": "duplicate_render_key"})
            continue
        seen.add(key)
        rec = json_index.get(key)
        if rec is None:
            skipped.append({"captureKey": key, "renderFile": str(jpg), "reason": "matching_preview_json_missing"})
            continue
        try:
            rows.append(feature_row(key, jpg, rec, labels))
        except Exception as e:
            skipped.append({"captureKey": key, "renderFile": str(jpg), "reason": f"feature_error:{e}"})

    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "rendergrid_features.csv", rows)
    write_csv(a.out / "rendergrid_skipped.csv", skipped)

    labelled = [r for r in rows if r.get("label") in LABELS]
    parity = [abs(float(r["previewIntegralParityErrorY"])) for r in rows if r.get("previewIntegralParityErrorY") is not None]
    summary = {
        "schema": "m9edgeplacement1a.rendergrid.v1",
        "mode": "research_only_finished_render_spatial_evidence_no_ev_no_live_selector",
        "renderCount": len(rows),
        "skippedCount": len(skipped),
        "labelCounts": {lab: sum(r.get("label") == lab for r in labelled) for lab in sorted(LABELS)},
        "maximumSavedVsRecomputedPreviewIntegralErrorY": max(parity) if parity else None,
        "integralMask": "exact_recovered_0x4001349c_sum14160",
        "regionalTopology": "4x6_24_regions_from_16x22_same_integer_partition_as_M10RMFMTEST1A",
        "luma": "exact_firmware_BT601_Q14_Y_from_finished_sRGB_JPEG_bytes",
        "invariant": "RENDERGRID1A produces evidence only; no feature or threshold is production authority and Frozen remains mandatory fallback.",
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
