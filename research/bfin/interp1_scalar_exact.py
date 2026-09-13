#!/usr/bin/env python3
"""Bit-exact scalar model of Leica M9 ASMRedBlueInterpolation1.

This models the recovered BF561 routine at pointer-relative array level.
Inputs:
  diff: signed 16-bit R-G/B-G difference plane, pointer-relative
  green: 16-bit green plane, pointer-relative
  width,height: dimensions supplied to Leica routine
Outputs:
  two 16-bit reconstructed planes A and B, pointer-relative

Finite precision follows the recovered Blackfin instructions:
- horizontal two-tap sums saturate signed 16-bit before arithmetic >> 1
- vertical/second-stage sums wrap signed 16-bit before arithmetic >> 1
- final green + interpolated difference wraps signed 16-bit
- final result clamps signed to [0, 16383]

Only the one-pixel interior is written, matching support=1.
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


def _estimate(diff: Sequence[int], width: int, y: int, x: int, even_lattice: bool) -> int:
    k = y * width + x
    p = 0 if even_lattice else 1
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


def render_interp1(diff: Sequence[int], green: Sequence[int], width: int, height: int) -> tuple[list[int], list[int]]:
    """Return pointer-relative output planes A and B.

    A uses the even/even source lattice. B uses the odd/odd source lattice.
    """
    n = width * height
    if width < 3 or height < 3:
        raise ValueError("width and height must be at least 3")
    if len(diff) < n or len(green) < n:
        raise ValueError("diff and green must contain at least width*height samples")
    out_a = [0] * n
    out_b = [0] * n
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            k = y * width + x
            out_a[k] = final_add(green[k], _estimate(diff, width, y, x, True))
            out_b[k] = final_add(green[k], _estimate(diff, width, y, x, False))
    return out_a, out_b
