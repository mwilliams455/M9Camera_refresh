#!/usr/bin/env python3
"""Prove M9 Sharp LUT archive geometry from the canonical decrypted firmware.

Evidence-only. No firmware bytes are embedded or retained.  LoadLutDataL3 is
already disassembled and proves:

  archive + 0x5f0 -> process + 0x66c, length 0x10c
  therefore process Sharp count +0x670 <- archive u32[0x5f4]

and:

  process Sharp source +0x664 <- archive_base + archive u32[0x10]

This probe follows those exact offsets into PROCESS/LUTS and reports only
metadata/hashes, never the Leica payload itself.
"""
from __future__ import annotations

import argparse, hashlib, json, struct
from pathlib import Path
from typing import Iterable

FW_SHA = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
EXPECTED_LUTS_SIZE = 427744
EXPECTED_BANK_OFF = 0xACF8
EXPECTED_COUNT = 2050
ISO_ROWS = 13


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_pwad(data: bytes):
    if data[:4] != b"PWAD":
        raise ValueError("not PWAD")
    n, directory = struct.unpack_from("<II", data, 4)
    out = []
    for i in range(n):
        off, size, raw = struct.unpack_from("<II8s", data, directory + 16*i)
        if off + size > len(data):
            raise ValueError("bad PWAD entry")
        name = raw.split(b"\0", 1)[0].decode("ascii", "replace")
        out.append((name, data[off:off+size]))
    return out


def walk(data: bytes, prefix="") -> Iterable[tuple[str, str, bytes]]:
    for name, payload in parse_pwad(data):
        path = f"{prefix}/{name}" if prefix else name
        yield path, name, payload
        if payload[:4] == b"PWAD":
            yield from walk(payload, path)


def u32(b: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(b):
        raise ValueError(hex(off))
    return struct.unpack_from("<I", b, off)[0]


def candidate_report(path: str, payload: bytes) -> dict:
    bank_off = u32(payload, 0x10) if len(payload) >= 0x14 else None
    count = u32(payload, 0x5F4) if len(payload) >= 0x5F8 else None
    row_bytes = 2 * count if count is not None else None
    total_bytes = ISO_ROWS * row_bytes if row_bytes is not None else None
    bank_end = bank_off + total_bytes if bank_off is not None and total_bytes is not None else None
    rows = []
    if bank_off is not None and row_bytes and bank_end <= len(payload):
        for i in range(ISO_ROWS):
            lo = bank_off + i*row_bytes
            hi = lo + row_bytes
            rows.append({"iso_slot": i, "offset": hex(lo), "size": row_bytes, "sha256": sha(payload[lo:hi])})
    return {
        "path": path,
        "size": len(payload),
        "sha256": sha(payload),
        "header_u32_0x00": u32(payload, 0) if len(payload) >= 4 else None,
        "sharp_source_bank_offset_from_header_0x10": hex(bank_off) if bank_off is not None else None,
        "sharp_lut_count_from_archive_0x5f4": count,
        "sharp_row_bytes": row_bytes,
        "iso_rows": ISO_ROWS,
        "sharp_bank_total_bytes": total_bytes,
        "sharp_bank_end": hex(bank_end) if bank_end is not None else None,
        "bank_range_fits_payload": bool(bank_end is not None and bank_end <= len(payload)),
        "matches_historical_bank_offset_0xacf8": bank_off == EXPECTED_BANK_OFF,
        "matches_count_2050": count == EXPECTED_COUNT,
        "matches_13x4100_geometry": row_bytes == 4100 and total_bytes == 53300,
        "row_hashes": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware", type=Path)
    ap.add_argument("--out", type=Path, default=Path("m9_sharpness_luts_resource_probe.json"))
    a = ap.parse_args()
    root = a.firmware.read_bytes()
    if sha(root) != FW_SHA:
        raise SystemExit("canonical decrypted firmware hash mismatch")

    entries = list(walk(root))
    candidates = []
    for path, name, payload in entries:
        # Keep the path-based candidate and the exact historic size as independent
        # discovery criteria. This avoids silently assuming either one is correct.
        if name.upper() == "LUTS" or path.upper().endswith("/PROCESS/LUTS") or len(payload) == EXPECTED_LUTS_SIZE:
            if len(payload) >= 0x5F8:
                candidates.append(candidate_report(path, payload))

    report = {
        "schema": "m9.sharpness.luts-resource-probe.v1",
        "firmware_sha256": sha(root),
        "loadlutdata_l3_proven_mapping": {
            "metadata_copy": "archive+0x5f0 -> process+0x66c length 0x10c",
            "sharp_count_mapping": "process+0x670 <- archive u32[0x5f4]",
            "sharp_source_mapping": "process+0x664 <- archive_base + archive u32[0x10]",
        },
        "candidates": candidates,
        "proof_rule": (
            "A candidate closes the historical 13x4100 Sharp-bank identity only if "
            "the same canonical LUTS payload gives header[0x10]=0xACF8 and "
            "u32[0x5F4]=2050, yielding 13*4100=53300 bytes at that source pointer."
        ),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "out": str(a.out),
        "candidate_count": len(candidates),
        "summary": [
            {k: c[k] for k in (
                "path", "size", "header_u32_0x00",
                "sharp_source_bank_offset_from_header_0x10",
                "sharp_lut_count_from_archive_0x5f4",
                "matches_historical_bank_offset_0xacf8",
                "matches_count_2050", "matches_13x4100_geometry")}
            for c in candidates
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
