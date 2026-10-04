#!/usr/bin/env python3
"""Exact-output parity and host timing regression for NOISEPERF1A."""
from pathlib import Path
import ctypes as C,json,subprocess,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OUT=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
ASSEMBLED=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
BASE=REPO/'patches/noisecancel1b/m9noisecancel1b.cpp'
CAND=(ASSEMBLED/'app/src/main/cpp/m9noisecancel1b.cpp') if ASSEMBLED else HERE/'m9noisecancel1b.cpp'

def build(src,name,macro):
    so=OUT/(name+'.so')
    cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off',
         '-fno-fast-math','-fPIC','-shared','-pthread','-D'+macro,str(src),'-o',str(so)]
    subprocess.run(cmd,check=True)
    lib=C.CDLL(str(so));fn=lib.m9_noisecancel1b_apply
    fn.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_double,C.c_void_p]
    fn.restype=C.c_int
    return fn,cmd

base,base_cmd=build(BASE,'scalar','M9NOISECANCEL1B_HOST')
cand,cand_cmd=build(CAND,'parallel','M9NOISEPERF1A_HOST')

def call(fn,rgb,profile,gains,mw,mh,scale):
    # Always isolate each implementation from the other's in-place output.
    a=np.array(rgb,dtype=np.uint16,copy=True,order='C');p=np.ascontiguousarray(profile,np.float64)
    g=np.ascontiguousarray(gains,np.float64);stats=np.zeros(14,np.float64)
    t=time.perf_counter()
    rc=fn(a.ctypes.data,a.shape[1],a.shape[0],p.ctypes.data,g.ctypes.data,mw,mh,scale,stats.ctypes.data)
    wall=(time.perf_counter()-t)*1000
    if rc: raise RuntimeError('native rc='+str(rc))
    return a,stats,wall

rng=np.random.default_rng(187)
h,w=768,1024;mw,mh=17,13;scale=1.72
# Structured + random image stresses worker boundaries, edges, clipping and quiet areas.
yy,xx=np.indices((h,w))
green=np.clip(9000 + 18*xx + 7*yy + rng.normal(0,170,(h,w)),0,65535)
r=np.clip(green + 1300*np.sin(xx/21.0) + rng.normal(0,520,(h,w)),0,65535)
b=np.clip(green - 900*np.cos(yy/17.0) + rng.normal(0,610,(h,w)),0,65535)
rgb=np.stack([r,green,b],axis=2).astype(np.uint16)
rgb[40:65,70:100]=0
rgb[300:330,500:540]=65535
profile=np.array([.00135,6.7e-6,.00134,6.1e-6,.00137,6.8e-6],np.float64)
gains=np.empty((mh,mw,4),np.float64)
for gy in range(mh):
  for gx in range(mw):
    common=1.0+(scale-1.0)*((gx/(mw-1)-.5)**2+(gy/(mh-1)-.5)**2)
    common=min(scale,max(.98,common))
    gains[gy,gx]=[common*.99,common*.985,common*.985,common*.995]
gains=np.minimum(gains,scale).reshape(-1)

# Multiple deterministic passes ensure exact parity is stable, not accidental.
records=[]
for seedoff in range(3):
    src=rgb.copy()
    if seedoff:
        src=np.roll(src,seedoff*7,axis=1)
    bo,bs,bwall=call(base,src,profile,gains,mw,mh,scale)
    co,cs,cwall=call(cand,src,profile,gains,mw,mh,scale)
    assert np.array_equal(bo,co),f'pixel parity failure pass {seedoff}'
    for idx in [0,1,2,3,4,6,7,10,11]:
        assert bs[idx]==cs[idx],(seedoff,idx,bs[idx],cs[idx])
    assert abs(bs[5]-cs[5])<1e-11,(bs[5],cs[5])
    assert abs(bs[8]-cs[8])<1e-9,(bs[8],cs[8])
    assert int(cs[12])==8,cs[12]
    assert cs[13]==1
    assert np.array_equal(co[:,:,1],src[:,:,1]),'green changed'
    records.append({'pass':seedoff,'scalarWallMs':bwall,'parallelWallMs':cwall,
                    'parallelWorkers':int(cs[12]),'changed':int(cs[1])})

# Border rows/columns are untouched exactly.
co,cs,_=call(cand,rgb,profile,gains,mw,mh,scale)
assert np.array_equal(co[0],rgb[0]) and np.array_equal(co[-1],rgb[-1])
assert np.array_equal(co[:,0],rgb[:,0]) and np.array_equal(co[:,-1],rgb[:,-1])

receipt={
  'revision':'M9NOISEPERF1A_PARALLEL8_EXACT',
  'pixelParityVsFrozen1p86Scalar':True,
  'integerDiagnosticParity':True,
  'greenExact':True,
  'borderExact':True,
  'parallelWorkers':8,
  'fullFrameCopyAdded':False,
  'passes':records,
  'scalarMedianWallMs':float(np.median([x['scalarWallMs'] for x in records])),
  'parallelMedianWallMs':float(np.median([x['parallelWallMs'] for x in records])),
  'hostTimingInformationalOnly':True,
  'baseCompile':base_cmd,
  'candidateCompile':cand_cmd,
}
(OUT/'noiseperf1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
