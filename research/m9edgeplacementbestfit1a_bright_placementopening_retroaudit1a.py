#!/usr/bin/env python3
"""M9 BESTFIT1A — BRIGHT PLACEMENTOPENING RETROAUDIT1A.

Research-only. Pairs *_M9.json with matching *_M9_PRIMARY.json and computes
cross-pipeline preview->finished placement proxies. If a standalone PRIMARY
sidecar is absent, the tool may recover its exact staged payload from an
M9_DIAGNOSTICS_BURST_*.json bundle.

It preserves the existing LOWKEY seed, adds BOUNDARY_HOLD and BROADOPENING
reporting states, and never authorizes treatment.

Preview Y and finished BT.601 Y are different pipeline spaces. The log2 ratios
below are placement proxies, NOT capture/exposure EV.
"""
from __future__ import annotations

import argparse, csv, json, math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

INTENT_MAX_EV = 0.10
LOWKEY_SCORE_STRONG = 0.60
LOWKEY_SCORE_BOUNDARY = 0.50
TC20_GAIN_MIN = 1.50
FINISHED_MEDIAN_MIN_Y = 75.0


def load_json(path: Path) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x, dict):
        raise ValueError(f"top-level JSON not object: {path}")
    return x


def get_path(obj: Any, *keys: str) -> Any:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def fnum(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def first(*vals: Any) -> Any:
    return next((v for v in vals if v is not None), None)


def log_ratio(dst: Optional[float], src: Optional[float]) -> Optional[float]:
    if dst is None or src is None or dst <= 0 or src <= 0:
        return None
    return math.log2(dst / src)


def opening_sign_class(median_ev: Optional[float], q95_ev: Optional[float]) -> str:
    """Describe sign consistency only; this is not an eligibility decision."""
    if median_ev is None or q95_ev is None:
        return "MISSING"
    if median_ev > 0 and q95_ev > 0:
        return "BROAD_POSITIVE"
    if median_ev > 0 and q95_ev <= 0:
        return "BODY_POSITIVE_UPPER_NONPOSITIVE"
    if median_ev <= 0 and q95_ev > 0:
        return "UPPER_POSITIVE_BODY_NONPOSITIVE"
    return "RETAINED_OR_DENSER"


def stem_of(path: Path) -> str:
    suffix = "_M9.json"
    if not path.name.endswith(suffix) or path.name.endswith("_M9_PRIMARY.json"):
        raise ValueError(path)
    return path.name[:-len(suffix)]


def load_labels(path: Optional[Path]) -> list[dict]:
    if not path:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def match_label(stem: str, labels: list[dict]) -> dict:
    matches = [r for r in labels if r.get("pattern") and r["pattern"] in stem]
    if not matches:
        return {"visualLabel": "", "m9ness": "", "labelNotes": ""}
    r = max(matches, key=lambda x: len(x.get("pattern", "")))
    return {
        "visualLabel": r.get("label", ""),
        "m9ness": r.get("m9ness", ""),
        "labelNotes": r.get("notes", ""),
    }


def load_bundle_payloads(root: Path) -> dict[str, dict]:
    """Index exact staged sidecar payloads by publicFilename.

    Diagnostic bundles are a lossless metadata fallback for cases where the
    individual deferred sidecar export did not make it into the research copy.
    If duplicate filenames occur, the latest bundle by path sort wins; payload
    equality is not assumed and the source bundle is reported per row.
    """
    out: dict[str, dict] = {}
    for path in sorted(root.rglob("M9_DIAGNOSTICS_BURST_*.json")):
        try:
            obj = load_json(path)
        except Exception:
            continue
        entries = obj.get("entries")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("publicFilename")
            payload = entry.get("payload")
            if isinstance(name, str) and isinstance(payload, dict):
                out[name] = {
                    "payload": payload,
                    "bundlePath": str(path),
                    "role": entry.get("role"),
                    "sequence": entry.get("sequence"),
                }
    return out


def extract(capture: dict, primary: dict) -> dict:
    renderer = get_path(primary, "renderer") or {}
    direct = renderer.get("directRenderedLuma") or get_path(renderer, "renderMeterDiagnostic", "directRenderedLuma") or {}
    fg = direct.get("global") or {}
    fc = direct.get("center50") or {}
    pg = get_path(capture, "subjectMotion", "previewLuma", "global") or {}
    pc = get_path(capture, "subjectMotion", "previewLuma", "center50") or {}
    pb = get_path(capture, "m9SceneExposureDiagnostic", "positiveBodyPressure") or {}
    intent = first(
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPhotonOnlyEv"),
        get_path(capture, "m9ExposureAudit", "derived", "captureEnergyVsPreviewEv"),
    )
    out = {
        "achievedIntentEv": fnum(intent),
        "structuralLowKeyScore": fnum(pb.get("structuralLowKeyScore")),
        "tc20Gain": fnum(renderer.get("gain")),
        "baseMedianGain": fnum(renderer.get("baseMedianGain")),
        "tc20GuardGain": fnum(renderer.get("tc20GuardGain")),
        "previewGlobalMedianY": fnum(pg.get("median")),
        "previewGlobalQ95Y": fnum(pg.get("q95")),
        "previewGlobalQ99Y": fnum(pg.get("q99")),
        "previewCenterMedianY": fnum(pc.get("median")),
        "finishedGlobalMedianY": fnum(fg.get("median")),
        "finishedGlobalQ95Y": fnum(fg.get("q95")),
        "finishedGlobalQ99Y": fnum(fg.get("q99")),
        "finishedCenterMedianY": fnum(fc.get("median")),
        "finishedCenterQ95Y": fnum(fc.get("q95")),
    }
    out["globalMedianOpeningProxyEv"] = log_ratio(out["finishedGlobalMedianY"], out["previewGlobalMedianY"])
    out["globalQ95OpeningProxyEv"] = log_ratio(out["finishedGlobalQ95Y"], out["previewGlobalQ95Y"])
    out["globalQ99OpeningProxyEv"] = log_ratio(out["finishedGlobalQ99Y"], out["previewGlobalQ99Y"])
    out["centerMedianOpeningProxyEv"] = log_ratio(out["finishedCenterMedianY"], out["previewCenterMedianY"])
    med = out["globalMedianOpeningProxyEv"]
    q95 = out["globalQ95OpeningProxyEv"]
    out["broadOpeningMinProxyEv"] = min(med, q95) if med is not None and q95 is not None else None
    out["openingSignClass"] = opening_sign_class(med, q95)
    return out


def classify(x: dict) -> tuple[str, str]:
    intent, score, gain, body = (x.get(k) for k in (
        "achievedIntentEv", "structuralLowKeyScore", "tc20Gain", "finishedGlobalMedianY"))
    missing = [k for k, v in (("INTENT", intent), ("SCORE", score), ("GAIN", gain), ("BODY", body)) if v is None]
    if missing:
        return "OFF", "MISSING_" + "+".join(missing)
    base = intent < INTENT_MAX_EV and gain >= TC20_GAIN_MIN and body >= FINISHED_MEDIAN_MIN_Y
    if base and score >= LOWKEY_SCORE_STRONG:
        return "STRONG_CANDIDATE", "EXISTING_LOWKEY_SEED_ON"
    if base and LOWKEY_SCORE_BOUNDARY <= score < LOWKEY_SCORE_STRONG:
        return "BOUNDARY_HOLD", "SCORE_0P50_TO_0P60_FROZEN_ONLY"
    failed = []
    if not intent < INTENT_MAX_EV: failed.append("INTENT")
    if not score >= LOWKEY_SCORE_BOUNDARY: failed.append("SCORE")
    if not gain >= TC20_GAIN_MIN: failed.append("GAIN")
    if not body >= FINISHED_MEDIAN_MIN_Y: failed.append("BODY")
    return "OFF", "OFF_" + "+".join(failed)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--json", dest="json_out", type=Path)
    ap.add_argument("--csv", dest="csv_out", type=Path)
    args = ap.parse_args()

    labels = load_labels(args.labels)
    bundle_payloads = load_bundle_payloads(args.root)
    rows, unpaired = [], []
    standalone_primary_count = 0
    bundle_primary_count = 0

    for cp in sorted(args.root.rglob("*_M9.json")):
        if cp.name.endswith("_M9_PRIMARY.json"):
            continue
        stem = stem_of(cp)
        pp = cp.with_name(stem + "_M9_PRIMARY.json")
        primary_source = ""
        primary_source_path = ""

        if pp.exists():
            primary = load_json(pp)
            primary_source = "standalone_primary_sidecar"
            primary_source_path = str(pp)
            standalone_primary_count += 1
        else:
            expected_name = stem + "_M9_PRIMARY.json"
            recovered = bundle_payloads.get(expected_name)
            if not recovered:
                unpaired.append({
                    "frame": stem,
                    "captureJson": str(cp),
                    "missingPrimary": str(pp),
                    "bundleFallbackFound": False,
                })
                continue
            primary = recovered["payload"]
            primary_source = "diagnostic_bundle_primary_payload"
            primary_source_path = recovered["bundlePath"]
            bundle_primary_count += 1

        x = extract(load_json(cp), primary)
        state, reason = classify(x)
        rows.append({
            "frame": stem,
            "captureJson": str(cp),
            "primarySource": primary_source,
            "primarySourcePath": primary_source_path,
            **match_label(stem, labels),
            **x,
            "lowkeyResearchState": state,
            "lowkeyReason": reason,
        })

    # Rank likely falsifiers first: labeled GOOD/BOUNDARY with strongest broad opening.
    rows.sort(key=lambda r: (
        0 if r["visualLabel"] in ("GOOD", "BOUNDARY") else 1,
        -(r["broadOpeningMinProxyEv"] if r["broadOpeningMinProxyEv"] is not None else -999.0),
        r["frame"],
    ))

    states = Counter(r["lowkeyResearchState"] for r in rows)
    sign_classes = Counter(r["openingSignClass"] for r in rows)
    by_label = defaultdict(list)
    for r in rows:
        by_label[r["visualLabel"] or "UNLABELED"].append(r["globalMedianOpeningProxyEv"])
    label_summary = {}
    for label, vals in by_label.items():
        vv = sorted(v for v in vals if v is not None)
        label_summary[label] = {
            "count": len(vals), "proxyCount": len(vv),
            "minGlobalMedianOpeningProxyEv": vv[0] if vv else None,
            "maxGlobalMedianOpeningProxyEv": vv[-1] if vv else None,
        }

    result = {
        "schema": "m9edgeplacementbestfit1a.bright_placementopening_retroaudit1a.research.v3",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "authority": "none_proxy_diagnostics_only",
        "warning": "preview and finished Y are different pipeline spaces; log2 ratios are placement proxies, not exposure EV",
        "primaryRecovery": {
            "standalonePrimaryCount": standalone_primary_count,
            "diagnosticBundleFallbackCount": bundle_primary_count,
            "fallbackSemantics": "exact staged primary payload; no image reconstruction",
        },
        "existingLowkeySeedUnchanged": {
            "achievedIntentEvLt": INTENT_MAX_EV,
            "structuralLowKeyScoreGe": LOWKEY_SCORE_STRONG,
            "tc20GainGe": TC20_GAIN_MIN,
            "finishedGlobalMedianYGe": FINISHED_MEDIAN_MIN_Y,
        },
        "broadOpeningDiagnostic": {
            "definition": "min(globalMedianOpeningProxyEv, globalQ95OpeningProxyEv)",
            "signClassOnly": True,
            "noNumericAuthority": True,
            "centerAndQ99AreDiagnosticOnly": True,
        },
        "boundaryOverlay": {"scoreGe": LOWKEY_SCORE_BOUNDARY, "scoreLt": LOWKEY_SCORE_STRONG, "action": "HOLD_FROZEN"},
        "summary": {
            "pairedFrames": len(rows),
            "unpairedFrames": len(unpaired),
            "stateCounts": dict(states),
            "openingSignClassCounts": dict(sign_classes),
            "byVisualLabel": label_summary,
        },
        "unpaired": unpaired,
        "rows": rows,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    if args.csv_out and rows:
        with args.csv_out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
