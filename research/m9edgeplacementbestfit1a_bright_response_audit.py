#!/usr/bin/env python3
"""Audit BRIGHT LOWKEY/BROADOPENING response from M9 diagnostic bundles.

Research-only. Reads JSON diagnostics and writes CSV/JSON summaries. It does not
modify capture policy, renderer pixels, DNGs, JPEGs, or Android source.

The harness deliberately separates:
  * structural LOWKEY morphology / eligibility
  * observed preview->finished BROADOPENING response
  * treatment/severity (not decided here)

It is intentionally tolerant of diagnostic-schema nesting: exact metric keys are
located recursively, but ambiguous conflicting values are surfaced rather than
silently resolved.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

LOWKEY_SCORE_MIN = 0.60
LOWKEY_GAIN_MIN = 1.50
LOWKEY_FINISHED_MEDIAN_MIN = 75.0
LOWKEY_INTENT_MAX = 0.10

INTENT_KEYS = (
    "achievedIntentEv",
    "achievedIntentEV",
    "intentAchievedEv",
    "intentEvAchieved",
)


def walk(obj: Any) -> Iterable[Any]:
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def values_for_key(obj: Any, key: str) -> list[Any]:
    out = []
    for node in walk(obj):
        if isinstance(node, dict) and key in node:
            out.append(node[key])
    return out


def numeric_values_for_key(obj: Any, key: str) -> list[float]:
    out = []
    for v in values_for_key(obj, key):
        try:
            if v is not None:
                out.append(float(v))
        except (TypeError, ValueError):
            pass
    return out


def unique_numeric(obj: Any, key: str, tol: float = 1e-9) -> tuple[float | None, list[float]]:
    vals = numeric_values_for_key(obj, key)
    if not vals:
        return None, []
    uniq: list[float] = []
    for v in vals:
        if not any(abs(v-u) <= tol for u in uniq):
            uniq.append(v)
    return (uniq[0] if len(uniq) == 1 else None), uniq


def bundle_entries(root: dict) -> tuple[dict | None, dict | None, str | None]:
    capture = None
    primary = None
    stem = None
    entries = root.get("entries") if isinstance(root, dict) else None
    if isinstance(entries, list):
        for e in entries:
            if not isinstance(e, dict):
                continue
            role = e.get("role")
            payload = e.get("payload")
            if role == "capture_metadata" and isinstance(payload, dict):
                capture = payload
                fn = e.get("publicFilename")
                if isinstance(fn, str):
                    stem = fn.removesuffix("_M9.json")
            elif role == "primary_timing" and isinstance(payload, dict):
                primary = payload
    return capture, primary, stem


def preview_global(capture: dict) -> dict | None:
    try:
        g = capture["subjectMotion"]["previewLuma"]["global"]
        if isinstance(g, dict):
            return g
    except Exception:
        pass
    for node in walk(capture):
        if not isinstance(node, dict):
            continue
        schema = node.get("schema")
        if isinstance(schema, str) and schema.startswith("m9cam.previewluma"):
            g = node.get("global")
            if isinstance(g, dict):
                return g
    return None


def finished_global(primary: dict) -> tuple[dict | None, list[dict]]:
    hits = []
    for node in walk(primary):
        if not isinstance(node, dict):
            continue
        schema = node.get("schema")
        if isinstance(schema, str) and schema.startswith("m9cam.renderedluma"):
            g = node.get("global")
            if isinstance(g, dict):
                hits.append(g)
    # Bundles can contain a repeated copy of the same rendered-luma block.
    # Deduplicate only when median/q95 agree; otherwise mark ambiguous.
    if not hits:
        return None, []
    pairs = []
    for g in hits:
        try:
            pairs.append((float(g["median"]), float(g["q95"])))
        except Exception:
            pairs.append((None, None))
    valid = [p for p in pairs if p[0] is not None and p[1] is not None]
    if not valid:
        return None, hits
    first = valid[0]
    if any(abs(a-first[0]) > 1e-9 or abs(b-first[1]) > 1e-9 for a,b in valid[1:]):
        return None, hits
    for g in hits:
        try:
            if abs(float(g["median"])-first[0]) <= 1e-9 and abs(float(g["q95"])-first[1]) <= 1e-9:
                return g, hits
        except Exception:
            pass
    return None, hits


def intent_value(capture: dict) -> tuple[float | None, dict[str, list[float]]]:
    evidence: dict[str, list[float]] = {}
    merged: list[float] = []
    for key in INTENT_KEYS:
        vals = numeric_values_for_key(capture, key)
        if vals:
            evidence[key] = vals
            merged.extend(vals)
    if not merged:
        return None, evidence
    first = merged[0]
    if any(abs(v-first) > 1e-9 for v in merged[1:]):
        return None, evidence
    return first, evidence


def ev_ratio(out_y: float | None, in_y: float | None) -> float | None:
    if out_y is None or in_y is None or out_y <= 0 or in_y <= 0:
        return None
    return math.log2(out_y / in_y)


def as_float(d: dict | None, key: str) -> float | None:
    if not isinstance(d, dict):
        return None
    try:
        return float(d[key])
    except Exception:
        return None


def audit_file(path: Path) -> dict:
    root = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    capture, primary, stem = bundle_entries(root)
    row = {
        "source": str(path),
        "frame": stem or "",
        "validBundle": bool(capture is not None and primary is not None),
    }
    if capture is None or primary is None:
        row["reason"] = "missing capture_metadata or primary_timing payload"
        return row

    pg = preview_global(capture)
    fg, fg_hits = finished_global(primary)
    score, score_values = unique_numeric(capture, "structuralLowKeyScore", tol=1e-6)
    gain, gain_values = unique_numeric(primary, "baseMedianGain", tol=1e-6)
    intent, intent_evidence = intent_value(capture)

    pmed = as_float(pg, "median")
    pq95 = as_float(pg, "q95")
    fmed = as_float(fg, "median")
    fq95 = as_float(fg, "q95")
    med_shift = ev_ratio(fmed, pmed)
    q95_shift = ev_ratio(fq95, pq95)
    broad = bool(med_shift is not None and q95_shift is not None and med_shift > 0 and q95_shift > 0)

    core_no_intent = bool(
        score is not None and score >= LOWKEY_SCORE_MIN
        and gain is not None and gain >= LOWKEY_GAIN_MIN
        and fmed is not None and fmed >= LOWKEY_FINISHED_MEDIAN_MIN
    )
    lowkey = None if intent is None else bool(core_no_intent and intent < LOWKEY_INTENT_MAX)
    lowkey_broad = None if lowkey is None else bool(lowkey and broad)

    row.update({
        "reason": "ok",
        "previewMedianY": pmed,
        "previewQ95Y": pq95,
        "finishedMedianY": fmed,
        "finishedQ95Y": fq95,
        "medianShiftEv": med_shift,
        "q95ShiftEv": q95_shift,
        "broadOpening": broad,
        "broadOpeningMinEv": min(med_shift, q95_shift) if broad else None,
        "structuralLowKeyScore": score,
        "structuralLowKeyScoreValues": json.dumps(score_values, separators=(",", ":")),
        "baseMedianGain": gain,
        "baseMedianGainValues": json.dumps(gain_values, separators=(",", ":")),
        "achievedIntentEv": intent,
        "intentEvidence": json.dumps(intent_evidence, separators=(",", ":"), sort_keys=True),
        "lowkeyCoreNoIntent": core_no_intent,
        "lowkeySeed": lowkey,
        "lowkeyBroad": lowkey_broad,
        "renderedLumaHitCount": len(fg_hits),
    })
    return row


def write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Directory containing M9 diagnostic bundle JSON files")
    ap.add_argument("--glob", default="M9_DIAGNOSTICS_BURST_*.json")
    ap.add_argument("--out", type=Path, default=Path("M9_BRIGHT_RESPONSE_AUDIT"))
    ap.add_argument("--expect-count", type=int, default=None)
    a = ap.parse_args()

    files = sorted(a.root.rglob(a.glob))
    if a.expect_count is not None and len(files) != a.expect_count:
        raise SystemExit(f"expected {a.expect_count} bundles, found {len(files)}")
    a.out.mkdir(parents=True, exist_ok=True)
    rows = [audit_file(p) for p in files]
    write_csv(a.out / "frames.csv", rows)

    valid = [r for r in rows if r.get("reason") == "ok"]
    broad = [r for r in valid if r.get("broadOpening") is True]
    core = [r for r in valid if r.get("lowkeyCoreNoIntent") is True]
    lowkey_known = [r for r in valid if r.get("lowkeySeed") is not None]
    lowkey = [r for r in valid if r.get("lowkeySeed") is True]
    lowkey_broad = [r for r in valid if r.get("lowkeyBroad") is True]
    missing_intent = [r for r in valid if r.get("achievedIntentEv") is None]

    summary = {
        "schema": "m9edgeplacementbestfit1a.brightresponseaudit.v1",
        "researchOnly": True,
        "thresholds": {
            "lowkeyScoreMin": LOWKEY_SCORE_MIN,
            "lowkeyGainMin": LOWKEY_GAIN_MIN,
            "lowkeyFinishedMedianMinY": LOWKEY_FINISHED_MEDIAN_MIN,
            "lowkeyIntentMaxEv": LOWKEY_INTENT_MAX,
            "broadOpening": "medianShiftEv>0 AND q95ShiftEv>0",
        },
        "bundleCount": len(files),
        "validCount": len(valid),
        "broadOpeningCount": len(broad),
        "broadOpeningFrames": [r["frame"] for r in broad],
        "lowkeyCoreNoIntentCount": len(core),
        "lowkeyCoreNoIntentFrames": [r["frame"] for r in core],
        "lowkeySeedKnownCount": len(lowkey_known),
        "lowkeySeedCount": len(lowkey),
        "lowkeySeedFrames": [r["frame"] for r in lowkey],
        "lowkeyBroadCount": len(lowkey_broad),
        "lowkeyBroadFrames": [r["frame"] for r in lowkey_broad],
        "missingIntentCount": len(missing_intent),
        "missingIntentFrames": [r["frame"] for r in missing_intent],
        "warning": (
            "If achievedIntentEv is absent from a diagnostic schema, lowkeySeed and lowkeyBroad remain unknown. "
            "Do not silently assume zero intent; use lowkeyCoreNoIntent only as a candidate prefilter."
        ),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
