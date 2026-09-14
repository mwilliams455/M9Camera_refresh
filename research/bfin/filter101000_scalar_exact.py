#!/usr/bin/env python3
"""Bit-faithful scalar model for Leica M9 ASMFilter_101_000_101_2.

BFINORACLE4B closed the geometry and BFINORACLE4C closed the arithmetic:
for each reconstructed Bayer-phase sample, Leica averages the four diagonal
signed-16 taps using an arithmetic right shift by two.
"""


def u16(v: int) -> int:
    return int(v) & 0xffff


def s16(v: int) -> int:
    v = u16(v)
    return v - 0x10000 if v & 0x8000 else v


def filter_sample(nw: int, ne: int, sw: int, se: int) -> int:
    """Return exact stored u16 result for one logical reconstructed sample."""
    total = s16(nw) + s16(ne) + s16(sw) + s16(se)
    return u16(total >> 2)


def logical_positions(base_halfword: int, inner: int, outer: int, stride: int):
    """Yield (center_source_halfword, destination_halfword_index).

    The routine reconstructs one Bayer phase.  Centers advance by two
    halfwords horizontally and by 2*stride between outer rows.  Relative to
    the harness destination base, the first meaningful output is halfword 2.
    """
    if inner <= 0 or inner & 1:
        raise ValueError('inner must be positive and even')
    if outer <= 0:
        raise ValueError('outer must be positive')
    if stride <= inner:
        raise ValueError('stride must be greater than inner')
    for r in range(outer):
        row = base_halfword + r * 2 * stride
        out_row = r * 2 * stride
        for c in range(inner):
            yield row + 2 * c, 2 + out_row + 2 * c


def scalar_output(source, base_halfword: int, inner: int, outer: int, stride: int,
                  word_count: int = 128, sentinel: int = 0x1357):
    out = [u16(sentinel)] * word_count
    for center, oi in logical_positions(base_halfword, inner, outer, stride):
        out[oi] = filter_sample(
            source[center - stride - 1],
            source[center - stride + 1],
            source[center + stride - 1],
            source[center + stride + 1],
        )
    return out


if __name__ == '__main__':
    tests = [
        (1, 0, 0, 0),
        (3, 0, 0, 0),
        (-1, 0, 0, 0),
        (-3, 0, 0, 0),
        (32767, -32768, 32767, -32768),
    ]
    for taps in tests:
        y = filter_sample(*taps)
        print(taps, hex(y), s16(y))
