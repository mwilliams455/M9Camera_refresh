#!/usr/bin/env python3
"""Generate deterministic regression vectors for the recovered M9 Sharp stage.

Research-only. Produces 13 manual ISO x 5 menu cases plus Pull 80 equivalence
checks from the canonical firmware-derived 2050-entry LUT bank.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import m9_sharpness_reference as ref


ISOS = [160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500]
MENUS = ["off", "low", "standard", "medium_high", "high"]


def u16_bytes(img):
    return b"".join(struct.pack("<H", int(v)) for row in img for v in row)


def i16_bytes(vals):
    return b"".join(struct.pack("<h", int(v)) for v in vals)


def fixture(width=37, height=31):
    """Deterministic 14-bit field exercising flat, edge and clipped residual cases."""
    out = []
    for y in range(height):
        row = []
        for x in range(width):
            v = (137 * x + 251 * y + 19 * x * y + 4096) & 0x3FFF
            # Introduce repeated flats and hard local transitions.
            if 6 <= x <= 11 and 5 <= y <= 10:
                v = 4096
            if 20 <= x <= 24 and 12 <= y <= 18:
                v = 14000 if ((x + y) & 1) else 300
            if x == width // 2 and y == height // 2:
                v = 16383
            if x == width // 2 + 1 and y == height // 2:
                v = 0
            row.append(v)
        out.append(row)
    return out


def generate(bank):
    ref.validate_bank(bank)
    src = fixture()
    cases = []
    for iso in ISOS:
        sel = ref.select_iso_slot(iso)
        for menu in MENUS:
            work = ref.scale_lut(bank[sel.slot], menu)
            out, border, _ = ref.apply_m9_sharpness(src, bank, iso, menu, incoming_border=0)
            cases.append({
                "iso": iso,
                "slot": sel.slot,
                "menu": menu,
                "working_lut_sha256": hashlib.sha256(i16_bytes(work)).hexdigest(),
                "output_u16le_sha256": hashlib.sha256(u16_bytes(out)).hexdigest(),
                "border": border,
                "output_min": min(min(r) for r in out),
                "output_max": max(max(r) for r in out),
            })

    pull = []
    for menu in MENUS:
        a, ba, sa = ref.apply_m9_sharpness(src, bank, 80, menu, incoming_border=0)
        b, bb, sb = ref.apply_m9_sharpness(src, bank, 160, menu, incoming_border=0)
        ah = hashlib.sha256(u16_bytes(a)).hexdigest()
        bh = hashlib.sha256(u16_bytes(b)).hexdigest()
        pull.append({
            "menu": menu,
            "pull80_slot": sa.slot,
            "iso160_slot": sb.slot,
            "output_sha256_pull80": ah,
            "output_sha256_iso160": bh,
            "sharp_output_equal": a == b and ah == bh,
            "border_equal": ba == bb,
        })
        if not pull[-1]["sharp_output_equal"]:
            raise AssertionError(f"Pull80 Sharp differs from ISO160 for {menu}")

    return {
        "schema": "m9.sharpness.reference-vectors.v1",
        "canonical_bank_sha256": ref.EXPECTED_BANK_SHA256,
        "fixture": {
            "width": len(src[0]),
            "height": len(src),
            "source_u16le_sha256": hashlib.sha256(u16_bytes(src)).hexdigest(),
        },
        "algorithm": {
            "lut_len": ref.LUT_LEN,
            "lut_center": ref.LUT_CENTER,
            "residual_limit": ref.RESIDUAL_LIMIT,
            "coefficient_limit": ref.COEFF_LIMIT,
            "pixel_max": ref.PIXEL_MAX,
            "border_increment": ref.SHARP_BORDER_INCREMENT,
            "gaussian": "[1 2 1; 2 4 2; 1 2 1] / 16, truncating",
        },
        "cases": cases,
        "pull80_sharp_equivalence": pull,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut-json", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    bank = ref.load_bank_json(args.lut_json)
    obj = generate(bank)
    Path(args.out).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "case_count": len(obj["cases"]),
        "pull80_equivalence_cases": len(obj["pull80_sharp_equivalence"]),
        "all_pull80_equal": all(x["sharp_output_equal"] for x in obj["pull80_sharp_equivalence"]),
        "fixture_sha256": obj["fixture"]["source_u16le_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
