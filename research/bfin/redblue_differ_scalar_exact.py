#!/usr/bin/env python3
"""Bit-faithful scalar model for Leica M9 ASMRedBlueAndGreenDiffer.

The per-sample arithmetic is closed by BFINORACLE2A/BFINSCALAR2B.
The geometry helper models the routine's physical software-pipelined writes,
including the row-boundary scratch overlap and preserved companion halfword.
"""

def sat32(v: int) -> int:
    return max(-(1 << 31), min((1 << 31) - 1, int(v)))

def s16(v: int) -> int:
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def u16(v: int) -> int:
    return v & 0xffff

def raw_difference(a_u16: int, b_u16: int) -> int:
    """Low 16 bits of the routine's saturated 32-bit R0-R1 result."""
    return u16(sat32(u16(a_u16) - u16(b_u16)))

def differ_sample(a_u16: int, b_u16: int, threshold_u16: int, shift: int) -> int:
    """Return the corrected 16-bit row-end result."""
    a = u16(a_u16)
    b = u16(b_u16)
    t = u16(threshold_u16)
    d = sat32(a - b)
    corr = t >> int(shift)
    if d >= 0:
        cand = max(sat32(d - corr), 0)
    else:
        cand = min(d + corr, 0)
    if abs(d) < abs(t):
        d = cand
    return u16(d)

def differ_geometry_memory(a, b, threshold, inner: int, outer: int, stride: int,
                           shift: int, word_count: int, low_sentinel: int = 0x1357,
                           high_sentinel: int = 0x5a5a):
    """Model physical output memory after the firmware routine.

    Each logical sample occupies the low halfword of a 32-bit cell. The high
    halfword is preserved. The loop's multifunction packet stores raw
    differences into the software-pipeline positions; the explicit row-end
    store writes the corrected last sample.

    First row:
      - inner==1: output[0] = corrected sample 0
      - inner>1: output[0..inner-2] = raw samples 1..inner-1
                 output[inner-1] = corrected last sample
    Subsequent row r:
      - raw samples 0..inner-1 are written at r*stride-1 .. r*stride+inner-2
      - corrected last sample is written at r*stride+inner-1

    This intentionally models physical side effects, not a conventional dense
    image abstraction.
    """
    if inner < 1 or outer < 1 or stride < inner:
        raise ValueError('require inner>=1, outer>=1, stride>=inner')
    need = (outer - 1) * stride + inner
    if len(a) < need or len(b) < need or len(threshold) < need:
        raise ValueError('input arrays too short')
    lows = [u16(low_sentinel)] * word_count
    highs = [u16(high_sentinel)] * word_count

    # First row: the first pipeline store lands in the pre-buffer guard.
    if inner == 1:
        lows[0] = differ_sample(a[0], b[0], threshold[0], shift)
    else:
        for c in range(1, inner):
            lows[c - 1] = raw_difference(a[c], b[c])
        last = inner - 1
        lows[inner - 1] = differ_sample(a[last], b[last], threshold[last], shift)

    # Later rows expose the first pipeline store at one cell before row start.
    for r in range(1, outer):
        src = r * stride
        dst = r * stride - 1
        for c in range(inner):
            if dst + c < word_count:
                lows[dst + c] = raw_difference(a[src + c], b[src + c])
        end = r * stride + inner - 1
        if end < word_count:
            last = src + inner - 1
            lows[end] = differ_sample(a[last], b[last], threshold[last], shift)
    return lows, highs

if __name__ == '__main__':
    cases={
      'equal':(1000,1000,100,2),'positive_keep':(1100,1000,50,2),'positive_shrink':(1100,1000,200,2),'positive_floor':(1100,1000,1000,2),
      'negative_shrink':(1000,1100,200,2),'negative_floor':(1000,1100,1000,2),'strict_threshold':(1100,1000,100,2),
      'shift0':(1100,1000,200,0),'shift1':(1100,1000,200,1),'shift3':(1100,1000,200,3),
      'max14_positive':(16383,0,20000,2),'max14_negative':(0,16383,20000,2),'threshold_zero_positive':(5000,1000,0,4),'threshold_zero_negative':(1000,5000,0,4)
    }
    for n,c in cases.items():
        u=differ_sample(*c); print(n,u,s16(u))
