#!/usr/bin/env python3
"""Extract BF561 green/noise/sharp/red-blue stages for dataflow forensics.

No firmware bytes are embedded. Input is a recovered BF561 LDR/map pair.
Some hand-written assembly labels are zero-sized in the map and overlap later
mapped symbols, so selected ASM labels are deliberately extracted through a
fixed forensic window rather than being truncated at the next symbol.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

from m9_sharpnessforensics1a import parse_map, parse_ldr, read_overlay, long_branches

TARGETS = [
    "Run",
    "GreenInterpolationWithCo",
    "Process_Noise",
    "Process_Sharpness",
    "ASMUMGauss3LUT",
    "ASMRedBlueInterpolation1",
    "ASMRedBlueAndGreenDiffer",
    "ASMFilter_010_101_010_2",
    "ASMFilter_101_040_101_An",
    "ASMFilter_101_000_101_2",
    "InitInterpolation",
    "StartInterpolation",
]

# Map size zero does not imply zero executable extent for Leica's hand-written
# assembly labels. Use a broad read-only window so the disassembler can expose
# the body/return and any nested aliases. We never republish the binary bytes.
ZERO_SIZE_WINDOW = 0x800


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldr", type=Path, required=True)
    ap.add_argument("--map", dest="map_path", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    syms = sorted(parse_map(a.map_path), key=lambda x: (x["addr"], x["mapoff"]))
    _, blocks = parse_ldr(a.ldr)
    exact: dict[int, list[str]] = {}
    for s in syms:
        exact.setdefault(s["addr"], []).append(s["name"])

    addrs = sorted(set(s["addr"] for s in syms))
    nxt = {v: addrs[i + 1] if i + 1 < len(addrs) else v + 0x100 for i, v in enumerate(addrs)}

    entries = []
    for wanted in TARGETS:
        matches = [s for s in syms if s["name"] == wanted]
        for idx, s in enumerate(matches):
            natural = int(s["size"])
            size = natural if natural > 0 else ZERO_SIZE_WINDOW
            code = read_overlay(blocks, s["addr"], size)
            calls = long_branches(code, s["addr"])
            for c in calls:
                c["target_names"] = exact.get(c["target"], [])
            stem = f"{wanted}_{idx:02d}_{s['addr']:08x}"
            fn = a.out / f"{stem}.bin"
            fn.write_bytes(code)
            entries.append({
                "name": wanted,
                "index": idx,
                "address": f"0x{s['addr']:08x}",
                "map_size": natural,
                "extracted_size": size,
                "zero_size_fixed_window": natural == 0,
                "next_symbol_address": f"0x{nxt[s['addr']]:08x}",
                "sha256": sha(code),
                "file": fn.name,
                "calls_or_long_jumps": calls,
            })

    candidates = []
    for s in syms:
        n = s["name"].lower()
        if any(k in n for k in ("green", "redblue", "red_blue", "interpol", "sharp", "noise", "gauss", "filter")):
            candidates.append({"name": s["name"], "address": f"0x{s['addr']:08x}", "size": s["size"]})

    report = {
        "schema": "m9.bf561-sharp-dataflow.v2",
        "ldr_sha256": sha(a.ldr.read_bytes()),
        "map_sha256": sha(a.map_path.read_bytes()),
        "zero_size_window": ZERO_SIZE_WINDOW,
        "targets": entries,
        "related_symbols": candidates,
    }
    (a.out / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
