#!/usr/bin/env python3
"""Verify the two M9 GreenInterpolationWithCo copies are identical modulo CALL relocation."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_CALL_OFFSETS = (0x78, 0xBE, 0x10A, 0x156, 0x1AC, 0x1E4, 0x236, 0x292, 0x2E2, 0x31A)
EXPECTED_SIZE = 810


def parse_disassembly(path: Path, base: int, size: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    rx = re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)(.*)$")
    for line in path.read_text(errors="replace").splitlines():
        m = rx.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        off = addr - base
        if not 0 <= off < size:
            continue
        out[off] = {
            "bytes": bytes.fromhex(m.group(2)),
            "text": m.group(3).strip(),
            "addr": addr,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("active", type=Path)
    ap.add_argument("linked", type=Path)
    ap.add_argument("--active-base", type=lambda x: int(x, 0), default=0xFEB10660)
    ap.add_argument("--linked-base", type=lambda x: int(x, 0), default=0xFF613558)
    ap.add_argument("--size", type=lambda x: int(x, 0), default=EXPECTED_SIZE)
    args = ap.parse_args()

    active = parse_disassembly(args.active, args.active_base, args.size)
    linked = parse_disassembly(args.linked, args.linked_base, args.size)
    if set(active) != set(linked):
        raise SystemExit(
            f"instruction-offset mismatch active={len(active)} linked={len(linked)} "
            f"delta={sorted(set(active) ^ set(linked))[:16]}"
        )

    mismatches = []
    for off in sorted(active):
        if active[off]["bytes"] == linked[off]["bytes"]:
            continue
        mismatches.append({
            "off": off,
            "active_text": active[off]["text"],
            "linked_text": linked[off]["text"],
            "active_bytes": active[off]["bytes"].hex(),
            "linked_bytes": linked[off]["bytes"].hex(),
        })

    offsets = tuple(x["off"] for x in mismatches)
    if offsets != EXPECTED_CALL_OFFSETS:
        raise SystemExit(f"unexpected mismatch offsets: {[hex(x) for x in offsets]}")
    if not all(x["active_text"].startswith("CALL ") and x["linked_text"].startswith("CALL ") for x in mismatches):
        raise SystemExit("non-CALL instruction differs between copies")

    result = {
        "status": "PASS",
        "schema": "m9.rb.green-overlay-parity.v1",
        "function_bytes": args.size,
        "decoded_instructions": len(active),
        "mismatch_count": len(mismatches),
        "mismatch_offsets": [hex(x) for x in offsets],
        "all_mismatches_are_calls": True,
        "non_call_bytes_identical": True,
        "call_pairs": mismatches,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
