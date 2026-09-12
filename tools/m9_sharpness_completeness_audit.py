#!/usr/bin/env python3
"""Falsification-oriented Leica M9 BF561 Sharpness completeness audit.

This tool asks whether the canonical BF561 image contains any Sharp/UM/Gauss
execution path that is not accounted for by the recovered Run ->
Process_Sharpness -> ASMUMGauss3LUT chain. It embeds no firmware bytes and
changes no renderer code.

A PASS means the *manual-ISO Sharp processing math/path* is structurally
accounted for in this firmware image. It deliberately does NOT close two
separate integration gates:
  1. Auto-ISO final nIso writer/active-object value.
  2. Exact post-Sharp buffer/lane alias into red/blue reconstruction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from m9_sharpnessforensics1a import parse_map, parse_ldr, read_overlay, long_branches

SHARP_KEYS = ("sharp", "gauss3lut", "um_gauss", "asmum")
KNOWN_SHARP_NAMES = {
    "Process_Sharpness",
    "ASMUMGauss3LUT",
    "UM_Gauss3LUT",
    "LoadAndModifySharpnessDa",
}
CORE_STAGE_NAMES = {
    "Process_WB",
    "GreenInterpolationWithCo",
    "Process_Noise",
    "Process_Sharpness",
    "ASMRedBlueInterpolation1",
    "ExecuteColorMatrix_14FM1",
    "Process_FPGA_YCrCb",
}
ZERO_WINDOW = 0x900


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def symbol_extent(s: dict) -> int:
    n = int(s.get("size", 0))
    return n if n > 0 else ZERO_WINDOW


def source_symbol(pc: int, syms: list[dict]) -> dict | None:
    # Prefer an explicit non-zero map extent. Fall back to the closest preceding
    # zero-size assembly label within the same forensic window.
    exact = [s for s in syms if int(s["size"]) > 0 and s["addr"] <= pc < s["addr"] + int(s["size"])]
    if exact:
        exact.sort(key=lambda s: (s["addr"], s["size"]), reverse=True)
        return exact[0]
    prior = [s for s in syms if s["addr"] <= pc and pc - s["addr"] < ZERO_WINDOW]
    if prior:
        prior.sort(key=lambda s: s["addr"], reverse=True)
        return prior[0]
    return None


def calls_for_symbol(s: dict, blocks: list[dict], exact: dict[int, list[str]]) -> list[dict]:
    code = read_overlay(blocks, s["addr"], symbol_extent(s))
    out = long_branches(code, s["addr"])
    for x in out:
        x["target_names"] = exact.get(x["target"], [])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldr", type=Path, required=True)
    ap.add_argument("--map", dest="map_path", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    syms = sorted(parse_map(a.map_path), key=lambda s: (s["addr"], s["mapoff"]))
    _, blocks = parse_ldr(a.ldr)
    exact: dict[int, list[str]] = defaultdict(list)
    by_name: dict[str, list[dict]] = defaultdict(list)
    for s in syms:
        exact[s["addr"]].append(s["name"])
        by_name[s["name"]].append(s)

    sharp_inventory = [
        {"name": s["name"], "address": hex(s["addr"]), "size": int(s["size"])}
        for s in syms
        if any(k in s["name"].lower() for k in SHARP_KEYS)
    ]
    inventory_names = sorted({x["name"] for x in sharp_inventory})
    unexpected_symbol_names = sorted(set(inventory_names) - KNOWN_SHARP_NAMES)

    # Build a global exact-target xref index. Only branches landing exactly on a
    # Sharp-related mapped address are retained, which makes data false positives
    # very unlikely and also exposes alternate callers outside the known wrappers.
    sharp_addrs = {s["addr"] for s in syms if s["name"] in KNOWN_SHARP_NAMES}
    global_xrefs: list[dict] = []
    for b in blocks:
        if not b["data"]:
            continue
        for x in long_branches(b["data"], b["addr"]):
            if x["target"] not in sharp_addrs:
                continue
            src = source_symbol(x["pc"], syms)
            global_xrefs.append({
                "pc": hex(x["pc"]),
                "type": x["type"],
                "target": hex(x["target"]),
                "target_names": exact.get(x["target"], []),
                "source_name": src["name"] if src else None,
                "source_address": hex(src["addr"]) if src else None,
            })

    # Enumerate every Run variant and score it by the known photographic stage
    # calls. This intentionally reports mirror/overlay chains instead of silently
    # discarding them.
    run_rows = []
    for s in by_name.get("Run", []):
        calls = calls_for_symbol(s, blocks, exact)
        names = [n for c in calls for n in c["target_names"]]
        core = sorted(set(names) & CORE_STAGE_NAMES)
        run_rows.append({
            "address": hex(s["addr"]),
            "size": int(s["size"]),
            "core_stage_score": len(core),
            "core_stage_names": core,
            "sharp_targets": [
                {"pc": hex(c["pc"]), "target": hex(c["target"]), "target_names": c["target_names"]}
                for c in calls if "Process_Sharpness" in c["target_names"]
            ],
        })
    run_rows.sort(key=lambda r: (r["core_stage_score"], int(r["address"], 16)), reverse=True)
    production_like_runs = [r for r in run_rows if r["core_stage_score"] >= 5 and r["sharp_targets"]]

    # Inspect every Process_Sharpness mapped variant. The key falsifier is an
    # alternate computational helper besides ASMUMGauss3LUT.
    process_rows = []
    for s in by_name.get("Process_Sharpness", []):
        calls = calls_for_symbol(s, blocks, exact)
        named_calls = [
            {"pc": hex(c["pc"]), "target": hex(c["target"]), "target_names": c["target_names"]}
            for c in calls if c["target_names"]
        ]
        process_rows.append({
            "address": hex(s["addr"]),
            "size": int(s["size"]),
            "named_calls": named_calls,
            "asmum_calls": [c for c in named_calls if "ASMUMGauss3LUT" in c["target_names"]],
            "um_gauss_calls": [c for c in named_calls if "UM_Gauss3LUT" in c["target_names"]],
        })

    # Resolve only Process_Sharpness variants reached by production-like Runs.
    active_process_addrs = {
        int(t["target"], 16)
        for r in production_like_runs for t in r["sharp_targets"]
    }
    active_process = [r for r in process_rows if int(r["address"], 16) in active_process_addrs]

    direct_run_to_um = [
        x for x in global_xrefs
        if x["source_name"] == "Run" and any(n in ("ASMUMGauss3LUT", "UM_Gauss3LUT") for n in x["target_names"])
    ]
    active_without_asmum = [r for r in active_process if len(r["asmum_calls"]) != 1]
    active_with_alt_um = [r for r in active_process if r["um_gauss_calls"]]

    # Xrefs are grouped rather than forced into a brittle allowed-list. Any
    # caller not belonging to the normal Run / Process / load-modify families is
    # surfaced as a review item, not hidden.
    unexplained_xrefs = [
        x for x in global_xrefs
        if x["source_name"] not in {
            "Run", "Process_Sharpness", "LoadAndModifySharpnessDa",
            "Set", "LoadLutDataL3", "CheckL1MemoryProcessing", "InitL1MemoryProcessing",
        }
    ]

    structural_pass = bool(production_like_runs) and bool(active_process) \
        and not active_without_asmum and not active_with_alt_um and not direct_run_to_um

    report = {
        "schema": "m9.sharpness-completeness-audit.v1",
        "ldr_sha256": h(a.ldr.read_bytes()),
        "map_sha256": h(a.map_path.read_bytes()),
        "scope": "BF561 manual-ISO Sharp processing structure; Auto ISO and post-Sharp R/B pointer alias are separate gates",
        "sharp_symbol_inventory": sharp_inventory,
        "unexpected_sharp_symbol_names": unexpected_symbol_names,
        "global_exact_sharp_xrefs": global_xrefs,
        "run_variants": run_rows,
        "production_like_runs": production_like_runs,
        "process_sharpness_variants": process_rows,
        "active_process_sharpness_variants": active_process,
        "falsifiers": {
            "active_process_without_exactly_one_ASMUMGauss3LUT": active_without_asmum,
            "active_process_calls_UM_Gauss3LUT": active_with_alt_um,
            "Run_directly_calls_UM_or_ASMUM": direct_run_to_um,
            "unexplained_exact_sharp_xrefs_for_review": unexplained_xrefs,
        },
        "closed_if_structural_pass": {
            "production_like_Run_reaches_Process_Sharpness": bool(production_like_runs),
            "active_Process_Sharpness_variants_resolved": bool(active_process),
            "active_Process_Sharpness_uses_ASMUMGauss3LUT": not active_without_asmum,
            "no_active_alternate_UM_Gauss3LUT_path": not active_with_alt_um,
            "no_Run_bypass_direct_to_kernel": not direct_run_to_um,
        },
        "structural_pass": structural_pass,
        "still_open_by_design": [
            "Auto ISO final active-object +0x34 / concrete BF561 nIso value",
            "exact Sharp-output buffer and packed lane alias into ASMRedBlueInterpolation1",
            "Xiaomi normalized16 -> Leica 14-bit quantization policy (firmware ceiling is known; conversion policy is not)",
        ],
    }

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "structural_pass": structural_pass,
        "sharp_symbol_names": inventory_names,
        "unexpected_sharp_symbol_names": unexpected_symbol_names,
        "production_like_runs": len(production_like_runs),
        "active_process_variants": len(active_process),
        "global_sharp_xrefs": len(global_xrefs),
        "unexplained_xrefs_for_review": len(unexplained_xrefs),
    }, indent=2, sort_keys=True))
    if not structural_pass:
        raise SystemExit("Sharp completeness structural hypothesis falsified")


if __name__ == "__main__":
    main()
