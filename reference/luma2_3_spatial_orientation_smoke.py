#!/usr/bin/env python3
"""Synthetic check for the Java display-orientation coordinate mapping."""
W,H=96,72
src=[y*W+x for y in range(H) for x in range(W)]

def orient(rotation):
    if rotation==0:
        return src[:],W,H
    if rotation==180:
        out=[None]*(W*H)
        for y in range(H):
            for x in range(W):
                out[(H-1-y)*W+(W-1-x)]=src[y*W+x]
        return out,W,H
    dw,dh=H,W
    out=[None]*(dw*dh)
    if rotation==90:
        for y in range(H):
            for x in range(W):
                dx=H-1-y; dy=x
                out[dy*dw+dx]=src[y*W+x]
    else:
        for y in range(H):
            for x in range(W):
                dx=y; dy=W-1-x
                out[dy*dw+dx]=src[y*W+x]
    return out,dw,dh

# Corner identities for clockwise-positive display rotation, matching renderer Matrix.postRotate.
o,w,h=orient(90)
assert (w,h)==(72,96)
assert o[0*w+(w-1)] == src[0]                  # sensor TL -> display TR
assert o[(h-1)*w+(w-1)] == src[W-1]            # sensor TR -> display BR
assert o[0] == src[(H-1)*W]                    # sensor BL -> display TL
assert o[(h-1)*w] == src[(H-1)*W+(W-1)]        # sensor BR -> display BL

o,w,h=orient(270)
assert o[(h-1)*w] == src[0]                    # sensor TL -> display BL
assert o[0] == src[W-1]                        # sensor TR -> display TL
print('LUMA2.3 spatial orientation synthetic mapping: PASS')
