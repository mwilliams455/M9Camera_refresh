#!/usr/bin/env python3
"""Extract the Leica M9 Sharp menu x ISO selector-mode matrix from canonical 1.216 LUTS.

Research-only: emits derived integers/hashes, never firmware bytes.  This resolves
an ambiguity left by the older single-multiplier reference model: selector 2
(Standard) is already proven to vary with ISO, so all five user menu selectors
must be read as 13-slot rows from the same firmware table.
"""
from __future__ import annotations

import argparse, hashlib, json, struct
from pathlib import Path

FW_SHA = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
EXPECTED_SIZE = 427744
BANK_OFF = 0xACF8
COUNT = 2050
ROWS = 13
MODE_OFF = 0x5F8
MENU = ["Off", "Low", "Standard", "Medium high", "High"]
ISO = [160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500]
STANDARD_EXPECT = [4,4,4,4,4,4,3,3,3,3,3,2,2]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pwad(data: bytes):
    if data[:4] != b"PWAD":
        raise ValueError("not PWAD")
    n, directory = struct.unpack_from("<II", data, 4)
    for i in range(n):
        off, size, raw = struct.unpack_from("<II8s", data, directory + 16*i)
        name = raw.split(b"\0",1)[0].decode("ascii","replace")
        yield name, data[off:off+size]


def walk(data: bytes, prefix=""):
    for name, payload in pwad(data):
        path = f"{prefix}/{name}" if prefix else name
        yield path, name, payload
        if payload[:4] == b"PWAD":
            yield from walk(payload, path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fw = a.firmware.read_bytes()
    if sha(fw) != FW_SHA:
        raise SystemExit("canonical decrypted firmware hash mismatch")

    candidates = []
    for path, name, p in walk(fw):
        if len(p) == EXPECTED_SIZE or name.upper() == "LUTS" or path.upper().endswith("/PROCESS/LUTS"):
            if (len(p) >= BANK_OFF + ROWS*COUNT*2 and
                struct.unpack_from("<I", p, 0x10)[0] == BANK_OFF and
                struct.unpack_from("<I", p, 0x5F4)[0] == COUNT):
                candidates.append((path,p))
    if len(candidates) != 1:
        raise SystemExit(f"expected one canonical LUTS candidate, got {len(candidates)}")
    resource_path, p = candidates[0]

    matrix = []
    for selector, name in enumerate(MENU):
        off = MODE_OFF + selector*ROWS*4
        row = [struct.unpack_from("<I", p, off + 4*i)[0] for i in range(ROWS)]
        matrix.append(row)
    if matrix[2] != STANDARD_EXPECT:
        raise SystemExit(f"Standard selector row mismatch: {matrix[2]}")

    base_hashes = []
    for slot in range(ROWS):
        lo = BANK_OFF + slot*COUNT*2
        base_hashes.append(sha(p[lo:lo+COUNT*2]))

    values = sorted({v for row in matrix for v in row})
    report = {
        "schema": "m9.sharpness-menu-iso-rows.v1",
        "firmware_sha256": FW_SHA,
        "resource_path": resource_path,
        "mode_table_offset": hex(MODE_OFF),
        "row_layout": "five user Sharp selectors, each 13 little-endian u32 mode values",
        "menu_enum": {name:i for i,name in enumerate(MENU)},
        "iso_labels": ISO,
        "mode_rows": {MENU[i]: matrix[i] for i in range(len(MENU))},
        "mode_values_observed": values,
        "standard_crosscheck": matrix[2] == STANDARD_EXPECT,
        "base_bank": {
            "offset": hex(BANK_OFF),
            "rows": ROWS,
            "count_per_row": COUNT,
            "slot_sha256": base_hashes,
        },
        "interpretation_guard": (
            "Rows are firmware selector-mode values, not Android generic sharpness strengths. "
            "Do not collapse a menu position to one multiplier when its 13-slot row varies."
        ),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"resource":resource_path,"mode_rows":report["mode_rows"],"observed":values}, indent=2))


if __name__ == "__main__":
    main()
