#!/usr/bin/env python3
"""Candidate bit-faithful scalar model for Leica M9 ASMRedBlueAndGreenDiffer.

Not promoted/frozen until BFINORACLE2A and direct machine parity pass.
"""

def sat32(v: int) -> int:
    return max(-(1 << 31), min((1 << 31) - 1, int(v)))

def s16(v: int) -> int:
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def u16(v: int) -> int:
    return v & 0xffff

def differ_sample(a_u16: int, b_u16: int, threshold_u16: int, shift: int) -> int:
    """Return the 16-bit stored result.

    Firmware semantics inferred from BF561 instructions:
    d = sat32(zext16(a)-zext16(b))
    correction = zext16(threshold) logically shifted right by shift
    candidate moves d toward zero without crossing zero
    candidate is selected iff abs(d) < abs(zext16(threshold))
    output is low 16 bits written by W[]
    """
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

if __name__ == '__main__':
    cases={
      'equal':(1000,1000,100,2),'positive_keep':(1100,1000,50,2),'positive_shrink':(1100,1000,200,2),'positive_floor':(1100,1000,1000,2),
      'negative_shrink':(1000,1100,200,2),'negative_floor':(1000,1100,1000,2),'strict_threshold':(1100,1000,100,2),
      'shift0':(1100,1000,200,0),'shift1':(1100,1000,200,1),'shift3':(1100,1000,200,3),
      'max14_positive':(16383,0,20000,2),'max14_negative':(0,16383,20000,2),'threshold_zero_positive':(5000,1000,0,4),'threshold_zero_negative':(1000,5000,0,4)
    }
    for n,c in cases.items():
        u=differ_sample(*c); print(n,u,s16(u))
