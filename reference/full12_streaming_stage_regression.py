#!/usr/bin/env python3
"""Byte-exact arithmetic smoke: N buffered stage vs FULL12 streamed pair stage."""
import math, random
RAW_MAX=16383; LUT_MAX=2047
QE=[16754,-7632,-922,-3124,14774,-3458,-567,-9579,18330]
QO=[15518,-6430,-896,-2330,14388,-3866,-493,-10024,18709]
TG_CB=.25; TG_CR=.16

def clip(v,a,b): return a if v<a else b if v>b else v
def round_u8(v): return int(clip(v/255.0,0.0,1.0)*255.0+0.5)
def curve_pixel(m9,gain,curve):
    vals=[clip(round(v*gain*RAW_MAX),0,RAW_MAX) for v in m9]
    r,g,b=vals; q=QE if r>=g else QO
    aa=[q[i]*r+q[i+1]*g+q[i+2]*b for i in (0,3,6)]
    idx=[clip(a>>16,0,LUT_MAX) for a in aa]
    return tuple(curve[i] for i in idx)
def pair(rgb0,rgb1,tgw):
    r0,g0,b0=rgb0; r1,g1,b1=rgb1
    y0=(4899*r0+9617*g0+1868*b0)>>14; y1=(4899*r1+9617*g1+1868*b1)>>14
    rs=r0+r1; gs=g0+g1; bs=b0+b1
    cbs=((((-2765*rs+1)>>1)-((5427*gs)>>1)+((8192*bs)>>1)))>>14
    crs=((((8192*rs)>>1)-((6860*gs)>>1)-((1332*bs)>>1)))>>14
    cb=((cbs+128)&255)-128; cr=((crs+128)&255)-128
    cbm=cb*(1-TG_CB*tgw) if cb<0 else cb; crm=cr*(1-TG_CR*tgw) if cr<0 else cr
    def one(y): return (round_u8(y+1.402*crm),round_u8(y-.344136*cbm-.714136*crm),round_u8(y+1.772*cbm))
    return one(y0),one(y1)

def buffered(m9s,gain,curve,tgw):
    rgb=[curve_pixel(v,gain,curve) for v in m9s]
    out=[]
    for i in range(0,len(rgb)-1,2): out.extend(pair(rgb[i],rgb[i+1],tgw))
    if len(rgb)&1: out.append(rgb[-1])
    return out

def streamed(m9s,gain,curve,tgw):
    out=[]
    i=0
    while i+1<len(m9s):
        out.extend(pair(curve_pixel(m9s[i],gain,curve),curve_pixel(m9s[i+1],gain,curve),tgw)); i+=2
    if i<len(m9s): out.append(curve_pixel(m9s[i],gain,curve))
    return out

rng=random.Random(0x912)
curve=[int(round((i/LUT_MAX)**(1/2.15)*255)) for i in range(LUT_MAX+1)]
for n in (2,3,16,127,1024):
    for _ in range(30):
        m9s=[[rng.random()*1.4 for _ in range(3)] for __ in range(n)]
        gain=10**rng.uniform(-.25,.8); tgw=rng.random()
        a=buffered(m9s,gain,curve,tgw); b=streamed(m9s,gain,curve,tgw)
        assert a==b, (n,gain,tgw)
print('FULL12 streamed SAT3/curve02/BT601/TG1 arithmetic regression PASS')
