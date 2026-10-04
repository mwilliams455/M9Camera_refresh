#!/usr/bin/env python3
"""Offline SHARPSOURCE1A discriminator for M9 mobile sharpness port.

Purpose:
  Keep the validated neutral-MHC RGB foundation frozen, but derive the Sharp
  correction from a Leica-like green signal reconstructed from the recovered
  BF561 GreenInterpolationWithCo filter weights.

This is NOT claimed bit-for-bit Leica GreenInterpolationWithCo parity yet.
The recovered arithmetic/weights and interior CFA phase mapping are firmware-derived;
packed border/tile traversal still needs final parity closure.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import tifffile

RAW_BLACK = 64
RAW_WHITE = 1023
RAW_RANGE = RAW_WHITE - RAW_BLACK

# Compact exact ISO160 / Standard x2 coefficients used by CLOSURETEST1B.
EXC = {997:-26,998:-25,999:-24,1000:-23,1001:-21,1002:-20,1003:-19,1004:-17,
1005:-16,1006:-15,1007:-13,1008:-12,1009:-11,1010:-10,1011:-9,1012:-8,
1013:-7,1014:-6,1015:-5,1016:-4,1017:-3,1018:-2,1019:-2,1020:-1,1021:-1,
1022:0,1023:0,1025:0,1026:0,1027:1,1028:1,1029:2,1030:2,1031:3,1032:4,
1033:5,1034:6,1035:7,1036:8,1037:9,1038:10,1039:11,1040:12,1041:13,
1042:15,1043:16,1044:17,1045:19,1046:20,1047:21,1048:23,1049:24,1050:25,
1051:26}

def shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    p = np.pad(a, ((2,2),(2,2)), mode='edge')
    h,w = a.shape
    return p[2+dy:2+dy+h, 2+dx:2+dx+w]

def nd(v):
    return np.clip(np.floor(v + 0.5), 0, 65535).astype(np.int32)

def q14(v):
    return ((v.astype(np.int64) * 16383 + 32767) // 65535).astype(np.int32)

def clamp14(v):
    return np.clip(v, 0, 16383).astype(np.int32)

def coeff(idx):
    out = idx - 1024
    for k,v in EXC.items():
        out = np.where(idx == k, v, out)
    return np.clip(out * 2, -2048, 2048)

def sharp14(g):
    gp = np.pad(g, 1, mode='edge')
    ga = (gp[:-2,:-2] + 2*gp[:-2,1:-1] + gp[:-2,2:] +
          2*gp[1:-1,:-2] + 4*gp[1:-1,1:-1] + 2*gp[1:-1,2:] +
          gp[2:,:-2] + 2*gp[2:,1:-1] + gp[2:,2:]) // 16
    res = np.clip(g - ga, -1024, 1024)
    out = clamp14(g + coeff(1024 + res))
    out[:2] = g[:2]; out[-2:] = g[-2:]
    out[:,:2] = g[:,:2]; out[:,-2:] = g[:,-2:]
    return out

def masks(h,w,y0,x0):
    yy,xx = np.indices((h,w)); yy += y0; xx += x0
    r=((yy&1)==0)&((xx&1)==0); b=((yy&1)==1)&((xx&1)==1)
    gr=((yy&1)==0)&((xx&1)==1); gb=((yy&1)==1)&((xx&1)==0)
    return r,b,gr,gb

def frozen_mhc_rgb(raw, nr, nb, y0, x0):
    h,w=raw.shape; R,B,Gr,Gb=masks(h,w,y0,x0)
    raw16=np.clip(np.floor(np.clip(raw-RAW_BLACK,0,RAW_RANGE).astype(np.float64)*65535.0/RAW_RANGE+0.5),0,65535).astype(np.int32)
    n=raw16.astype(np.float64); n[R]/=nr; n[B]/=nb
    C=n; N=shift(n,-1,0); S=shift(n,1,0); W=shift(n,0,-1); E=shift(n,0,1)
    NN=shift(n,-2,0); SS=shift(n,2,0); WW=shift(n,0,-2); EE=shift(n,0,2)
    NW=shift(n,-1,-1); NE=shift(n,-1,1); SW=shift(n,1,-1); SE=shift(n,1,1)
    g=(4*C+2*(N+S+W+E)-(NN+SS+WW+EE))/8.0
    o=(12*C+4*(NW+NE+SW+SE)-3*(NN+SS+WW+EE))/16.0
    hh=(10*C+8*(W+E)+(NN+SS)-2*(NW+NE+SW+SE)-2*(WW+EE))/16.0
    vv=(10*C+8*(N+S)+(WW+EE)-2*(NW+NE+SW+SE)-2*(NN+SS))/16.0
    G16=raw16.copy(); G16[R|B]=nd(g)[R|B]
    R16=np.empty_like(raw16); B16=np.empty_like(raw16)
    R16[R]=raw16[R]; B16[R]=nd(o*nb)[R]
    R16[B]=nd(o*nr)[B]; B16[B]=raw16[B]
    R16[Gr]=nd(hh*nr)[Gr]; B16[Gr]=nd(vv*nb)[Gr]
    R16[Gb]=nd(vv*nr)[Gb]; B16[Gb]=nd(hh*nb)[Gb]
    return raw16,q14(R16),q14(G16),q14(B16),R,B,Gr,Gb

def leica_green_source14(raw16,R,B,Gr,Gb):
    """Image-space interpretation of the recovered green weights.

    Missing-G colour sites:
      ASMFilter_010_101_010_2 with shift=2 -> cardinal 4-neighbour /4.
    Measured-G sites:
      ASMFilter_101_040_101_An -> center/2 + four diagonals/8.
    """
    # Leica firmware stages operate in the 14-bit stored signal domain.
    raw14=q14(raw16)
    g=raw14.astype(np.int64).copy()
    cross=(shift(raw14,-1,0).astype(np.int64)+shift(raw14,1,0)+
           shift(raw14,0,-1)+shift(raw14,0,1))//4
    g[R|B]=cross[R|B]
    diag=(4*raw14.astype(np.int64)+shift(raw14,-1,-1)+shift(raw14,-1,1)+
          shift(raw14,1,-1)+shift(raw14,1,1))//8
    g[Gr|Gb]=diag[Gr|Gb]
    return np.clip(g,0,16383).astype(np.int32)

def metrics(g,r,b):
    gx=np.abs(shift(g,0,1)-shift(g,0,-1)); gy=np.abs(shift(g,1,0)-shift(g,-1,0)); grad=gx+gy
    edge=grad>=np.percentile(grad[4:-4,4:-4],85)
    core=np.zeros_like(edge); core[6:-6,6:-6]=True; edge &= core
    cyan=(g>2048)&(b>2048)&(r<np.minimum(g,b)*0.35)&core
    denom=core.sum(); ed=edge.sum()
    return {
      'r0_pct':100*((r==0)&core).sum()/denom,
      'b0_pct':100*((b==0)&core).sum()/denom,
      'rmax_pct':100*((r==16383)&core).sum()/denom,
      'bmax_pct':100*((b==16383)&core).sum()/denom,
      'edge_r0_pct':100*((r==0)&edge).sum()/ed,
      'edge_b0_pct':100*((b==0)&edge).sum()/ed,
      'cyan_pct':100*cyan.sum()/denom,
      'edge_cyan_pct':100*(cyan&edge).sum()/ed,
    }

def replay_tile(raw,nr,nb,y0,x0):
    raw16,R14,G14,B14,R,B,Gr,Gb=frozen_mhc_rgb(raw,nr,nb,y0,x0)
    sg=sharp14(G14)
    old_r=clamp14(sg+(R14-G14)); old_b=clamp14(sg+(B14-G14))
    src=leica_green_source14(raw16,R,B,Gr,Gb); ssrc=sharp14(src)
    delta=ssrc.astype(np.int64)-src.astype(np.int64)
    ga=clamp14(G14.astype(np.int64)+delta)
    ra=clamp14(R14.astype(np.int64)+delta)
    ba=clamp14(B14.astype(np.int64)+delta)
    return sg,old_r,old_b,ga,ra,ba,delta

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('dng',type=Path)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--tile',type=int,default=512)
    a=ap.parse_args()
    with tifffile.TiffFile(a.dng) as tf:
        full=tf.pages[0].asarray().astype(np.int32); asn=tf.pages[0].tags['AsShotNeutral'].value
    nr=asn[0]/asn[1]; nb=asn[4]/asn[5]; H,W=full.shape; T=a.tile
    gp=(full[0::2,1::2].astype(np.int32)+full[1::2,0::2].astype(np.int32))//2
    grad=np.abs(np.diff(gp,axis=1,prepend=gp[:,:1]))+np.abs(np.diff(gp,axis=0,prepend=gp[:1,:]))
    cand=[]
    for y0 in range(0,H-T+1,T):
      for x0 in range(0,W-T+1,T):
        q=grad[y0//2:(y0+T)//2,x0//2:(x0+T)//2]
        cand.append((float(np.percentile(q,95)),y0,x0))
    cand.sort(reverse=True); picks=cand[:6]+[min(cand)]
    rows=[]
    for score,y0,x0 in picks:
        halo=8; ya=max(0,y0-halo); xa=max(0,x0-halo); yb=min(H,y0+T+halo); xb=min(W,x0+T+halo)
        sg,ro,bo,ga,ra,ba,d=replay_tile(full[ya:yb,xa:xb],nr,nb,ya,xa)
        ys=y0-ya; xs=x0-xa; sl=np.s_[ys:ys+T,xs:xs+T]
        core=d[sl][6:-6,6:-6]
        rows.append({'tile':[y0,x0,T,T],'edge_score_p95':score,'old_1b':metrics(sg[sl],ro[sl],bo[sl]),
                     'sharpsource1a':metrics(ga[sl],ra[sl],ba[sl]),
                     'delta_stats':{'mean':float(core.mean()),'p01':float(np.percentile(core,1)),
                                    'p50':float(np.percentile(core,50)),'p99':float(np.percentile(core,99)),
                                    'min':int(core.min()),'max':int(core.max())}})
    report={'schema':'m9.sharpsource1a-replay.v1','dng':a.dng.name,
            'status':'offline diagnostic; firmware-derived weights and interior CFA phase mapping; border/tile traversal parity still open',
            'neutralRoverG':nr,'neutralBoverG':nb,'tiles':rows,'mean':{}}
    for k in ('r0_pct','b0_pct','edge_r0_pct','edge_b0_pct','cyan_pct','edge_cyan_pct','rmax_pct','bmax_pct'):
      report['mean']['old_1b_'+k]=float(np.mean([r['old_1b'][k] for r in rows]))
      report['mean']['sharpsource1a_'+k]=float(np.mean([r['sharpsource1a'][k] for r in rows]))
    out=a.out or a.dng.with_name(a.dng.stem+'_SHARPSOURCE1A.json')
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['mean'],indent=2))
    print(out)
if __name__=='__main__': main()
