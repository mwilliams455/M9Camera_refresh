#!/usr/bin/env python3
"""M9 ISO/Sharp reverse-callgraph probe.

Research-only. Embeds no Leica firmware bytes and changes no renderer code.

Purpose:
- locate mapped BF561 implementations of LoadISODataL1 / Process_Sharpness /
  Process_Noise / Process_DNGNoise;
- extract their bytes from the Blackfin LDR overlay;
- compare LoadISODataL1 against the independently decoded M Monochrom helper;
- build a strict direct CALL/JUMP.L reverse callgraph from every mapped symbol;
- report which mapped functions directly reference the ISO helper and the Sharp/
  Noise functions.

A matching Monochrom LoadISODataL1 hash proves byte identity of that helper only;
it does not by itself assign the M9 13x4100-byte bank to sharpening or noise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any

MM_LOADISODATAL1_SHA256 = "32c47c722ff3c947da899ca4f545d65ecebd4ec7b92b8ffc7288d783e2fc764f"
TARGETS = {
    "LoadISODataL1",
    "Process_Sharpness",
    "Process_Noise",
    "Process_DNGNoise",
    "CalculateNoiseParameter",
    "Run",
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sx(x: int, n: int) -> int:
    return x - (1 << n) if x & (1 << (n - 1)) else x


def parse_map(path: Path) -> list[dict[str, Any]]:
    b = path.read_bytes()
    out: list[dict[str, Any]] = []
    for off in range(0, len(b) - 31, 32):
        r = b[off:off+32]
        name = r[:24].split(b"\0", 1)[0].decode("ascii", "ignore").rstrip("'")
        if not name:
            continue
        addr, size = struct.unpack_from("<II", r, 24)
        if size:
            out.append({"name": name, "addr": addr, "size": size, "mapoff": off})
    return out


def parse_ldr(path: Path) -> list[dict[str, Any]]:
    b = path.read_bytes()
    if len(b) < 4:
        raise ValueError("LDR too short")
    off = 4
    blocks = []
    while off + 10 <= len(b):
        addr, count, flags = struct.unpack_from("<IIH", b, off)
        off += 10
        data = bytes(count) if (flags & 1) else b[off:off+count]
        if not (flags & 1):
            off += count
        blocks.append({"addr": addr, "count": count, "flags": flags, "data": data})
        if flags & 0x8000:
            break
    return blocks


def overlay(blocks: list[dict[str, Any]], addr: int, size: int) -> tuple[bytes, int]:
    out = bytearray(size)
    covered = bytearray(size)
    for bl in blocks:
        ba, be = bl["addr"], bl["addr"] + bl["count"]
        s, e = max(addr, ba), min(addr + size, be)
        if e > s:
            out[s-addr:e-addr] = bl["data"][s-ba:e-ba]
            covered[s-addr:e-addr] = b"\x01" * (e-s)
    return bytes(out), sum(covered)


def long_branches(code: bytes, base: int) -> list[dict[str, int | str]]:
    out = []
    for off in range(0, len(code) - 3, 2):
        hi, lo = struct.unpack_from("<HH", code, off)
        if (hi & 0xFE00) == 0xE200:
            call = (hi >> 8) & 1
            imm = sx(((hi & 0xFF) << 16) | lo, 24) << 1
            pc = base + off
            out.append({
                "off": off,
                "pc": pc,
                "kind": "CALL" if call else "JUMP.L",
                "target": (pc + imm) & 0xFFFFFFFF,
            })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldr", type=Path, required=True)
    ap.add_argument("--map", dest="map_path", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("M9_ISO_SHARP_CONSUMER_PROBE.json"))
    args = ap.parse_args()

    syms = parse_map(args.map_path)
    blocks = parse_ldr(args.ldr)
    by_addr: dict[int, list[str]] = defaultdict(list)
    for s in syms:
        by_addr[s["addr"]].append(s["name"])

    functions = []
    reverse: dict[int, list[dict[str, Any]]] = defaultdict(list)
    target_instances: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for s in syms:
        code, covered = overlay(blocks, s["addr"], s["size"])
        if covered != s["size"]:
            continue
        branches = long_branches(code, s["addr"])
        entry = {
            "name": s["name"],
            "addr": hex(s["addr"]),
            "size": s["size"],
            "sha256": sha256(code),
            "calls": [],
        }
        for br in branches:
            names = by_addr.get(int(br["target"]), [])
            call = {**br, "target_hex": hex(int(br["target"])), "target_names": names}
            entry["calls"].append(call)
            reverse[int(br["target"])].append({
                "caller": s["name"],
                "caller_addr": hex(s["addr"]),
                "site": hex(int(br["pc"])),
                "kind": br["kind"],
            })
        functions.append(entry)
        if s["name"] in TARGETS:
            target_instances[s["name"]].append(entry)

    targets_report: dict[str, Any] = {}
    for name, entries in target_instances.items():
        enriched = []
        for e in entries:
            addr = int(e["addr"], 16)
            x = dict(e)
            x["reverse_xrefs"] = reverse.get(addr, [])
            if name == "LoadISODataL1":
                x["matches_mm_1_022_exact_helper"] = e["sha256"] == MM_LOADISODATAL1_SHA256
                x["mm_reference_semantics_if_exact_match"] = (
                    "return *(uint32_t *)(descriptor + 0x5C + 4*descriptor->iso_slot)"
                    if x["matches_mm_1_022_exact_helper"] else None
                )
            enriched.append(x)
        targets_report[name] = enriched

    report = {
        "schema": "m9.iso_sharp_consumer_probe.v1",
        "ldr_sha256": sha256(args.ldr.read_bytes()),
        "map_sha256": sha256(args.map_path.read_bytes()),
        "mm_reference": {
            "firmware": "M Monochrom 1.022",
            "LoadISODataL1_sha256": MM_LOADISODATAL1_SHA256,
            "semantics": "descriptor + 0x5C + 4*iso_slot -> uint32 entry",
        },
        "targets": targets_report,
        "evidence_policy": [
            "Exact helper hash match proves helper byte identity only.",
            "Direct xref proves a code reference, not photographic execution order.",
            "Do not label the M9 13x4100 bank Sharp or Noise without a closed pointer/data consumer trace.",
            "Do not infer runtime list order from Run dispatcher case order.",
        ],
    }
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({"out": str(args.out), "targets": sorted(targets_report)}, indent=2))


if __name__ == "__main__":
    main()
