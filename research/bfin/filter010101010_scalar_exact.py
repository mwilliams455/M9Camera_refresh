#!/usr/bin/env python3
"""Bit-faithful scalar model for Leica M9 ASMFilter_010_101_010_2.

GREENORACLE6D established that the routine reconstructs one Bayer-phase
lattice from the four cardinal neighbours of each missing sample.  Leica uses
two production selector values:

  selector 2: floor((L + R + U + D) / 4) over u16 taps
  selector 0: low-16 wrap of (L + R + U + D)

The two source-address/stride packing phases are implementation details of the
Blackfin packed loads; they produce the same logical kernel.
"""


def u16(v: int) -> int:
    return int(v) & 0xffff


def filter_sample(left: int, right: int, up: int, down: int, selector: int) -> int:
    """Return the exact stored u16 result for one logical reconstructed sample."""
    total = u16(left) + u16(right) + u16(up) + u16(down)
    if selector == 2:
        return total >> 2
    if selector == 0:
        return u16(total)
    raise ValueError('validated Leica production selectors are 0 and 2')


def logical_positions(base_halfword: int, inner: int, outer: int, stride: int,
                      destination_base_halfword: int = 0):
    """Yield (source_center_halfword, destination_halfword_index).

    Centers advance by two halfwords horizontally and by 2*stride between
    outer rows.  Destination samples follow the identical Bayer-phase lattice.
    """
    if inner <= 0 or inner & 1:
        raise ValueError('inner must be positive and even')
    if outer <= 0:
        raise ValueError('outer must be positive')
    if stride <= inner:
        raise ValueError('stride must be greater than inner')
    for r in range(outer):
        source_row = base_halfword + r * 2 * stride
        destination_row = destination_base_halfword + r * 2 * stride
        for c in range(inner):
            yield source_row + 2 * c, destination_row + 2 * c


def scalar_output(source, base_halfword: int, inner: int, outer: int, stride: int,
                  selector: int, destination_base_halfword: int = 0,
                  halfword_count: int = 256, sentinel: int = 0x5a5a):
    """Return the complete destination buffer, including untouched sentinels."""
    out = [u16(sentinel)] * halfword_count
    for center, oi in logical_positions(
            base_halfword, inner, outer, stride, destination_base_halfword):
        if not 0 <= oi < halfword_count:
            raise ValueError(f'destination index out of range: {oi}')
        out[oi] = filter_sample(
            source[center - 1],
            source[center + 1],
            source[center - stride],
            source[center + stride],
            selector,
        )
    return out


if __name__ == '__main__':
    edge_sets = [
        (1, 1, 1, 1),
        (0xffff, 0xffff, 0xffff, 0xffff),
        (0x8000, 0x7fff, 0xffff, 1),
    ]
    for taps in edge_sets:
        print(taps, 'selector2=', hex(filter_sample(*taps, 2)),
              'selector0=', hex(filter_sample(*taps, 0)))
