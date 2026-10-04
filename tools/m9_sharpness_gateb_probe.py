#!/usr/bin/env python3
"""Strict Gate-B probe for Leica M9 1.216 Sharpness menu encoding.

This tool does not embed Leica firmware bytes and does not modify renderer code.
It accepts either the canonical extracted BF547 binary or the decrypted updater,
extracts BF547 when needed, verifies provenance, then scans the real Leica
20-byte menu-record format used by the M-generation controller firmware.

Important policy:
- A five-state Low..High table is NOT automatically Sharpness.
- Standard=2 is NOT promoted for M9 Sharpness merely because homologous Leica
  controls use 0..4 and Standard=2.
- +13=nSharpness remains a hypothesis until an M9-specific property/consumer
  xref closes the semantic identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Iterable

EXPECTED_M9_BF547_SHA256 = "f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd"
EXPECTED_M9_DECRYPTED_SHA256 = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
BF547_RAM_DELTA = 0x20000
MENU_RECORD_STRIDE = 20
MENU_LABELS = (b"Low ", b"Medium low ", b"Standard", b"Medium high ", b"High ")
PROPERTY_WORDS = (
    "Sharp", "nSharp", "nSharpness", "Noise", "nNoise",
    "nContrast", "nSaturation", "nColorSpace", "nIso",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pwad(data: bytes) -> list[tuple[str, bytes]]:
    if len(data) < 12 or data[:4] != b"PWAD":
        raise ValueError("not PWAD")
    count, directory = struct.unpack_from("<II", data, 4)
    if count > 10000 or directory + count * 16 > len(data):
        raise ValueError("invalid PWAD directory")
    out: list[tuple[str, bytes]] = []
    for i in range(count):
        off, size, raw_name = struct.unpack_from("<II8s", data, directory + i * 16)
        if off + size > len(data):
            raise ValueError("PWAD lump exceeds payload")
        name = raw_name.split(b"\0", 1)[0].decode("ascii", "replace")
        out.append((name, data[off:off + size]))
    return out


def find_root_pwad(raw: bytes) -> bytes:
    if raw[:4] == b"PWAD":
        return raw
    for off in range(min(len(raw), 0x1000)):
        if raw[off:off + 4] != b"PWAD":
            continue
        try:
            parse_pwad(raw[off:])
        except Exception:
            continue
        return raw[off:]
    raise ValueError("no valid PWAD root in first 0x1000 bytes")


def walk_pwad(data: bytes, prefix: str = "") -> Iterable[tuple[str, str, bytes]]:
    for name, payload in parse_pwad(data):
        path = f"{prefix}/{name}" if prefix else name
        yield path, name, payload
        if payload[:4] == b"PWAD":
            yield from walk_pwad(payload, path)


def extract_bf547_from_firmware(raw: bytes) -> tuple[str, bytes]:
    root = find_root_pwad(raw)
    hits = [(path, payload) for path, name, payload in walk_pwad(root) if name.upper() == "BF547"]
    if not hits:
        raise ValueError("no BF547 lump found")
    # M9 updater has one controller BF547 payload. Refuse ambiguity rather than guess.
    if len(hits) != 1:
        raise ValueError(f"expected one BF547 lump, found {len(hits)}: {[x[0] for x in hits]}")
    return hits[0]


def cstr(data: bytes, off: int) -> bytes | None:
    if not 0 <= off < len(data):
        return None
    end = data.find(b"\0", off, min(len(data), off + 96))
    if end < 0:
        return None
    raw = data[off:end]
    if not raw or any(x < 0x20 or x > 0x7E for x in raw):
        return None
    return raw


def find_all(data: bytes, needle: bytes) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return out
        out.append(pos)
        start = pos + 1


def u32_xrefs(data: bytes, value: int) -> list[int]:
    return find_all(data, struct.pack("<I", value & 0xFFFFFFFF))


def menu_record(data: bytes, off: int) -> tuple[bytes, int] | None:
    if off < 0 or off + 8 > len(data):
        return None
    ptr, value = struct.unpack_from("<II", data, off)
    if ptr < BF547_RAM_DELTA:
        return None
    label = cstr(data, ptr - BF547_RAM_DELTA)
    if label is None:
        return None
    return label, value


def scan_five_state_tables(data: bytes) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Real tables are word-aligned and records are 20 bytes.
    for off in range(0, len(data) - 5 * MENU_RECORD_STRIDE + 1, 4):
        rows = []
        ok = True
        for i, expected_label in enumerate(MENU_LABELS):
            rec = menu_record(data, off + i * MENU_RECORD_STRIDE)
            if rec is None:
                ok = False
                break
            label, value = rec
            if label != expected_label or value != i:
                ok = False
                break
            ptr = struct.unpack_from("<I", data, off + i * MENU_RECORD_STRIDE)[0]
            rows.append({
                "record_off": hex(off + i * MENU_RECORD_STRIDE),
                "label": label.decode("ascii"),
                "enum": value,
                "string_ptr": hex(ptr),
                "string_file_off": hex(ptr - BF547_RAM_DELTA),
            })
        if not ok:
            continue
        table_addr = off + BF547_RAM_DELTA
        out.append({
            "table_off": hex(off),
            "table_addr": hex(table_addr),
            "rows": rows,
            "table_addr_xrefs": [hex(x) for x in u32_xrefs(data, table_addr)],
            "semantic_status": "UNASSIGNED",
        })
    return out


def scan_property_xrefs(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for text in PROPERTY_WORDS:
        rows = []
        for off in find_all(data, text.encode("ascii")):
            addr = off + BF547_RAM_DELTA
            rows.append({
                "string_off": hex(off),
                "string_addr": hex(addr),
                "pointer_xrefs": [hex(x) for x in u32_xrefs(data, addr)],
            })
        result[text] = rows
    return result


def nearest_semantic_clues(tables: list[dict[str, Any]], props: dict[str, Any]) -> list[dict[str, Any]]:
    prop_sites: list[tuple[str, int]] = []
    for name in ("Sharp", "nSharp", "nSharpness"):
        for row in props.get(name, []):
            for x in row["pointer_xrefs"]:
                prop_sites.append((name, int(x, 16)))

    out = []
    for table in tables:
        table_sites = [int(x, 16) for x in table["table_addr_xrefs"]]
        nearest = None
        for prop_name, p in prop_sites:
            for t in table_sites:
                d = abs(p - t)
                if nearest is None or d < nearest["distance"]:
                    nearest = {"property": prop_name, "property_xref": hex(p), "table_xref": hex(t), "distance": d}
        out.append({
            "table_off": table["table_off"],
            "nearest_sharp_related_xref": nearest,
            "interpretation": "proximity clue only; does not close Gate B",
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--bf547", type=Path, help="extracted M9 BF547.bin")
    g.add_argument("--firmware", type=Path, help="decrypted M9 1.216 updater/container")
    ap.add_argument("--allow-noncanonical", action="store_true",
                    help="scan even if canonical M9 SHA256 does not match")
    ap.add_argument("--out", type=Path, default=Path("SHARPNESSFORENSICS1A_GATEB"))
    args = ap.parse_args()

    firmware_meta: dict[str, Any] | None = None
    if args.firmware:
        raw = args.firmware.read_bytes()
        fw_hash = sha256(raw)
        firmware_meta = {"path": str(args.firmware), "sha256": fw_hash}
        if fw_hash != EXPECTED_M9_DECRYPTED_SHA256 and not args.allow_noncanonical:
            raise SystemExit(
                "decrypted updater SHA256 mismatch; refusing semantic scan. "
                f"got {fw_hash}, expected {EXPECTED_M9_DECRYPTED_SHA256}"
            )
        bf547_path, data = extract_bf547_from_firmware(raw)
        source = f"{args.firmware}:{bf547_path}"
    else:
        data = args.bf547.read_bytes()
        source = str(args.bf547)

    bf_hash = sha256(data)
    canonical = bf_hash == EXPECTED_M9_BF547_SHA256
    if not canonical and not args.allow_noncanonical:
        raise SystemExit(
            "BF547 SHA256 mismatch; refusing semantic scan. "
            f"got {bf_hash}, expected {EXPECTED_M9_BF547_SHA256}"
        )

    tables = scan_five_state_tables(data)
    props = scan_property_xrefs(data)
    clues = nearest_semantic_clues(tables, props)

    report = {
        "schema": "m9.sharpnessforensics1a.gateb.v1",
        "source": source,
        "firmware": firmware_meta,
        "bf547": {
            "sha256": bf_hash,
            "canonical_m9_1_216": canonical,
            "expected_sha256": EXPECTED_M9_BF547_SHA256,
            "ram_delta": hex(BF547_RAM_DELTA),
        },
        "proven_structure": {
            "menu_record_stride": MENU_RECORD_STRIDE,
            "menu_record_shape": "u32 string_pointer, u32 enum, 12 further bytes",
            "five_state_sequence": [0, 1, 2, 3, 4],
            "labels": [x.decode("ascii") for x in MENU_LABELS],
        },
        "five_state_candidates": tables,
        "property_strings": props,
        "sharp_table_proximity_clues": clues,
        "gate_b": {
            "status": "OPEN",
            "strongly_bounded": [
                "+13 is the leading nSharpness candidate from homologous record layout",
                "M-generation five-state controls encode Low..High as 0..4 with Standard=2",
            ],
            "not_yet_proven_for_m9_sharpness": [
                "+13 = nSharpness",
                "Sharpness Standard = 2",
                "identity of any five-state candidate as Sharpness",
            ],
            "closure_requirement": (
                "M9-specific semantic xref connecting the Sharpness property/record field "
                "to a five-state table or selector, then tie that state into the Sharp process record"
            ),
        },
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "gateb_report.json").write_text(json.dumps(report, indent=2))

    print(f"BF547 canonical={canonical} sha256={bf_hash}")
    print(f"five-state candidates={len(tables)}")
    for t in tables:
        print(f"  {t['table_off']} xrefs={len(t['table_addr_xrefs'])}: 0=Low 1=Medium-low 2=Standard 3=Medium-high 4=High")
    print("Gate B: OPEN — M9 Sharpness semantic xref still required")
    print(f"report: {args.out / 'gateb_report.json'}")


if __name__ == "__main__":
    main()
