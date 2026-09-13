#!/usr/bin/env python3
"""Firmware-derived Leica M9 sharpness reference model.

Research-only oracle for the BF561 Sharp stage.  It deliberately does not
import PhotonCamera/Android code and does not mutate the production renderer.

Evidence represented here:
  * 13 ISO-dependent base LUTs, each 2050 signed int16 entries.
  * Manual ISO 160..2500 map monotonically to LUT slots 0..12; pull 80 reuses
    slot 0 while retaining its separate firmware flag.
  * Leica Sharp is a five-position menu whose selector chooses a 13-slot row of
    *internal* modes.  A menu position is therefore not one global multiplier.
  * Internal modes 1..7 are recovered from LoadAndModifySharpnessData:
      1: signed coeff >> 2
      2: signed coeff >> 1
      3: identity
      4: signed coeff << 1
      5: signed coeff << 2
      6: 3 * (signed coeff >> 1)   [important odd-coefficient rounding]
      7: 3 * signed coeff
    Every result is then clamped to [-2048,+2048].
  * 3x3 separable [1 2 1]^T[1 2 1]/16 Gaussian, residual clamp
    [-1024,+1024], centered LUT index 1024+r, and 14-bit output clamp.
  * Sharp contributes two untouched pixels per side beyond the incoming valid
    border; no synthetic mirror/replicate padding is introduced here.

The exact Leica ISO *threshold selection* used during camera operation is not
claimed here.  This oracle accepts proven manual Leica ISO labels directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple


ISO_LABELS = (160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500)
ISO_TO_SLOT = {iso: slot for slot, iso in enumerate(ISO_LABELS)}

# Recovered directly from LUTS/PROCESS/LUTS at firmware mode-table offset 0x5f8.
# Selector enum: Off=0, Low=1, Standard=2, Medium high=3, High=4.
MENU_MODE_ROWS = {
    "off": (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    "low": (3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1),
    "standard": (4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 2, 2),
    "medium_high": (7, 7, 7, 7, 7, 7, 6, 6, 6, 6, 6, 3, 4),
    "high": (5, 5, 5, 5, 5, 5, 4, 4, 4, 4, 4, 4, 5),
}
MENU_SELECTOR = {"off": 0, "low": 1, "standard": 2, "medium_high": 3, "high": 4}

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


def normalize_menu_name(menu: str) -> str:
    key = menu.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in MENU_MODE_ROWS:
        raise ValueError(f"unknown Leica Sharp menu level: {menu!r}")
    return key


def select_iso_slot(iso: int) -> IsoSelection:
    if iso == 80:
        return IsoSelection(80, 0, True)
    try:
        return IsoSelection(iso, ISO_TO_SLOT[iso], False)
    except KeyError as exc:
        raise ValueError(f"unsupported proven M9 manual ISO: {iso}") from exc


def menu_mode(menu: str, slot: int) -> int:
    if not 0 <= slot < LUT_COUNT:
        raise ValueError(f"Sharp ISO slot must be 0..{LUT_COUNT - 1}, got {slot}")
    return int(MENU_MODE_ROWS[normalize_menu_name(menu)][slot])


def transform_coefficient(value: int, mode: int) -> int:
    """Apply exact recovered LoadAndModifySharpnessData integer transform."""
    x = int(value)
    if mode == 1:
        y = x >> 2
    elif mode == 2:
        y = x >> 1
    elif mode == 3:
        y = x
    elif mode == 4:
        y = x << 1
    elif mode == 5:
        y = x << 2
    elif mode == 6:
        # Firmware halves first with signed arithmetic shift, then multiplies
        # by 3.  Do NOT replace with float 1.5*x or (3*x)>>1: odd values differ.
        y = 3 * (x >> 1)
    elif mode == 7:
        y = 3 * x
    else:
        raise ValueError(f"unsupported recovered Sharp internal mode: {mode}")
    return clamp(y, -COEFF_LIMIT, COEFF_LIMIT)


def transform_lut_mode(base: Sequence[int], mode: int) -> List[int]:
    return [transform_coefficient(v, mode) for v in base]


def scale_lut(base: Sequence[int], menu: str, slot: int = 0) -> List[int]:
    """Compatibility wrapper: transform a base LUT for menu+ISO slot.

    Older research code called scale_lut(base, menu) with no slot and assumed a
    global menu multiplier.  That model is superseded.  The default slot=0 is
    retained only so old research callers fail photographically *loudly* rather
    than at import time; new code should always pass the selected slot.
    """
    return transform_lut_mode(base, menu_mode(menu, slot))


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


def gaussian_121_3x3(src: Sequence[Sequence[int]], x: int, y: int) -> int:
    h0 = int(src[y - 1][x - 1]) + 2 * int(src[y - 1][x]) + int(src[y - 1][x + 1])
    h1 = int(src[y][x - 1]) + 2 * int(src[y][x]) + int(src[y][x + 1])
    h2 = int(src[y + 1][x - 1]) + 2 * int(src[y + 1][x]) + int(src[y + 1][x + 1])
    return (h0 + 2 * h1 + h2) // 16


def apply_sharpness(src: Sequence[Sequence[int]], working_lut: Sequence[int], incoming_border: int = 0) -> Tuple[List[List[int]], int]:
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


def apply_m9_sharpness(src: Sequence[Sequence[int]], luts: Sequence[Sequence[int]], iso: int, menu: str = "standard", incoming_border: int = 0) -> Tuple[List[List[int]], int, IsoSelection]:
    sel = select_iso_slot(iso)
    mode = menu_mode(menu, sel.slot)
    work = transform_lut_mode(luts[sel.slot], mode)
    out, border = apply_sharpness(src, work, incoming_border)
    return out, border, sel


def _identity_lut() -> List[int]:
    lut = [0] * LUT_LEN
    for r in range(-RESIDUAL_LIMIT, RESIDUAL_LIMIT + 1):
        lut[LUT_CENTER + r] = r
    return lut


def self_test(bank: Sequence[Sequence[int]] | None = None) -> dict:
    assert [select_iso_slot(x).slot for x in ISO_LABELS] == list(range(13))
    p = select_iso_slot(80)
    assert p.slot == 0 and p.pull80

    expected_rows = {
        "off": (1,1,1,1,1,1,1,1,1,1,1,1,1),
        "low": (3,3,3,3,3,3,2,2,2,2,2,1,1),
        "standard": (4,4,4,4,4,4,3,3,3,3,3,2,2),
        "medium_high": (7,7,7,7,7,7,6,6,6,6,6,3,4),
        "high": (5,5,5,5,5,5,4,4,4,4,4,4,5),
    }
    assert MENU_MODE_ROWS == expected_rows

    # Exact mode arithmetic including the mode-6 odd-number fingerprint.
    assert transform_coefficient(3, 6) == 3
    assert transform_coefficient(-3, 6) == -6
    assert transform_coefficient(5, 6) == 6
    assert transform_coefficient(-5, 6) == -9
    assert transform_coefficient(3, 7) == 9
    assert transform_coefficient(-3, 7) == -9
    assert transform_coefficient(1025, 5) == COEFF_LIMIT
    assert transform_coefficient(-1025, 5) == -COEFF_LIMIT
    for mode in range(1, 8):
        assert -COEFF_LIMIT <= transform_coefficient(32767, mode) <= COEFF_LIMIT
        assert -COEFF_LIMIT <= transform_coefficient(-32768, mode) <= COEFF_LIMIT

    # Representative non-saturated coefficient should preserve menu ordering at
    # low, mid and high ISO despite each menu using an ISO-dependent mode row.
    for slot in (0, 7, 11, 12):
        vals = [transform_coefficient(100, menu_mode(name, slot)) for name in
                ("off", "low", "standard", "medium_high", "high")]
        assert vals == sorted(vals), (slot, vals)

    plane = [[4096] * 11 for _ in range(11)]
    out, border = apply_sharpness(plane, _identity_lut())
    assert border == 2 and out == plane

    impulse = [[0] * 11 for _ in range(11)]
    impulse[5][5] = 4096
    out, border = apply_sharpness(impulse, _identity_lut())
    assert out[5][5] == 5120
    for y in range(11):
        for x in range(11):
            if y < 2 or y >= 9 or x < 2 or x >= 9:
                assert out[y][x] == impulse[y][x]

    result = {
        "schema": "m9.sharpness.reference-selftest.v2",
        "iso_slots": {str(k): v for k, v in ISO_TO_SLOT.items()},
        "pull80": {"slot": 0, "special_flag": True},
        "menu_mode_rows": {k: list(v) for k, v in MENU_MODE_ROWS.items()},
        "mode6_rounding": "3_times_signed_arithmetic_shift_right_1_not_float_1p5",
        "border_increment": SHARP_BORDER_INCREMENT,
        "synthetic_tests": "pass",
    }
    if bank is not None:
        result["bank_sha256"] = validate_bank(bank)
        result["canonical_center_coefficients"] = [int(lut[LUT_CENTER]) for lut in bank]
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
        key = normalize_menu_name(args.menu)
        mode = menu_mode(key, sel.slot)
        print(json.dumps({
            "iso": args.iso,
            "slot": sel.slot,
            "pull80": sel.pull80,
            "menu": key,
            "menu_selector": MENU_SELECTOR[key],
            "internal_mode": mode,
        }, indent=2))
        return 0
    ap.error("use --self-test or --iso")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
