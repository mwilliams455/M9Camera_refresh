#!/usr/bin/env python3
"""Firmware-derived Leica M9 sharpness reference model.

Research-only model for the BF561 Sharp stage recovered from Leica M9 firmware.
It deliberately does not depend on PhotonCamera or Android code.

Evidence-backed behavior represented here:
  * 13 ISO-dependent base LUTs, each 2050 signed int16 entries.
  * ISO 160..2500 map monotonically to LUT slots 0..12.
  * Pull 80 reuses slot 0 (its separate firmware special flag is reported but
    is not applied here because no Sharp-kernel arithmetic consumer has been
    proven for that flag).
  * Menu modes: Off=1/4, Low=1/2, Standard=1x, Medium high=2x, High=4x,
    coefficient clamp [-2048,+2048].
  * 3x3 separable [1 2 1]^T[1 2 1]/16 Gaussian with truncation.
  * residual clamp [-1024,+1024], centered LUT index 1024+r.
  * 14-bit output clamp [0,16383].
  * Sharp contributes two untouched pixels per side beyond the incoming valid
    border; no synthetic mirror/replicate padding is introduced here.

This file is intentionally a reference/oracle, not production renderer code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


ISO_TO_SLOT = {
    160: 0,
    200: 1,
    250: 2,
    320: 3,
    400: 4,
    500: 5,
    640: 6,
    800: 7,
    1000: 8,
    1250: 9,
    1600: 10,
    2000: 11,
    2500: 12,
}

MENU_TO_MODE = {
    "off": 1,
    "low": 2,
    "standard": 3,
    "medium_high": 4,
    "medium high": 4,
    "high": 5,
}

EXPECTED_BANK_SHA256 = "a9c60000a8ec60ce922f8715436aa45223988f16c5b00fbfc417e546cdf7a8eb"
LUT_COUNT = 13
LUT_LEN = 2050
LUT_CENTER = 1024
RESIDUAL_LIMIT = 1024
COEFF_LIMIT = 2048
PIXEL_MAX = 16383
SHARP_BORDER_INCREMENT = 2


@dataclass(frozen=True)
class IsoSelection:
    requested_iso: int
    slot: int
    pull80: bool = False


def clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


def select_iso_slot(iso: int) -> IsoSelection:
    if iso == 80:
        # Firmware nIso enum 1 is decoded to slot 0 and sets a separate flag.
        return IsoSelection(80, 0, True)
    try:
        return IsoSelection(iso, ISO_TO_SLOT[iso], False)
    except KeyError as exc:
        raise ValueError(f"unsupported proven M9 manual ISO: {iso}") from exc


def bank_raw_bytes(luts: Sequence[Sequence[int]]) -> bytes:
    return b"".join(struct.pack("<h", int(v)) for lut in luts for v in lut)


def validate_bank(luts: Sequence[Sequence[int]], expected_sha256: str | None = EXPECTED_BANK_SHA256) -> str:
    if len(luts) != LUT_COUNT:
        raise ValueError(f"expected {LUT_COUNT} LUTs, got {len(luts)}")
    for i, lut in enumerate(luts):
        if len(lut) != LUT_LEN:
            raise ValueError(f"LUT {i}: expected {LUT_LEN} entries, got {len(lut)}")
        if any(int(v) < -32768 or int(v) > 32767 for v in lut):
            raise ValueError(f"LUT {i}: value outside int16 range")
    digest = hashlib.sha256(bank_raw_bytes(luts)).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f"Sharp LUT bank SHA256 mismatch: {digest} != {expected_sha256}")
    return digest


def load_bank_json(path: str | Path, verify_sha: bool = True) -> List[List[int]]:
    obj = json.loads(Path(path).read_text())
    luts = obj.get("luts")
    if not isinstance(luts, list):
        raise ValueError("JSON does not contain a 'luts' array")
    expected = EXPECTED_BANK_SHA256 if verify_sha else None
    validate_bank(luts, expected)
    return [[int(v) for v in lut] for lut in luts]


def scale_lut(base: Sequence[int], menu: str) -> List[int]:
    key = menu.strip().lower().replace("-", "_")
    if key == "medium_high":
        mode = 4
    else:
        mode = MENU_TO_MODE.get(key)
    if mode is None:
        raise ValueError(f"unknown Sharp menu level: {menu!r}")

    out: List[int] = []
    for x0 in base:
        x = int(x0)
        if mode == 1:
            # Blackfin arithmetic right shift; Python >> has matching signed semantics.
            y = x >> 2
        elif mode == 2:
            y = x >> 1
        elif mode == 3:
            y = x
        elif mode == 4:
            y = x << 1
        elif mode == 5:
            y = x << 2
        else:  # unreachable for five-state M9 UI
            raise AssertionError(mode)
        out.append(clamp(y, -COEFF_LIMIT, COEFF_LIMIT))
    return out


def gaussian_121_3x3(src: Sequence[Sequence[int]], x: int, y: int) -> int:
    # Equivalent to the recovered separable horizontal/vertical implementation.
    h0 = int(src[y - 1][x - 1]) + 2 * int(src[y - 1][x]) + int(src[y - 1][x + 1])
    h1 = int(src[y][x - 1]) + 2 * int(src[y][x]) + int(src[y][x + 1])
    h2 = int(src[y + 1][x - 1]) + 2 * int(src[y + 1][x]) + int(src[y + 1][x + 1])
    return (h0 + 2 * h1 + h2) // 16


def apply_sharpness(
    src: Sequence[Sequence[int]],
    working_lut: Sequence[int],
    incoming_border: int = 0,
) -> Tuple[List[List[int]], int]:
    if len(working_lut) != LUT_LEN:
        raise ValueError(f"working LUT must contain {LUT_LEN} entries")
    if incoming_border < 0:
        raise ValueError("incoming_border must be >= 0")
    h = len(src)
    w = len(src[0]) if h else 0
    if any(len(row) != w for row in src):
        raise ValueError("source rows are not rectangular")
    if any(int(v) < 0 or int(v) > PIXEL_MAX for row in src for v in row):
        raise ValueError("source must be unsigned 14-bit [0,16383]")

    out = [[int(v) for v in row] for row in src]
    border = incoming_border + SHARP_BORDER_INCREMENT
    if h <= 2 * border or w <= 2 * border:
        return out, border

    for y in range(border, h - border):
        for x in range(border, w - border):
            g = gaussian_121_3x3(src, x, y)
            residual = clamp(int(src[y][x]) - g, -RESIDUAL_LIMIT, RESIDUAL_LIMIT)
            corr = int(working_lut[LUT_CENTER + residual])
            out[y][x] = clamp(int(src[y][x]) + corr, 0, PIXEL_MAX)
    return out, border


def apply_m9_sharpness(
    src: Sequence[Sequence[int]],
    luts: Sequence[Sequence[int]],
    iso: int,
    menu: str = "standard",
    incoming_border: int = 0,
) -> Tuple[List[List[int]], int, IsoSelection]:
    sel = select_iso_slot(iso)
    work = scale_lut(luts[sel.slot], menu)
    out, border = apply_sharpness(src, work, incoming_border)
    return out, border, sel


def _identity_lut() -> List[int]:
    # Synthetic helper: correction == residual. Entry 2049 is unused guard.
    lut = [0] * LUT_LEN
    for r in range(-RESIDUAL_LIMIT, RESIDUAL_LIMIT + 1):
        lut[LUT_CENTER + r] = r
    return lut


def self_test(bank: Sequence[Sequence[int]] | None = None) -> dict:
    assert [select_iso_slot(x).slot for x in ISO_TO_SLOT] == list(range(13))
    p = select_iso_slot(80)
    assert p.slot == 0 and p.pull80

    # Menu transforms, including signed arithmetic shift and saturation.
    sample = [-2048, -1025, -5, -1, 0, 1, 5, 1025, 2048]
    assert scale_lut(sample + [0] * (LUT_LEN - len(sample)), "off")[:9] == [-512, -257, -2, -1, 0, 0, 1, 256, 512]
    assert scale_lut(sample + [0] * (LUT_LEN - len(sample)), "low")[:9] == [-1024, -513, -3, -1, 0, 0, 2, 512, 1024]
    assert scale_lut(sample + [0] * (LUT_LEN - len(sample)), "high")[:9] == [-2048, -2048, -20, -4, 0, 4, 20, 2048, 2048]

    # Constant field: Gaussian equals source; identity correction at r=0 is zero.
    plane = [[4096] * 11 for _ in range(11)]
    out, border = apply_sharpness(plane, _identity_lut())
    assert border == 2 and out == plane

    # Border is copied through exactly; interior can change.
    impulse = [[0] * 11 for _ in range(11)]
    impulse[5][5] = 4096
    out, border = apply_sharpness(impulse, _identity_lut())
    assert out[5][5] == 5120  # G=1024, residual clamps to +1024, +1024 correction.
    for y in range(11):
        for x in range(11):
            if y < 2 or y >= 9 or x < 2 or x >= 9:
                assert out[y][x] == impulse[y][x]

    result = {
        "schema": "m9.sharpness.reference-selftest.v1",
        "iso_slots": {str(k): v for k, v in ISO_TO_SLOT.items()},
        "pull80": {"slot": 0, "special_flag": True},
        "border_increment": SHARP_BORDER_INCREMENT,
        "synthetic_tests": "pass",
    }
    if bank is not None:
        result["bank_sha256"] = validate_bank(bank)
        # Canonical Standard must be byte-for-byte identity relative to base LUT.
        for i, lut in enumerate(bank):
            if scale_lut(lut, "standard") != list(lut):
                raise AssertionError(f"Standard altered base LUT {i}")
        # A flat input should remain flat for every ISO at residual zero if the
        # recovered canonical LUT center coefficient is zero.
        center = [int(lut[LUT_CENTER]) for lut in bank]
        result["canonical_center_coefficients"] = center
        result["canonical_standard_identity"] = True
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut-json", help="sharp_base_lut_bank.json evidence file")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--iso", type=int)
    ap.add_argument("--menu", default="standard")
    args = ap.parse_args()

    bank = load_bank_json(args.lut_json) if args.lut_json else None
    if args.self_test:
        print(json.dumps(self_test(bank), indent=2, sort_keys=True))
        return 0
    if args.iso is not None:
        sel = select_iso_slot(args.iso)
        print(json.dumps({"iso": args.iso, "slot": sel.slot, "pull80": sel.pull80, "menu": args.menu}, indent=2))
        return 0
    ap.error("use --self-test or --iso")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
