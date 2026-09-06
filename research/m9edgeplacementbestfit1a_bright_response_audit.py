#!/usr/bin/env python3
"""Audit BRIGHT LOWKEY/BROADOPENING response from M9 diagnostic bundles.

Research-only. Reads JSON diagnostics and writes CSV/JSON summaries. It does not
modify capture policy, renderer pixels, DNGs, JPEGs, or Android source.

The harness deliberately separates:
  * structural LOWKEY morphology / eligibility
  * observed preview->finished BROADOPENING response
  * treatment/severity (not decided here)

Important schema rules:
  * achieved intent is taken first from the actual capture-energy audit path
    (`m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv`), with the preview
    comparison as a fallback; it is never silently assumed to be zero.
  * the LOWKEY gain floor uses TC20's **applied `gain`**, not `baseMedianGain`.
    `baseMedianGain` can be much larger on guard-limited frames and is retained
    only as diagnostic evidence.

The parser is tolerant of repeated diagnostic blocks, but conflicting values are
surfaced as ambiguous rather than silently resolved.
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


def get_path(obj: Any, *keys: str) -> Any:
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def as_number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def values_for_key(obj: Any, key: str) -> list[Any]:
    out = []
    for node in walk(obj):
        if isinstance(node, dict) and key in node:
            out.append(node[key])
    return out


def numeric_values_for_key(obj: Any, key: str) -> list[float]:
    out = []
    for v in values_for_key(obj, key):
        n = as_number(v)
        if n is not None:
            out.append(n)
    return out


def dedup_numeric(vals: list[float], tol: float = 1e-9) -> list[float]:
    uniq: list[float] = []
    for v in vals:
        if not any(abs(v-u) <= tol for u in uniq):
            uniq.append(v)
    return uniq


def unique_numeric(obj: Any, key: str, tol: float = 1e-9) -> tuple[float | None, list[float]]:
    uniq = dedup_numeric(numeric_values_for_key(obj, key), tol=tol)
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
    g = get_path(capture, "subjectMotion", "previewLuma", "global")
    if isinstance(g, dict):
        return g
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
    if not hits:
        return None, []

    pairs: list[tuple[float, float]] = []
    for g in hits:
        med = as_number(g.get("median"))
        q95 = as_number(g.get("q95"))
        if med is not None and q95 is not None:
            pairs.append((med, q95))
    if not pairs:
        return None, hits

    first = pairs[0]
    if any(abs(a-first[0]) > 1e-9 or abs(b-first[1]) > 1e-9 for a,b in pairs[1:]):
        return None, hits
    for g in hits:
        med = as_number(g.get("median"))
        q95 = as_number(g.get("q95"))
        if med is not None and q95 is not None and abs(med-first[0]) <= 1e-9 and abs(q95-first[1]) <= 1e-9:
            return g, hits
    return None, hits


def intent_value(capture: dict) -> tuple[float | None, dict[str, Any]]:
    """Resolve achieved capture intent from the real exposure-audit schema."""
    evidence: dict[str, Any] = {}

    photon_only = as_number(get_path(
        capture,
        "m9ExposureAudit",
        "derived",
        "captureEnergyVsPhotonOnlyEv",
    ))
    preview = as_number(get_path(
        capture,
        "m9ExposureAudit",
        "derived",
        "captureEnergyVsPreviewEv",
    ))
    if photon_only is not None:
        evidence["m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv"] = photon_only
        if preview is not None:
            evidence["m9ExposureAudit.derived.captureEnergyVsPreviewEv"] = preview
        return photon_only, evidence
    if preview is not None:
        evidence["m9ExposureAudit.derived.captureEnergyVsPreviewEv"] = preview
        return preview, evidence

    # Compatibility fallback for older/replayed research schemas.
    merged: list[float] = []
    for key in INTENT_KEYS:
        vals = dedup_numeric(numeric_values_for_key(capture, key))
        if vals:
            evidence[key] = vals
            merged.extend(vals)
    uniq = dedup_numeric(merged)
    return (uniq[0] if len(uniq) == 1 else None), evidence


def tc20_decision(primary: dict) -> tuple[dict[str, float | None], list[dict[str, float]]]:
    """Resolve TC20 applied gain triplet.

    The real TC20 decision contains all three keys `gain`, `baseMedianGain`, and
    `tc20GuardGain`. Repeated identical blocks are fine; conflicting triplets are
    treated as ambiguous.
    """
    triplets: list[dict[str, float]] = []
    for node in walk(primary):
        if not isinstance(node, dict):
            continue
        if not all(k in node for k in ("gain", "baseMedianGain", "tc20GuardGain")):
            continue
        gain = as_number(node.get("gain"))
        base = as_number(node.get("baseMedianGain"))
        guard = as_number(node.get("tc20GuardGain"))
        if gain is None or base is None or guard is None:
            continue
        candidate = {"gain": gain, "baseMedianGain": base, "tc20GuardGain": guard}
        if not any(
            abs(gain-x["gain"]) <= 1e-9
            and abs(base-x["baseMedianGain"]) <= 1e-9
            and abs(guard-x["tc20GuardGain"]) <= 1e-9
            for x in triplets
        ):
            triplets.append(candidate)

    if len(triplets) != 1:
        return {
            "gain": None,
            "baseMedianGain": None,
            "tc20GuardGain": None,
            "binding": None,
        }, triplets

    t = triplets[0]
    gain, base, guard = t["gain"], t["baseMedianGain"], t["tc20GuardGain"]
    eps = 1e-6
    if abs(gain-base) <= eps and gain <= guard + eps:
        binding = "median"
    elif abs(gain-guard) <= eps and gain < base - eps:
        binding = "guard"
    elif abs(base-guard) <= eps and abs(gain-base) <= eps:
        binding = "tie"
    else:
        binding = "other_or_clamped"

    return {
        "gain": gain,
        "baseMedianGain": base,
        "tc20GuardGain": guard,
        "binding": binding,
    }, triplets


def ev_ratio(out_y: float | None, in_y: float | None) -> float | None:
    if out_y is None or in_y is None or out_y <= 0 or in_y <= 0:
        return None
    return math.log2(out_y / in_y)


def as_float(d: dict | None, key: str) -> float | None:
    if not isinstance(d, dict):
        return None
    return as_number(d.get(key))


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
    tc20, tc20_triplets = tc20_decision(primary)
    intent, intent_evidence = intent_value(capture)

    pmed = as_float(pg, "median")
    pq95 = as_float(pg, "q95")
    fmed = as_float(fg, "median")
    fq95 = as_float(fg, "q95")
    med_shift = ev_ratio(fmed, pmed)
    q95_shift = ev_ratio(fq95, pq95)
    broad = bool(med_shift is not None and q95_shift is not None and med_shift > 0 and q95_shift > 0)

    applied_gain = as_number(tc20.get("gain"))
    core_no_intent = bool(
        score is not None and score >= LOWKEY_SCORE_MIN
        and applied_gain is not None and applied_gain >= LOWKEY_GAIN_MIN
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
        "tc20Gain": tc20.get("gain"),
        "baseMedianGain": tc20.get("baseMedianGain"),
        "tc20GuardGain": tc20.get("tc20GuardGain"),
        "tc20Binding": tc20.get("binding"),
        "tc20Triplets": json.dumps(tc20_triplets, separators=(",", ":"), sort_keys=True),
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
    ambiguous_tc20 = [r for r in valid if r.get("tc20Gain") is None]

    summary = {
        "schema": "m9edgeplacementbestfit1a.brightresponseaudit.v2",
        "researchOnly": True,
        "thresholds": {
            "lowkeyScoreMin": LOWKEY_SCORE_MIN,
            "lowkeyAppliedTc20GainMin": LOWKEY_GAIN_MIN,
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
        "ambiguousTc20Count": len(ambiguous_tc20),
        "ambiguousTc20Frames": [r["frame"] for r in ambiguous_tc20],
        "warning": (
            "LOWKEY uses applied TC20 gain, not baseMedianGain. If intent or the TC20 decision is absent/ambiguous, "
            "the frame must not be silently promoted into LOWKEY_BROAD."
        ),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
