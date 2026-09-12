#!/usr/bin/env python3
"""Extract M9 BF561 sharpness helpers plus a keyword-driven symbol inventory.

Research-only; embeds no Leica firmware bytes and changes no renderer code.
The inventory prevents initializer discovery from depending on guessed symbol names.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

EXACT_TARGETS = (
    "ASMUMGauss3LUT",
    "LoadAndModifySharpnessDa",
    "LoadISODataL1",
    "CalculateNoiseParameter",
    "Process_Sharpness",
    "Process_Noise",
    "Set",
    # Run calls InitL1MemoryProcessing before the processing-bit dispatcher.
    # These two functions are the best firmware-side candidates for seeding the
    # Sharp working-LUT pointer/count that LoadLutDataL3 itself does not write.
    "InitL1MemoryProcessing",
    "CheckL1MemoryProcessing",
)
KEYWORDS = ("sharp", "lut", "iso", "noise")

# Canonical BF547 disassembly at runtime 0x6c800 comes from BF547.bin file
# offset 0x4c800, establishing the +0x20000 image base used by these pointers.
BF547_RUNTIME_BASE = 0x20000

# The controller diagnostic at runtime ~0x6ca38 reads individual processing-
# record bytes and passes each to a field-specific firmware string.  These are
# the string pointers paired with the observed record offsets in that routine.
# Keeping the mapping explicit lets the firmware itself name record +0x0d.
RECORD_FIELD_LABEL_PTRS = {
    "0x07": 0x0F52F0,
    "0x08": 0x0F52FC,
    "0x09": 0x0F530C,
    "0x0a": 0x0F5314,
    "0x0b": 0x0F5320,
    "0x0d": 0x0F532C,
    "0x0e": 0x0F5334,
    "0x15": 0x0F5340,
    "0x17_0x18": 0x0F5350,
    "0x16": 0x0F5358,
    "0x19": 0x0F5360,
}


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("m9sharp_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:80]


def read_c_string(data: bytes, off: int, max_len: int = 96) -> dict[str, object]:
    if off < 0 or off >= len(data):
        return {"in_range": False, "file_offset": hex(off)}
    end = min(len(data), off + max_len)
    raw = data[off:end].split(b"\0", 1)[0]
    printable = all((0x20 <= b < 0x7f) or b in (9, 10, 13) for b in raw)
    return {
        "in_range": True,
        "file_offset": hex(off),
        "raw_hex": raw.hex(" "),
        "ascii": raw.decode("ascii", "replace") if printable else None,
        "printable_ascii": printable,
    }


def bf547_record_field_labels(ldr_path: Path) -> dict[str, object]:
    pass_root = ldr_path.parent.parent
    bf547 = pass_root / "bf547_00" / "BF547.bin"
    if not bf547.exists():
        return {"available": False, "path": str(bf547)}
    data = bf547.read_bytes()
    rows = {}
    for field_off, runtime in RECORD_FIELD_LABEL_PTRS.items():
        file_off = runtime - BF547_RUNTIME_BASE
        rows[field_off] = {
            "runtime_address": hex(runtime),
            **read_c_string(data, file_off),
        }
    return {
        "available": True,
        "bf547_path": str(bf547),
        "bf547_size": len(data),
        "runtime_base": hex(BF547_RUNTIME_BASE),
        "evidence_scope": (
            "Direct strings paired by the BF547 diagnostic routine with the listed "
            "processing-record offsets; names the field but does not by itself prove "
            "the later BF561 consumer."
        ),
        "fields": rows,
    }


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

    keyword_syms = [s for s in syms if any(k in s["name"].lower() for k in KEYWORDS)]
    names = list(EXACT_TARGETS)
    for s in keyword_syms:
        if s["name"] not in names:
            names.append(s["name"])

    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "keywords": list(KEYWORDS),
        "symbol_inventory": [
            {"name": s["name"], "addr": hex(s["addr"]), "size": s["size"], "mapoff": hex(s["mapoff"])}
            for s in keyword_syms
        ],
        "bf547_record_field_labels": bf547_record_field_labels(args.ldr),
        "targets": {},
    }
    for name in names:
        matches = [s for s in syms if s["name"] == name]
        rows = []
        for i, s in enumerate(matches):
            code = base.read_overlay(blocks, s["addr"], s["size"])
            stem = f"{safe_name(name)}_{i:02d}_{s['addr']:08x}"
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
    print(json.dumps({
        "out": str(args.out),
        "keyword_symbol_count": len(keyword_syms),
        "keyword_symbols": [s["name"] for s in keyword_syms],
        "bf547_field_labels_available": report["bf547_record_field_labels"].get("available", False),
        "targets": sorted(report["targets"]),
    }, indent=2))


if __name__ == "__main__":
    main()
