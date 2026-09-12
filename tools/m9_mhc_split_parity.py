#!/usr/bin/env python3
"""Prove a two-pass green->R/B decomposition is pixel-identical to frozen MHCNEUTRAL1A.

This is a research gate only. It reproduces the exact arithmetic/order used by
mhcPixelNeutralRggb in apply-m9cam-basishsm1p-demosaicmhcneutral1a.py and
compares it with an explicit green-plane first pass followed by R/B completion.
No Leica Sharpness arithmetic is applied here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
from pathlib import Path


def clamp(v: int, hi: int) -> int:
    return 0 if v < 0 else (hi - 1 if v >= hi else v)


def nd(v: float) -> int:
    if not math.isfinite(v) or v <= 0.0:
        return 0
    if v >= 65535.0:
        return 65535
    # C++ std::llround: halfway cases away from zero. All surviving values are >0.
    return int(math.floor(v + 0.5))


def n_at(raw, w, h, y, x, inv_r, inv_b):
    y = clamp(y, h); x = clamp(x, w)
    k = inv_r if ((y & 1) == 0 and (x & 1) == 0) else (inv_b if ((y & 1) and (x & 1)) else 1.0)
    return float(raw[y * w + x]) * k


def terms(raw, w, h, y, x, nr, nb):
    ir, ib = 1.0 / nr, 1.0 / nb
    C = n_at(raw,w,h,y,x,ir,ib); N = n_at(raw,w,h,y-1,x,ir,ib); S = n_at(raw,w,h,y+1,x,ir,ib)
    W = n_at(raw,w,h,y,x-1,ir,ib); E = n_at(raw,w,h,y,x+1,ir,ib)
    NN = n_at(raw,w,h,y-2,x,ir,ib); SS = n_at(raw,w,h,y+2,x,ir,ib)
    WW = n_at(raw,w,h,y,x-2,ir,ib); EE = n_at(raw,w,h,y,x+2,ir,ib)
    NW = n_at(raw,w,h,y-1,x-1,ir,ib); NE = n_at(raw,w,h,y-1,x+1,ir,ib)
    SW = n_at(raw,w,h,y+1,x-1,ir,ib); SE = n_at(raw,w,h,y+1,x+1,ir,ib)
    g = (4*C + 2*(N+S+W+E) - (NN+SS+WW+EE)) / 8.0
    o = (12*C + 4*(NW+NE+SW+SE) - 3*(NN+SS+WW+EE)) / 16.0
    hh = (10*C + 8*(W+E) + (NN+SS) - 2*(NW+NE+SW+SE) - 2*(WW+EE)) / 16.0
    vv = (10*C + 8*(N+S) + (WW+EE) - 2*(NW+NE+SW+SE) - 2*(NN+SS)) / 16.0
    return g,o,hh,vv


def monolithic_pixel(raw,w,h,y,x,nr,nb):
    g,o,hh,vv = terms(raw,w,h,y,x,nr,nb)
    ey, ex = (y & 1) == 0, (x & 1) == 0
    sm = raw[y*w+x]
    if ey and ex: return sm, nd(g), nd(o*nb)
    if (not ey) and (not ex): return nd(o*nr), nd(g), sm
    if ey: return nd(hh*nr), sm, nd(vv*nb)
    return nd(vv*nr), sm, nd(hh*nb)


def green_pixel(raw,w,h,y,x,nr,nb):
    ey, ex = (y & 1) == 0, (x & 1) == 0
    if ey != ex:
        return raw[y*w+x]
    g,_,_,_ = terms(raw,w,h,y,x,nr,nb)
    return nd(g)


def rb_complete_pixel(raw,w,h,y,x,nr,nb,g):
    _,o,hh,vv = terms(raw,w,h,y,x,nr,nb)
    ey, ex = (y & 1) == 0, (x & 1) == 0
    sm = raw[y*w+x]
    if ey and ex: return sm, g, nd(o*nb)
    if (not ey) and (not ex): return nd(o*nr), g, sm
    if ey: return nd(hh*nr), g, nd(vv*nb)
    return nd(vv*nr), g, nd(hh*nb)


def u16_hash(values):
    h=hashlib.sha256()
    for v in values: h.update(struct.pack('<H',v))
    return h.hexdigest()


def make_fixtures():
    w,h=37,31
    rng=random.Random(0x4D394D48)
    random16=[rng.randrange(65536) for _ in range(w*h)]
    ramp=[((x*65535)//(w-1) + (y*257)) & 0xffff for y in range(h) for x in range(w)]
    checker=[65535 if ((x//2+y//2)&1) else 0 for y in range(h) for x in range(w)]
    impulse=[0]*(w*h); impulse[(h//2)*w+w//2]=65535
    edge=[]
    for y in range(h):
        for x in range(w): edge.append(65535 if x >= w//2 else (16383 if y >= h//2 else 0))
    return w,h,{'random16':random16,'ramp':ramp,'checker2':checker,'impulse':impulse,'edge':edge}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    w,h,fixtures=make_fixtures()
    neutrals=[(1.0,1.0),(0.70,1.30),(1.80,0.60),(0.253,0.914)]
    cases=[]
    for fname,raw in fixtures.items():
        for nr,nb in neutrals:
            mono=[]; green=[]; split=[]
            for y in range(h):
                for x in range(w):
                    mono.extend(monolithic_pixel(raw,w,h,y,x,nr,nb))
                    green.append(green_pixel(raw,w,h,y,x,nr,nb))
            for y in range(h):
                for x in range(w):
                    split.extend(rb_complete_pixel(raw,w,h,y,x,nr,nb,green[y*w+x]))
            if mono != split:
                for i,(a,b) in enumerate(zip(mono,split)):
                    if a != b:
                        pix=i//3; ch=i%3
                        raise SystemExit(f'parity failure {fname} nr={nr} nb={nb} pixel=({pix//w},{pix%w}) ch={ch} mono={a} split={b}')
                raise SystemExit('parity failure length mismatch')
            cases.append({'fixture':fname,'neutralRoverG':nr,'neutralBoverG':nb,
                          'mono_rgb_sha256':u16_hash(mono),'split_rgb_sha256':u16_hash(split),
                          'green_plane_sha256':u16_hash(green),'pixels':w*h})
    report={'schema':'m9.mhc-split-parity.v1','width':w,'height':h,'cases':cases,
            'case_count':len(cases),'all_pixel_exact':True,
            'decomposition':'frozen MHCNEUTRAL1A -> green plane first -> R/B completion',
            'sharpness_applied':False,
            'note':'This closes structural split parity only; Leica Sharp 14-bit domain scaling remains a separate gate.'}
    text=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.out: args.out.write_text(text)
    print(text,end='')

if __name__=='__main__': main()
