#!/usr/bin/env python3
"""Bit-exact scalar model of Leica M9 ASMRedBlueInterpolation1.

This models the recovered BF561 routine at pointer-relative array level.
Finite precision follows the recovered Blackfin instructions:
- horizontal two-tap sums saturate signed 16-bit before arithmetic >> 1
- vertical/second-stage sums wrap signed 16-bit before arithmetic >> 1
- final green + interpolated difference wraps signed 16-bit
- final result clamps signed to [0, 16383]

The routine increments the mutable support/border value before processing.
For support_after=s, it writes [s,height-s) x [s,width-s). Plane B uses the
checkerboard lattice whose row/column parity equals s; plane A uses the
complementary lattice. Default support_before=0 preserves the proven 8x8 ABI.
"""
from __future__ import annotations

from typing import Sequence


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def wrap16(v: int) -> int:
    return s16(v)


def sat16(v: int) -> int:
    return -32768 if v < -32768 else 32767 if v > 32767 else v


def asr1(v: int) -> int:
    return int(v) >> 1


def h_avg(a: int, b: int) -> int:
    return asr1(sat16(s16(a) + s16(b)))


def wrap_avg(a: int, b: int) -> int:
    return asr1(wrap16(s16(a) + s16(b)))


def diagonal_avg(a: int, b: int, c: int, d: int) -> int:
    return wrap_avg(h_avg(a, b), h_avg(c, d))


def clamp14_signed(v: int) -> int:
    v = s16(v)
    if v < 0:
        return 0
    if v > 0x3FFF:
        return 0x3FFF
    return v


def final_add(green: int, diff_estimate: int) -> int:
    return clamp14_signed(wrap16(s16(green) + s16(diff_estimate)))


def _estimate(diff: Sequence[int], width: int, y: int, x: int, lattice_parity: int) -> int:
    k = y * width + x
    p = lattice_parity & 1
    if (y & 1) == p and (x & 1) == p:
        return s16(diff[k])
    if (y & 1) == p:
        return h_avg(diff[k - 1], diff[k + 1])
    if (x & 1) == p:
        return wrap_avg(diff[k - width], diff[k + width])
    return diagonal_avg(
        diff[k - width - 1], diff[k - width + 1],
        diff[k + width - 1], diff[k + width + 1],
    )


def render_interp1(
    diff: Sequence[int],
    green: Sequence[int],
    width: int,
    height: int,
    support_before: int = 0,
) -> tuple[list[int], list[int]]:
    """Return pointer-relative output planes A and B.

    `support_before` is the integer supplied through Leica's mutable support
    pointer. The firmware increments it first. This function returns only the
    two planes; callers validating the ABI should expect support_after to be
    support_before + 1.
    """
    n = width * height
    if width < 3 or height < 3:
        raise ValueError("width and height must be at least 3")
    if len(diff) < n or len(green) < n:
        raise ValueError("diff and green must contain at least width*height samples")
    support = int(support_before) + 1
    if support < 1 or 2 * support >= min(width, height):
        raise ValueError("support leaves no valid interpolation interior")

    # First Leica pass (plane B) starts on (support,support); second pass
    # (plane A) starts on the complementary checkerboard phase.
    b_parity = support & 1
    a_parity = (support + 1) & 1

    out_a = [0] * n
    out_b = [0] * n
    for y in range(support, height - support):
        for x in range(support, width - support):
            k = y * width + x
            out_a[k] = final_add(green[k], _estimate(diff, width, y, x, a_parity))
            out_b[k] = final_add(green[k], _estimate(diff, width, y, x, b_parity))
    return out_a, out_b
