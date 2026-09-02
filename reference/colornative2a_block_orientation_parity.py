#!/usr/bin/env python3
import numpy as np


def orient_block(src, rotation):
    rows, width = src.shape
    if rotation == 0:
        return src.copy()
    if rotation == 90:
        out = np.empty((width, rows), dtype=src.dtype)
        for y in range(rows):
            dest_x = rows - 1 - y
            for x in range(width):
                out[x, dest_x] = src[y, x]
        return out
    if rotation == 180:
        return src[::-1, ::-1].copy()
    if rotation == 270:
        out = np.empty((width, rows), dtype=src.dtype)
        for y in range(rows):
            for x in range(width):
                out[width - 1 - x, y] = src[y, x]
        return out
    return src.copy()


def block_pipeline(src, rotation, block_rows=384):
    h, w = src.shape
    if rotation in (90,270):
        dst = np.empty((w,h), dtype=src.dtype)
    else:
        dst = np.empty((h,w), dtype=src.dtype)
    for y0 in range(0,h,block_rows):
        rows=min(block_rows,h-y0)
        block=orient_block(src[y0:y0+rows],rotation)
        if rotation==90:
            dest_x=h-(y0+rows)
            dst[:, dest_x:dest_x+rows]=block
        elif rotation==270:
            dst[:, y0:y0+rows]=block
        elif rotation==180:
            dest_y=h-(y0+rows)
            dst[dest_y:dest_y+rows,:]=block
        else:
            dst[y0:y0+rows,:]=block
    return dst


def reference(src,rotation):
    if rotation==0: return src.copy()
    if rotation==90: return np.rot90(src, k=3)
    if rotation==180: return np.rot90(src, k=2)
    if rotation==270: return np.rot90(src, k=1)

for h,w in [(3072,4096),(1031,1373),(17,19)]:
    src=np.arange(h*w,dtype=np.int64).reshape(h,w)
    for rot in (0,90,180,270):
        got=block_pipeline(src,rot)
        want=reference(src,rot)
        assert np.array_equal(got,want),(h,w,rot)
print('COLORNATIVE2A 0/90/180/270 block orientation parity PASS')
