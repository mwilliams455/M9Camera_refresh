#!/usr/bin/env python3
"""Exact scalar composition of Leica M9 GreenInterpolationWithCo helper calls.

This models the production 0xFEB10660 orchestration using helper contracts that
were independently closed by BFINORACLE/BFINSCALAR and GREENORACLE6E.  The
orchestrator pointer arithmetic is translated directly from the frozen 810-byte
Blackfin body; no Android renderer code is involved.

Memory is represented as 16-bit-addressable little-endian halfwords keyed by
absolute byte address.  The Differ helper writes only the low halfword of each
32-bit output cell, preserving its companion halfword exactly as firmware does.
"""


def u16(v):
    return int(v) & 0xffff


def s16(v):
    v = u16(v)
    return v - 0x10000 if v & 0x8000 else v


def round_even_up(v):
    v = int(v)
    return v + (v & 1)


class Memory16:
    def __init__(self):
        self.h = {}

    def load_region(self, base, values):
        for i, v in enumerate(values):
            self.h[int(base) + 2 * i] = u16(v)

    def read(self, addr):
        addr = int(addr)
        if addr & 1:
            raise ValueError(f'unaligned u16 read 0x{addr:x}')
        if addr not in self.h:
            raise ValueError(f'unmapped u16 read 0x{addr:x}')
        return self.h[addr]

    def write(self, addr, value):
        addr = int(addr)
        if addr & 1:
            raise ValueError(f'unaligned u16 write 0x{addr:x}')
        if addr not in self.h:
            raise ValueError(f'unmapped u16 write 0x{addr:x}')
        self.h[addr] = u16(value)

    def region(self, base, count):
        return [self.read(int(base) + 2 * i) for i in range(int(count))]


def filter010(mem, src, dst, inner, outer, stride, selector):
    """ASMFilter_010_101_010_2: cardinal four-neighbour reconstruction."""
    if inner <= 0 or inner & 1 or outer <= 0 or stride <= inner:
        raise ValueError(('filter010 geometry', inner, outer, stride))
    # Writes occupy the missing-sample lattice.  Reads are taken immediately
    # from memory so in-place production calls retain firmware alias semantics.
    for r in range(outer):
        for c in range(inner):
            center = src + 4*c + 4*stride*r
            total = (mem.read(center - 2) + mem.read(center + 2) +
                     mem.read(center - 2*stride) + mem.read(center + 2*stride))
            value = (total >> 2) if selector == 2 else u16(total)
            if selector not in (0, 2):
                raise ValueError(selector)
            mem.write(dst + 4*c + 4*stride*r, value)


def abs16_v(v):
    x = s16(v)
    return 0x7fff if x == -0x8000 else abs(x)


def filter101040(mem, src, out1, out2, inner, outer, stride):
    """ASMFilter_101_040_101_An exact logical writes plus phase scratch."""
    if inner <= 0 or inner & 1 or outer <= 0 or stride <= 0 or stride & 1:
        raise ValueError(('filter101040 geometry', inner, outer, stride))
    # BFINORACLE3D proved one extra phase-1 pipeline write at out2-4.  Across
    # the oracle bank that scratch value is zero; retain that physical write so
    # complete destination buffers can be compared, not only logical samples.
    if src & 0x2:
        mem.write(out2 - 4, 0)
    for r in range(outer):
        for c in range(inner):
            center = src + 4*c + 4*stride*r
            cv = mem.read(center)
            nw = mem.read(center - 2*stride - 2)
            ne = mem.read(center - 2*stride + 2)
            sw = mem.read(center + 2*stride - 2)
            se = mem.read(center + 2*stride + 2)
            filtered = u16((4*cv + nw + ne + sw + se) >> 3)
            residual = abs16_v(u16(filtered - cv))
            mem.write(out1 + 4*c + 4*stride*r, filtered)
            mem.write(out2 + 4*c + 4*stride*r, residual)


def differ_sample(a, b, threshold, shift):
    a = u16(a); b = u16(b); threshold = u16(threshold)
    d = a - b
    corr = threshold >> int(shift)
    cand = max(d - corr, 0) if d >= 0 else min(d + corr, 0)
    if abs(d) < abs(threshold):
        d = cand
    return u16(d)


def differ_raw(a, b):
    return u16(u16(a) - u16(b))


def redblue_differ(mem, a, b, threshold, out, inner, outer, stride, shift):
    """ASMRedBlueAndGreenDiffer including software-pipeline physical writes."""
    if inner < 1 or outer < 1 or stride < inner:
        raise ValueError(('differ geometry', inner, outer, stride))

    def av(base, r, c):
        return mem.read(base + 4*(r*stride + c))

    # First row: the routine's first pipeline store is before the public output
    # pointer.  For inner>1 the visible raw stream starts from logical sample 1.
    if inner == 1:
        mem.write(out, differ_sample(av(a,0,0), av(b,0,0), av(threshold,0,0), shift))
    else:
        for c in range(1, inner):
            mem.write(out + 4*(c-1), differ_raw(av(a,0,c), av(b,0,c)))
        c = inner - 1
        mem.write(out + 4*c, differ_sample(av(a,0,c), av(b,0,c), av(threshold,0,c), shift))

    for r in range(1, outer):
        for c in range(inner):
            mem.write(out + 4*(r*stride - 1 + c), differ_raw(av(a,r,c), av(b,r,c)))
        c = inner - 1
        mem.write(out + 4*(r*stride + c),
                  differ_sample(av(a,r,c), av(b,r,c), av(threshold,r,c), shift))


def filter101000(mem, src, dst, inner, outer, stride):
    """ASMFilter_101_000_101_2 signed four-diagonal quarter average."""
    if inner <= 0 or inner & 1 or outer <= 0 or stride <= inner:
        raise ValueError(('filter101000 geometry', inner, outer, stride))
    for r in range(outer):
        for c in range(inner):
            center = src + 4*c + 4*stride*r
            total = (s16(mem.read(center - 2*stride - 2)) +
                     s16(mem.read(center - 2*stride + 2)) +
                     s16(mem.read(center + 2*stride - 2)) +
                     s16(mem.read(center + 2*stride + 2)))
            mem.write(dst + 4*c + 4*stride*r, u16(total >> 2))


def green_composite(mem, a, b, c, d, stride, height, shift, phase_initial):
    """Compose the ten helper calls made by production GreenInterpolationWithCo.

    Arguments correspond to the live Green ABI after LINK:
      R0=a, R1=b, R2=c,
      FP+0x14=d, FP+0x18=stride, FP+0x1c=height,
      FP+0x20=shift, FP+0x24=&phase.
    The caller's sixth home-space word maps to FP+0x28 but is overwritten by
    Green before any read and therefore is intentionally absent here.
    """
    trace = []
    half_h = int(height) >> 1

    p1 = int(phase_initial) + 1
    outer0 = half_h - p1
    inner0 = round_even_up((int(stride) >> 1) - p1)
    off1 = 2 * p1 * (stride + 1)

    calls = [
        ('filter010', a+off1, b+off1, inner0, outer0, stride, 2),
        ('filter010', a+off1+2*stride+2, b+off1+2*stride+2, inner0, outer0, stride, 2),
    ]
    for row in calls:
        trace.append(row); filter010(mem, *row[1:])

    row = ('filter101040', a+off1+2, b+off1+2, c+off1+2, inner0, outer0, stride)
    trace.append(row); filter101040(mem, *row[1:])
    row = ('filter101040', a+off1+2*stride, b+off1+2*stride, c+off1+2*stride, inner0, outer0, stride)
    trace.append(row); filter101040(mem, *row[1:])

    p2 = p1 + 1
    outer1 = half_h - p2
    inner1 = round_even_up((int(stride) >> 1) - p2)
    off2 = 2 * p2 * (stride + 1)
    row = ('filter010', c+off2, c+off2, inner1, outer1, stride, 0)
    trace.append(row); filter010(mem, *row[1:])
    row = ('filter010', c+off2+2*stride+2, c+off2+2*stride+2, inner1, outer1, stride, 0)
    trace.append(row); filter010(mem, *row[1:])

    row = ('differ', a+off2, b+off2, c+off2, d+off2, inner1, outer1, stride, shift)
    trace.append(row); redblue_differ(mem, *row[1:])
    # The second production Difference call uses a deliberately different A
    # phase than B/C/D; this asymmetry is taken directly from 0xFEB108DE..F2.
    a2 = a + 2*stride*p2 + 2*stride + 2
    bc2 = off2 + 2*stride + 2
    row = ('differ', a2, b+bc2, c+bc2, d+bc2, inner1, outer1, stride, shift)
    trace.append(row); redblue_differ(mem, *row[1:])

    p3 = p2 + 1
    outer2 = half_h - p3
    inner2 = round_even_up((int(stride) >> 1) - p3)
    off3 = 2 * p3 * (stride + 1)
    row = ('filter101000', d+off3, a+off3, inner2, outer2, stride)
    trace.append(row); filter101000(mem, *row[1:])
    row = ('filter101000', d+off3+2*stride+2, a+off3+2*stride+2, inner2, outer2, stride)
    trace.append(row); filter101000(mem, *row[1:])

    return {
        'phase_final': p3,
        'inner_outer': [[inner0, outer0], [inner1, outer1], [inner2, outer2]],
        'trace': trace,
    }
