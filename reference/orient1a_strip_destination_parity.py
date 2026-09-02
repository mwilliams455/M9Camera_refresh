#!/usr/bin/env python3
import numpy as np


def orient_local(src_strip, rotation):
    rows, width = src_strip.shape
    out = np.empty(src_strip.size, dtype=src_strip.dtype)
    flat = src_strip.reshape(-1)
    if rotation == 0:
        return flat.copy(), width, rows
    if rotation == 90:
        for y in range(rows):
            for x in range(width):
                out[x * rows + (rows - 1 - y)] = src_strip[y, x]
        return out, rows, width
    if rotation == 180:
        for y in range(rows):
            for x in range(width):
                out[(rows - 1 - y) * width + (width - 1 - x)] = src_strip[y, x]
        return out, width, rows
    if rotation == 270:
        for y in range(rows):
            for x in range(width):
                out[(width - 1 - x) * rows + y] = src_strip[y, x]
        return out, rows, width
    return flat.copy(), width, rows


def assemble(src, rotation, strip_rows):
    h, w = src.shape
    if rotation in (90, 270):
        dst = np.empty((w, h), dtype=src.dtype)
    else:
        dst = np.empty((h, w), dtype=src.dtype)
    for y0 in range(0, h, strip_rows):
        block = src[y0:min(y0 + strip_rows, h), :]
        rows = block.shape[0]
        local, rect_w, rect_h = orient_local(block, rotation)
        rect = local.reshape(rect_h, rect_w)
        if rotation == 90:
            x0 = h - (y0 + rows)
            dst[:, x0:x0 + rows] = rect
        elif rotation == 270:
            x0 = y0
            dst[:, x0:x0 + rows] = rect
        elif rotation == 180:
            ydst = h - (y0 + rows)
            dst[ydst:ydst + rows, :] = rect
        else:
            dst[y0:y0 + rows, :] = rect
    return dst


def reference(src, rotation):
    if rotation == 90:
        return np.rot90(src, k=3)
    if rotation == 180:
        return np.rot90(src, k=2)
    if rotation == 270:
        return np.rot90(src, k=1)
    return src.copy()

for h, w, strip in [(5,7,2),(6,8,4),(9,4,3),(3072,16,24)]:
    src = np.arange(h*w, dtype=np.int64).reshape(h,w)
    for rot in (0,90,180,270):
        got=assemble(src,rot,strip)
        ref=reference(src,rot)
        assert np.array_equal(got,ref), (h,w,strip,rot,np.argwhere(got!=ref)[:3])
        print(f'PASS {w}x{h} strip={strip} rot={rot} out={got.shape[1]}x{got.shape[0]}')
print('ORIENT1A strip destination mapping exact parity PASS')
