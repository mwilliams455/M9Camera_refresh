#!/usr/bin/env python3
"""Decode canonical M9 BF547 context around five-state table consumers.

This is an evidence-only companion to m9_sharpness_gateb_probe.py.  It does not
modify renderer code and embeds no Leica firmware bytes.  It extracts BF547 from
canonical decrypted M9 1.216, locates the exact Leica Low..High 0..4 menu table,
and emits pointer-resolved controller context around every table xref and around
known control/stage strings such as Contrast, Sharp, Saturation and Noise.

The goal is to determine whether the two direct consumers of the one five-state
table correspond to distinct controls (for example Contrast and Sharpness),
without promoting mere proximity to semantic proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Iterable

EXPECTED_M9_DECRYPTED_SHA256 = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
EXPECTED_M9_BF547_SHA256 = "f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd"
RAM_DELTA = 0x20000
STRIDE = 20
LABELS = (b"Low ", b"Medium low ", b"Standard", b"Medium high ", b"High ")
WORDS = (
    "Contrast", "Sharp", "Sharpness", "Sharpening", "Saturation", "Noise",
    "Standard", "Low ", "Medium low ", "Medium high ", "High ",
    "nContrast", "nSharp", "nSharpness", "nSaturation", "nNoise", "nColorSpace", "nIso",
)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_pwad(data: bytes) -> list[tuple[str, bytes]]:
    if len(data) < 12 or data[:4] != b"PWAD":
        raise ValueError("not PWAD")
    count, directory = struct.unpack_from("<II", data, 4)
    if count > 10000 or directory + 16 * count > len(data):
        raise ValueError("bad PWAD directory")
    out = []
    for i in range(count):
        off, size, raw = struct.unpack_from("<II8s", data, directory + 16 * i)
        if off + size > len(data):
            raise ValueError("PWAD lump outside file")
        name = raw.split(b"\0", 1)[0].decode("ascii", "replace")
        out.append((name, data[off:off + size]))
    return out


def walk(data: bytes, prefix: str = "") -> Iterable[tuple[str, str, bytes]]:
    for name, payload in parse_pwad(data):
        path = f"{prefix}/{name}" if prefix else name
        yield path, name, payload
        if payload[:4] == b"PWAD":
            yield from walk(payload, path)


def extract_bf547(root: bytes) -> bytes:
    hits = [payload for _, name, payload in walk(root) if name.upper() == "BF547"]
    if len(hits) != 1:
        raise RuntimeError(f"expected one BF547, got {len(hits)}")
    return hits[0]


def find_all(data: bytes, needle: bytes) -> list[int]:
    out = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def u32_hits(data: bytes, value: int) -> list[int]:
    return find_all(data, struct.pack("<I", value & 0xFFFFFFFF))


def cstr(data: bytes, off: int, maxlen: int = 128) -> str | None:
    if not 0 <= off < len(data):
        return None
    end = data.find(b"\0", off, min(len(data), off + maxlen))
    if end < 0 or end == off:
        return None
    raw = data[off:end]
    if any(x < 0x20 or x > 0x7e for x in raw):
        return None
    return raw.decode("ascii")


def ptr_string(data: bytes, value: int) -> dict[str, Any] | None:
    if not (RAM_DELTA <= value < RAM_DELTA + len(data)):
        return None
    off = value - RAM_DELTA
    text = cstr(data, off)
    if text is None:
        return None
    return {"file_off": hex(off), "text": text}


def find_table(data: bytes) -> dict[str, Any]:
    tables = []
    for off in range(0, len(data) - 5 * STRIDE + 1, 4):
        rows = []
        for i, label in enumerate(LABELS):
            ptr, value = struct.unpack_from("<II", data, off + i * STRIDE)
            if value != i or ptr < RAM_DELTA:
                break
            text = cstr(data, ptr - RAM_DELTA)
            if text != label.decode("ascii"):
                break
            rows.append((ptr, value, text))
        if len(rows) == 5:
            tables.append((off, rows))
    if len(tables) != 1:
        raise RuntimeError(f"expected one exact Low..High table, got {len(tables)}")
    off, rows = tables[0]
    addr = off + RAM_DELTA
    return {
        "file_off": off,
        "addr": addr,
        "rows": [
            {"record_off": hex(off + i*STRIDE), "label": r[2], "enum": r[1], "ptr": hex(r[0])}
            for i, r in enumerate(rows)
        ],
        "xrefs": u32_hits(data, addr),
    }


def resolved_words(data: bytes, center: int, radius: int = 0x100) -> dict[str, Any]:
    start = max(0, center - radius) & ~3
    end = min(len(data), center + radius)
    rows = []
    for off in range(start, end - 3, 4):
        val = struct.unpack_from("<I", data, off)[0]
        row: dict[str, Any] = {"off": hex(off), "u32": hex(val)}
        s = ptr_string(data, val)
        if s is not None:
            row["points_to_string"] = s
        if 0 <= val < len(data):
            row["possible_file_off"] = hex(val)
        rows.append(row)
    return {"center": hex(center), "start": hex(start), "end": hex(end), "words": rows}


def string_inventory(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for text in WORDS:
        rows = []
        for off in find_all(data, text.encode("ascii")):
            addr = off + RAM_DELTA
            rows.append({
                "off": hex(off), "addr": hex(addr),
                "xrefs": [hex(x) for x in u32_hits(data, addr)],
            })
        result[text] = rows
    return result


def nearby_named_xrefs(inventory: dict[str, Any], center: int, radius: int = 0x200) -> list[dict[str, Any]]:
    out = []
    for name, entries in inventory.items():
        for entry in entries:
            for raw in entry["xrefs"]:
                off = int(raw, 16)
                if abs(off - center) <= radius:
                    out.append({"name": name, "string_off": entry["off"], "xref": raw, "delta": off-center})
    return sorted(out, key=lambda x: (abs(x["delta"]), x["name"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware", type=Path)
    ap.add_argument("--out", type=Path, default=Path("gateb_context.json"))
    args = ap.parse_args()

    root = args.firmware.read_bytes()
    if sha256(root) != EXPECTED_M9_DECRYPTED_SHA256:
        raise SystemExit("canonical decrypted M9 hash mismatch")
    if root[:4] != b"PWAD":
        raise SystemExit("decrypted updater is not PWAD")
    bf = extract_bf547(root)
    if sha256(bf) != EXPECTED_M9_BF547_SHA256:
        raise SystemExit("canonical BF547 hash mismatch")

    table = find_table(bf)
    inv = string_inventory(bf)
    contexts = []
    for xref in table["xrefs"]:
        contexts.append({
            "table_xref": hex(xref),
            "nearby_named_xrefs": nearby_named_xrefs(inv, xref, 0x300),
            "resolved_u32_context": resolved_words(bf, xref, 0x180),
        })

    # Also capture every xref to the primary Sharp string and likely Contrast strings.
    anchor_contexts = []
    for name in ("Sharp", "Sharpness", "Sharpening", "Contrast", "Saturation", "Noise"):
        for entry in inv.get(name, []):
            for raw in entry["xrefs"]:
                off = int(raw, 16)
                anchor_contexts.append({
                    "name": name,
                    "xref": raw,
                    "string_off": entry["off"],
                    "nearby_named_xrefs": nearby_named_xrefs(inv, off, 0x300),
                    "resolved_u32_context": resolved_words(bf, off, 0x100),
                })

    report = {
        "schema": "m9.sharpness.gateb-context.v1",
        "bf547_sha256": sha256(bf),
        "table": {**table, "file_off": hex(table["file_off"]), "addr": hex(table["addr"]), "xrefs": [hex(x) for x in table["xrefs"]]},
        "strings": inv,
        "table_consumer_contexts": contexts,
        "named_anchor_contexts": anchor_contexts,
        "policy": "Context/pointer co-location is evidence; semantic promotion still requires a coherent controller structure or consumer flow.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"table=0x{table['file_off']:x} addr=0x{table['addr']:x} xrefs={[hex(x) for x in table['xrefs']]}")
    for c in contexts:
        print(f"xref {c['table_xref']} nearby={c['nearby_named_xrefs']}")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
