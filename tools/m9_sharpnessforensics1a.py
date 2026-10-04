#!/usr/bin/env python3
"""Leica M9 SHARPNESSFORENSICS1A evidence extractor.

This tool embeds no Leica firmware bytes. It operates on locally extracted M9
firmware assets and emits evidence for the Sharp/Noise investigation without
modifying the production renderer.

Inputs may be either an extracted BF561 directory (bf0.bin + bf0.map), or
explicit files. Optional BF547 raw image and candidate ISO-bank payload enable
menu and ISO-bank probes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any

TARGETS = [
    "Run",
    "Process_Sharpness",
    "Process_Noise",
    "Process_DNGNoise",
    "Process_Shading",
    "Process_WB",
    "Process_FPGA_Y",
    "Process_FPGA_YCrCb",
    "ExecuteColorMatrix_14FM1",
    "Process_Contrast",
    "SetStructParameter",
    "SetLutL3",
    "LoadISODataL1",
    "LoadLutArchiveL3",
    "CalculateNoiseParameter",
]

FIELD_STRINGS = [
    "nIso", "nContrast", "nSaturation", "nNoise", "nSharpness", "nSharp",
    "nColorSpace", "Shading", "WhiteBalance", "Noise", "Sharp",
    "InterpolationRedBlue", "ColorMatrix", "ConvertYCrCb",
]

MENU_NAMES = [b"Low ", b"Medium low ", b"Standard", b"Medium high ", b"High "]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sx(x: int, n: int) -> int:
    return x - (1 << n) if x & (1 << (n - 1)) else x


def parse_map(path: Path) -> list[dict[str, Any]]:
    b = path.read_bytes()
    out = []
    for off in range(0, len(b) - 31, 32):
        r = b[off : off + 32]
        name = r[:24].split(b"\0", 1)[0].decode("ascii", "ignore").rstrip("'")
        if not name:
            continue
        addr, size = struct.unpack_from("<II", r, 24)
        out.append({"name": name, "addr": addr, "size": size, "mapoff": off})
    return out


def parse_ldr(path: Path) -> tuple[int, list[dict[str, Any]]]:
    b = path.read_bytes()
    if len(b) < 4:
        raise ValueError("LDR too short")
    global_header = struct.unpack_from("<I", b, 0)[0]
    off = 4
    blocks = []
    while off + 10 <= len(b):
        addr, count, flags = struct.unpack_from("<IIH", b, off)
        header_off = off
        off += 10
        if flags & 1:
            data = bytes(count)
        else:
            data = b[off : off + count]
            off += count
        blocks.append({"addr": addr, "count": count, "flags": flags, "data": data, "header_off": header_off})
        if flags & 0x8000:
            break
    return global_header, blocks


def read_overlay(blocks: list[dict[str, Any]], addr: int, size: int) -> bytes:
    out = bytearray(size)
    for block in blocks:
        ba = block["addr"]
        be = ba + block["count"]
        s = max(addr, ba)
        e = min(addr + size, be)
        if e > s:
            out[s - addr : e - addr] = block["data"][s - ba : e - ba]
    return bytes(out)


def long_branches(code: bytes, base: int) -> list[dict[str, Any]]:
    """Decode only the 32-bit Blackfin CALL/JUMP.L form used by prior M9 work."""
    out = []
    for off in range(0, len(code) - 3, 2):
        hi, lo = struct.unpack_from("<HH", code, off)
        if (hi & 0xFE00) == 0xE200:
            s = (hi >> 8) & 1
            imm = sx(((hi & 0xFF) << 16) | lo, 24) << 1
            pc = base + off
            out.append({
                "off": off,
                "pc": pc,
                "type": "CALL" if s else "JUMP.L",
                "rel": imm,
                "target": (pc + imm) & 0xFFFFFFFF,
            })
    return out


def extract_bf561(ldr: Path, map_path: Path, outdir: Path) -> dict[str, Any]:
    syms = parse_map(map_path)
    gh, blocks = parse_ldr(ldr)
    exact = defaultdict(list)
    for s in syms:
        exact[s["addr"]].append(s["name"])

    report: dict[str, Any] = {
        "global_header": hex(gh),
        "map_sha256": sha256(map_path.read_bytes()),
        "ldr_sha256": sha256(ldr.read_bytes()),
        "targets": {},
    }
    fdir = outdir / "bf561_functions"
    fdir.mkdir(parents=True, exist_ok=True)

    for name in TARGETS:
        matches = [s for s in syms if s["name"] == name]
        entries = []
        for index, s in enumerate(matches):
            code = read_overlay(blocks, s["addr"], s["size"])
            calls = long_branches(code, s["addr"])
            for c in calls:
                c["target_names"] = exact.get(c["target"], [])
            stem = f"{name}_{index:02d}_{s['addr']:08x}"
            (fdir / f"{stem}.bin").write_bytes(code)
            (fdir / f"{stem}.hex.txt").write_text(
                "\n".join(f"{s['addr']+o:08x}: {code[o:o+16].hex(' ')}" for o in range(0, len(code), 16))
            )
            entries.append({
                "addr": hex(s["addr"]),
                "size": s["size"],
                "mapoff": hex(s["mapoff"]),
                "sha256": sha256(code),
                "calls": calls,
            })
        if entries:
            report["targets"][name] = entries
    return report


def ascii_occurrences(data: bytes, needle: bytes) -> list[int]:
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def cstr(data: bytes, off: int) -> str | None:
    if not (0 <= off < len(data)):
        return None
    raw = data[off : off + 96].split(b"\0", 1)[0]
    try:
        s = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    if not s or any(ord(ch) < 32 or ord(ch) > 126 for ch in s):
        return None
    return s


def detect_menu_records(bf547: bytes) -> dict[str, Any]:
    """Find 20-byte Leica menu records without assigning property semantics.

    Known M-generation menu records begin with a pointer to a NUL-terminated
    label plus a 32-bit enum value. We search common RAM deltas and report
    five-record Low..High sequences. Multiple hits are expected; xrefs are
    needed to label Contrast vs Sharpness vs other five-state properties.
    """
    result: dict[str, Any] = {"field_strings": {}, "five_state_candidates": []}
    for text in FIELD_STRINGS:
        result["field_strings"][text] = [hex(x) for x in ascii_occurrences(bf547, text.encode("ascii"))]

    deltas = [0, 0x20000, 0x40000, 0x80000, 0x100000]
    seen = set()
    for delta in deltas:
        for off in range(0, max(0, len(bf547) - 5 * 20), 4):
            rows = []
            ok = True
            for j in range(5):
                ro = off + j * 20
                ptr, val = struct.unpack_from("<II", bf547, ro)
                so = ptr - delta
                label = cstr(bf547, so)
                if val != j or label is None:
                    ok = False
                    break
                if not label.startswith(MENU_NAMES[j].decode("ascii").strip()):
                    ok = False
                    break
                rows.append({"record_off": hex(ro), "ptr": hex(ptr), "string_off": hex(so), "label": label, "value": val})
            if ok:
                key = (off, delta)
                if key not in seen:
                    seen.add(key)
                    result["five_state_candidates"].append({"table_off": hex(off), "ram_delta": hex(delta), "rows": rows})
    return result


def analyze_4100_bank(data: bytes) -> dict[str, Any]:
    """Describe repeated 4100-byte blocks; do not assign semantics."""
    n = len(data) // 4100
    blocks = [data[i*4100:(i+1)*4100] for i in range(n)]
    hashes = [sha256(x) for x in blocks]
    groups: dict[str, list[int]] = defaultdict(list)
    for i, h in enumerate(hashes):
        groups[h].append(i)
    return {
        "bytes": len(data),
        "complete_4100_blocks": n,
        "tail_bytes": len(data) - n * 4100,
        "groups": [{"sha256": h, "indices": idxs} for h, idxs in groups.items()],
    }


def hypothesis_table() -> list[dict[str, str]]:
    return [
        {"offset": "+9", "role": "nIso", "status": "proven in homologous M-generation record trace; verify on M9"},
        {"offset": "+10", "role": "nContrast", "status": "already proven in M9 / homologous trace"},
        {"offset": "+11", "role": "nSaturation", "status": "proven in homologous record trace; verify on M9"},
        {"offset": "+12", "role": "nNoise", "status": "proven in homologous record trace; verify on M9"},
        {"offset": "+13", "role": "nSharpness ?", "status": "HYPOTHESIS ONLY: gap between nNoise and nColorSpace; must be proven from M9 BF547/BF561"},
        {"offset": "+14", "role": "nColorSpace", "status": "already proven in M9 / homologous trace"},
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bf561-dir", type=Path, help="Directory containing bf0.bin and bf0.map")
    ap.add_argument("--ldr", type=Path, help="Explicit BF561 bf0.bin")
    ap.add_argument("--map", dest="map_path", type=Path, help="Explicit BF561 bf0.map")
    ap.add_argument("--bf547", type=Path, help="Optional extracted BF547 binary/lump")
    ap.add_argument("--iso-bank", type=Path, help="Optional isolated candidate 13x4100-byte bank")
    ap.add_argument("--out", type=Path, default=Path("SHARPNESSFORENSICS1A_OUT"))
    args = ap.parse_args()

    if args.bf561_dir:
        ldr = args.bf561_dir / "bf0.bin"
        map_path = args.bf561_dir / "bf0.map"
    else:
        ldr, map_path = args.ldr, args.map_path
    if not ldr or not map_path:
        ap.error("provide --bf561-dir or both --ldr and --map")
    if not ldr.exists() or not map_path.exists():
        ap.error("BF561 LDR/map input missing")

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "m9.sharpnessforensics1a.v1",
        "record_field_evidence": hypothesis_table(),
        "bf561": extract_bf561(ldr, map_path, out),
    }
    if args.bf547:
        data = args.bf547.read_bytes()
        report["bf547"] = {
            "sha256": sha256(data),
            "size": len(data),
            **detect_menu_records(data),
        }
    if args.iso_bank:
        data = args.iso_bank.read_bytes()
        report["iso_bank"] = analyze_4100_bank(data)

    (out / "report.json").write_text(json.dumps(report, indent=2))
    (out / "README.txt").write_text(
        "SHARPNESSFORENSICS1A evidence extraction\n"
        "\n"
        "Important: +13=nSharpness is intentionally marked hypothesis-only.\n"
        "Do not implement SHARPNESSSTD1A until M9 consumer/menu evidence closes it.\n"
        "The 4100-byte ISO bank is fingerprinted only; no semantic label is assigned.\n"
    )
    print(json.dumps({
        "out": str(out),
        "targets": sorted(report["bf561"]["targets"].keys()),
        "bf547": bool(args.bf547),
        "iso_bank": bool(args.iso_bank),
    }, indent=2))


if __name__ == "__main__":
    main()
