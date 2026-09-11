#!/usr/bin/env python3
"""Extract additional M9 BF561 sharpness helper functions from an LDR/map pair.

Research-only; embeds no Leica firmware bytes. This complements
m9_sharpnessforensics1a.py without changing the frozen renderer.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

TARGETS = (
    "ASMUMGauss3LUT",
    "LoadAndModifySharpnessDa",
    "LoadISODataL1",
    "CalculateNoiseParameter",
    "Process_Sharpness",
    "Process_Noise",
    "Set",
)


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("m9sharp_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldr", type=Path, required=True)
    ap.add_argument("--map", dest="map_path", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base-tool", type=Path,
                    default=Path(__file__).with_name("m9_sharpnessforensics1a.py"))
    args = ap.parse_args()

    base = load_base(args.base_tool)
    syms = base.parse_map(args.map_path)
    _, blocks = base.parse_ldr(args.ldr)
    exact = {}
    for s in syms:
        exact.setdefault(s["addr"], []).append(s["name"])

    args.out.mkdir(parents=True, exist_ok=True)
    report = {"targets": {}}
    for name in TARGETS:
        matches = [s for s in syms if s["name"] == name]
        rows = []
        for i, s in enumerate(matches):
            code = base.read_overlay(blocks, s["addr"], s["size"])
            stem = f"{name}_{i:02d}_{s['addr']:08x}"
            (args.out / f"{stem}.bin").write_bytes(code)
            calls = base.long_branches(code, s["addr"])
            for c in calls:
                c["target_names"] = exact.get(c["target"], [])
            rows.append({
                "addr": hex(s["addr"]), "size": s["size"],
                "sha256": base.sha256(code), "calls": calls,
            })
        if rows:
            report["targets"][name] = rows
    (args.out / "deep_targets.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"out": str(args.out), "targets": sorted(report["targets"])}, indent=2))


if __name__ == "__main__":
    main()
