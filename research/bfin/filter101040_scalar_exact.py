#!/usr/bin/env python3
"""Bit-faithful scalar arithmetic for Leica M9 ASMFilter_101_040_101_An.

The filter MACs use Blackfin unsigned-fractional (FU) operands and TFU
truncating half-register extraction.  Therefore source halfwords are treated
as u16 values even when their bit patterns would be negative as s16.
"""

def u16(v: int) -> int:
    return int(v) & 0xffff


def s16(v: int) -> int:
    v = u16(v)
    return v - 0x10000 if v & 0x8000 else v


def abs16_v(v: int) -> int:
    """Blackfin packed ABS(V): signed16 absolute with -32768 -> +32767."""
    x = s16(v)
    if x == -0x8000:
        return 0x7fff
    return abs(x)


def filter_sample(center: int, nw: int, ne: int, sw: int, se: int) -> tuple[int, int]:
    """Return (filtered_u16, residual_u16) for one logical sample.

    FU products are 0.16 x 0.16 with no sign correction.  The exact coefficient
    encoding is 0x8000 for center (1/2) and 0x2000 for each diagonal (1/8).
    TFU truncates the accumulator lower 16 bits on extraction, which reduces to
    floor((4*C + NW + NE + SW + SE) / 8) over u16 samples.

    The residual path then performs packed 16-bit wrap subtraction followed by
    vector absolute value with saturation of -32768 to +32767.
    """
    c, a, b, d, e = map(u16, (center, nw, ne, sw, se))
    filtered = (4 * c + a + b + d + e) >> 3
    # weighted average cannot exceed 0xffff, but retain explicit u16 storage.
    filtered = u16(filtered)
    residual = abs16_v(u16(filtered - c))
    return filtered, residual


def logical_positions(base_halfword: int, inner: int, outer: int, stride: int):
    """Yield (source_center, out1_halfword, out2_halfword) for meaningful samples.

    The routine processes one Bayer phase: horizontal centers advance by 2
    halfwords and successive outer rows advance by 2*stride halfwords.
    """
    if inner <= 0 or inner & 1:
        raise ValueError('inner must be positive and even')
    if stride <= 0 or stride & 1:
        raise ValueError('stride must be positive and even')
    for r in range(outer):
        row = base_halfword + r * 2 * stride
        out_row = r * 2 * stride
        for c in range(inner):
            yield row + 2 * c, 1 + out_row + 2 * c, 2 + out_row + 2 * c


def scalar_outputs(source, base_halfword: int, inner: int, outer: int, stride: int,
                   word_count: int = 128, out1_sentinel: int = 0x1357,
                   out2_sentinel: int = 0x2468):
    out1 = [u16(out1_sentinel)] * word_count
    out2 = [u16(out2_sentinel)] * word_count
    for center, oi1, oi2 in logical_positions(base_halfword, inner, outer, stride):
        f, r = filter_sample(
            source[center],
            source[center - stride - 1],
            source[center - stride + 1],
            source[center + stride - 1],
            source[center + stride + 1],
        )
        if oi1 < word_count:
            out1[oi1] = f
        if oi2 < word_count:
            out2[oi2] = r
    return out1, out2


if __name__ == '__main__':
    for amp in (1, 2, 7, 8, 1000, 16383, 0xffff):
        f, r = filter_sample(amp, 0, 0, 0, 0)
        print(amp, f, r)
