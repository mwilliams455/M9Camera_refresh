#!/usr/bin/env python3
"""M9 SHARPNESSFORENSICS1A firmware-direct pass.

This companion to m9_sharpnessforensics1a.py accepts a decrypted M9 updater,
walks nested PWAD payloads, identifies BF547 and *candidate* BF561 bf0/map
assets conservatively, and adds BF547 pointer/xref evidence around Sharp and
five-state Leica menu tables.

No Leica firmware bytes are embedded. No renderer code is modified. The
script deliberately does NOT promote +13=nSharpness, Standard=2, a menu table,
or a 4100-byte ISO bank to proven status from proximity/shape alone.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

RAM_DELTAS = (0, 0x20000, 0x40000, 0x80000, 0x100000)
STAGE_WORDS = (
    "Sharp", "Noise", "DNGNoise", "Shading", "WhiteBalance",
    "InterpolationRedBlue", "ColorMatrix", "ConvertYCrCb", "Contrast",
)
FIELD_WORDS = (
    "nIso", "nContrast", "nSaturation", "nNoise", "nSharpness", "nSharp",
    "nColorSpace",
)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class Lump:
    path: str
    name: str
    data: bytes


def parse_pwad(data: bytes) -> list[tuple[str, bytes]]:
    if len(data) < 12 or data[:4] != b"PWAD":
        raise ValueError("not PWAD")
    count, directory = struct.unpack_from("<II", data, 4)
    if directory + 16 * count > len(data):
        raise ValueError("PWAD directory exceeds payload")
    out = []
    for i in range(count):
        off, size, raw = struct.unpack_from("<II8s", data, directory + 16 * i)
        if off + size > len(data):
            raise ValueError(f"PWAD entry {i} exceeds payload")
        name = raw.split(b"\0", 1)[0].decode("ascii", "replace")
        out.append((name, data[off:off + size]))
    return out


def walk_pwad(data: bytes, prefix: str = "") -> Iterable[Lump]:
    for name, payload in parse_pwad(data):
        path = f"{prefix}/{name}" if prefix else name
        yield Lump(path, name, payload)
        if payload[:4] == b"PWAD":
            yield from walk_pwad(payload, path)


def find_root_pwad(raw: bytes) -> tuple[int, bytes]:
    if raw[:4] == b"PWAD":
        return 0, raw
    hits = []
    pos = 0
    while True:
        pos = raw.find(b"PWAD", pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
        if len(hits) >= 16:
            break
    valid = []
    for h in hits:
        try:
            parse_pwad(raw[h:])
        except Exception:
            continue
        valid.append(h)
    if not valid:
        raise ValueError("no valid PWAD root found")
    if valid[0] > 0x1000:
        raise ValueError(f"first valid PWAD root is unexpectedly late: 0x{valid[0]:x}")
    return valid[0], raw[valid[0]:]


def map_records(data: bytes) -> list[tuple[str, int, int]]:
    if len(data) < 32 or len(data) % 32:
        return []
    out = []
    printable = 0
    for off in range(0, len(data), 32):
        r = data[off:off + 32]
        raw_name = r[:24].split(b"\0", 1)[0]
        try:
            name = raw_name.decode("ascii").rstrip("'")
        except UnicodeDecodeError:
            return []
        if name:
            printable += 1
        addr, size = struct.unpack_from("<II", r, 24)
        out.append((name, addr, size))
    if printable < max(5, len(out) // 4):
        return []
    return out


def is_sharp_map(data: bytes) -> bool:
    recs = map_records(data)
    if not recs:
        return False
    names = {r[0] for r in recs}
    return {"Process_Sharpness", "Process_Noise"}.issubset(names)


def parse_ldr_blocks(data: bytes) -> list[tuple[int, int, int, bytes]]:
    if len(data) < 14:
        return []
    off = 4
    blocks = []
    try:
        while off + 10 <= len(data):
            addr, count, flags = struct.unpack_from("<IIH", data, off)
            off += 10
            if count > 16 * 1024 * 1024:
                return []
            if flags & 1:
                payload = bytes(count)
            else:
                if off + count > len(data):
                    return []
                payload = data[off:off + count]
                off += count
            blocks.append((addr, count, flags, payload))
            if flags & 0x8000:
                break
    except struct.error:
        return []
    return blocks if blocks else []


def ldr_covers_map(ldr: bytes, m: bytes) -> dict[str, Any]:
    blocks = parse_ldr_blocks(ldr)
    if not blocks:
        return {"valid_ldr": False, "covered": 0, "checked": 0}
    recs = [r for r in map_records(m) if r[0] in {
        "Run", "Process_Sharpness", "Process_Noise", "Process_DNGNoise",
        "Process_WB", "ExecuteColorMatrix_14FM1", "Process_FPGA_YCrCb",
    }]
    checked = 0
    covered = 0
    for _, addr, size in recs:
        if size <= 0:
            continue
        checked += 1
        end = addr + size
        if any(addr >= ba and end <= ba + count for ba, count, _, _ in blocks):
            covered += 1
    return {"valid_ldr": True, "covered": covered, "checked": checked}


def ascii_hits(data: bytes, text: str) -> list[int]:
    needle = text.encode("ascii")
    out, start = [], 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def u32_hits(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    out, start = [], 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def pointer_xrefs(data: bytes, file_off: int) -> list[dict[str, str]]:
    out = []
    for delta in RAM_DELTAS:
        addr = file_off + delta
        for x in u32_hits(data, addr):
            out.append({"delta": hex(delta), "pointer": hex(addr), "xref_off": hex(x)})
    return out


def window(data: bytes, off: int, radius: int = 64) -> dict[str, str]:
    a, b = max(0, off - radius), min(len(data), off + radius)
    return {"start": hex(a), "end": hex(b), "hex": data[a:b].hex(" ")}


def scan_bf547(data: bytes, base_tool: Any) -> dict[str, Any]:
    strings: dict[str, Any] = {}
    for text in FIELD_WORDS + STAGE_WORDS:
        rows = []
        for off in ascii_hits(data, text):
            refs = pointer_xrefs(data, off)
            rows.append({
                "string_off": hex(off),
                "xrefs": refs,
                "xref_windows": [window(data, int(r["xref_off"], 16)) for r in refs[:12]],
            })
        strings[text] = rows

    menus = base_tool.detect_menu_records(data).get("five_state_candidates", [])
    menu_rows = []
    sharp_refs = []
    for key in ("Sharp", "nSharp", "nSharpness"):
        for s in strings.get(key, []):
            sharp_refs.extend(int(r["xref_off"], 16) for r in s["xrefs"])

    for m in menus:
        off = int(m["table_off"], 16)
        delta = int(m["ram_delta"], 16)
        addr = off + delta
        refs = u32_hits(data, addr)
        nearest = None
        if refs and sharp_refs:
            nearest = min(abs(a - b) for a in refs for b in sharp_refs)
        menu_rows.append({
            **m,
            "table_addr": hex(addr),
            "table_xrefs": [hex(x) for x in refs],
            "table_xref_windows": [window(data, x) for x in refs[:12]],
            "nearest_sharp_xref_distance": nearest,
            "semantic_status": "UNASSIGNED — xref proximity is clue only, not Sharpness proof",
        })

    constants = {}
    for label, value, width in (
        ("record_stride_68", 68, 4),
        ("processing_list_956", 956, 4),
        ("max_records_14", 14, 4),
    ):
        needle = value.to_bytes(width, "little")
        hits, start = [], 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            hits.append(i)
            start = i + 1
        constants[label] = {
            "value": value,
            "count": len(hits),
            "hits": [hex(x) for x in hits[:200]],
            "windows": [window(data, x, 40) for x in hits[:30]],
        }

    return {
        "sha256": sha256(data), "size": len(data),
        "strings": strings,
        "five_state_menu_candidates": menu_rows,
        "processing_list_literal_breadcrumbs": constants,
    }


def load_base_tool(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("m9_sharpness_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import base extractor: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def parent_path(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("firmware", type=Path, help="decrypted M9 updater/container")
    ap.add_argument("--base-tool", type=Path,
                    default=Path(__file__).with_name("m9_sharpnessforensics1a.py"))
    ap.add_argument("--out", type=Path, default=Path("SHARPNESSFORENSICS1A_FIRMWAREPASS"))
    args = ap.parse_args()

    base = load_base_tool(args.base_tool)
    raw = args.firmware.read_bytes()
    root_off, root = find_root_pwad(raw)
    lumps = list(walk_pwad(root))
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    bf547s = [x for x in lumps if x.name.upper() == "BF547"]
    map_candidates = [x for x in lumps if is_sharp_map(x.data)]
    ldr_candidates = [x for x in lumps if parse_ldr_blocks(x.data)]

    if not bf547s:
        raise RuntimeError("no BF547 lump found")
    if not map_candidates:
        raise RuntimeError("no map-like payload containing Process_Sharpness + Process_Noise found")

    pair_scores = []
    for m in map_candidates:
        for l in ldr_candidates:
            score = ldr_covers_map(l.data, m.data)
            same_parent = parent_path(l.path) == parent_path(m.path)
            pair_scores.append({
                "map_path": m.path, "ldr_path": l.path,
                "same_parent": same_parent, **score,
            })
    pair_scores.sort(key=lambda r: (r["covered"], r["same_parent"], r["checked"]), reverse=True)

    deep = []
    for idx, pair in enumerate(pair_scores[:12]):
        if pair["covered"] <= 0:
            continue
        m = next(x for x in map_candidates if x.path == pair["map_path"])
        l = next(x for x in ldr_candidates if x.path == pair["ldr_path"])
        pdir = out / f"bf561_pair_{idx:02d}"
        pdir.mkdir(exist_ok=True)
        mp = pdir / "bf0.map"
        lp = pdir / "bf0.bin"
        mp.write_bytes(m.data)
        lp.write_bytes(l.data)
        try:
            detail = base.extract_bf561(lp, mp, pdir)
        except Exception as e:
            detail = {"error": f"{type(e).__name__}: {e}"}
        deep.append({**pair, "detail": detail})

    bf547_reports = []
    for i, lump in enumerate(bf547s):
        bdir = out / f"bf547_{i:02d}"
        bdir.mkdir(exist_ok=True)
        (bdir / "BF547.bin").write_bytes(lump.data)
        bf547_reports.append({"path": lump.path, **scan_bf547(lump.data, base)})

    report = {
        "schema": "m9.sharpnessforensics1a.firmwarepass.v1",
        "firmware": {
            "path": str(args.firmware), "sha256": sha256(raw),
            "root_pwad_offset": hex(root_off), "lump_count_recursive": len(lumps),
        },
        "policy": {
            "+13": "HYPOTHESIS ONLY; do not label nSharpness without M9 consumer/xref proof",
            "sharpness_standard": "NOT PROVEN; do not infer enum 2 from Contrast",
            "five_state_tables": "UNASSIGNED until property xref closes identity",
            "run_order": "NOT photographic pipeline order",
            "iso_4100_bank": "UNASSIGNED until consumer is proven",
        },
        "asset_candidates": {
            "bf547": [x.path for x in bf547s],
            "maps": [x.path for x in map_candidates],
            "ldrs": [x.path for x in ldr_candidates],
        },
        "bf561_pair_scores": pair_scores,
        "bf561_deep": deep,
        "bf547": bf547_reports,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2))

    lines = [
        "# SHARPNESSFORENSICS1A firmware-direct pass", "",
        f"Firmware SHA256: `{report['firmware']['sha256']}`",
        f"Recursive PWAD lumps: {len(lumps)}", "",
        "## Evidence policy", "",
        "- `+13 = nSharpness` remains hypothesis-only.",
        "- Sharpness `Standard = 2` is not assumed from Contrast.",
        "- Five-state menu tables remain unassigned until xrefs identify the property.",
        "- BF561 `Run` dispatch order is not used as pipeline order.",
        "- 4100-byte ISO resources remain unassigned until a consumer is proven.", "",
        "## Candidate assets", "",
        f"- BF547: {len(bf547s)}",
        f"- Sharp/Noise map candidates: {len(map_candidates)}",
        f"- LDR candidates: {len(ldr_candidates)}", "",
        "## Best BF561 pair candidates", "",
    ]
    for p in pair_scores[:12]:
        lines.append(
            f"- map `{p['map_path']}` + LDR `{p['ldr_path']}`: "
            f"covered {p['covered']}/{p['checked']}, same_parent={p['same_parent']}"
        )
    lines += ["", "## Next proof", "",
              "Use the BF547 menu-table xrefs and 68/956 breadcrumbs to close the property field and Sharp job builder before any renderer implementation."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({
        "out": str(out), "maps": len(map_candidates), "ldrs": len(ldr_candidates),
        "bf547": len(bf547s), "deep_pairs": len(deep),
    }, indent=2))


if __name__ == "__main__":
    main()
