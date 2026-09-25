#!/usr/bin/env python3
"""Byte-exact parity + timing for PHASENOISEPERF1A."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('PHASENOISEPERF1A_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=REPO/'patches/tests/colourtrial1d'
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int;D=C.c_double
fast=lib.phase_noise_banded_exact
fast.argtypes=[P,P,P,I,I,P,I];fast.restype=I
lib.m9_phasenoiseperf1a_band_rows.argtypes=[]
lib.m9_phasenoiseperf1a_band_rows.restype=I
assert lib.m9_phasenoiseperf1a_band_rows()==64

rng=np.random.default_rng(190)
cases=[]

# Diverse geometry, clipping and variance contracts. Exact uint16 output is the gate.
for w,h in [(16,16),(31,37),(65,67),(129,131),(257,193),(641,513)]:
  raw=rng.integers(0,65536,(h,w),np.uint16)
  var=np.exp(rng.uniform(np.log(20.0),np.log(180000.0),(h,w))).astype(np.float32)
  clip=np.zeros((h,w),np.uint8)
  # Exercise explicit clipping, zero and negative/invalid-effective variance bypass.
  if h>20 and w>20:
    clip[7::23,9::29]=1
    var[8::31,11::37]=0
  for workers in [1,2,4,8]:
    a=np.empty_like(raw);b=np.empty_like(raw)
    assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,a.ctypes.data,workers)==0
    assert fast(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,workers)==0
    assert np.array_equal(a,b),(w,h,workers,int(np.count_nonzero(a!=b)),int(np.max(np.abs(a.astype(np.int32)-b.astype(np.int32)))))
    cases.append({'w':w,'h':h,'workers':workers,'changed':int(np.count_nonzero(a!=raw))})

# Structured scene-like data catches same-phase edge and repeated-pattern behaviour.
w,h=1024,768
yy,xx=np.indices((h,w))
base=12000+18*xx+9*yy
raw=np.clip(base + 2400*np.sin(xx/13.0)+1700*np.cos(yy/19.0)+rng.normal(0,700,(h,w)),0,65535).astype(np.uint16)
var=(12000+0.7*raw).astype(np.float32)
clip=np.zeros((h,w),np.uint8)
clip[100:140,300:370]=1
var[500:520,700:730]=0
a=np.empty_like(raw);b=np.empty_like(raw)
assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,a.ctypes.data,8)==0
assert fast(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,8)==0
assert np.array_equal(a,b),('structured',int(np.count_nonzero(a!=b)))

# Exact end-to-end reconstruction parity across all CFA patterns.
recon_cases=[]
for cfa in range(4):
  w,h=385,321
  raw=rng.integers(900,61000,(h,w),np.uint16)
  var=np.exp(rng.uniform(np.log(100.0),np.log(90000.0),(h,w))).astype(np.float32)
  censor=np.zeros((h,w),np.uint8);censor[30:35,80:87]=1
  scalar=np.empty((h,w,3),np.uint16);prod=np.empty_like(scalar)
  ss=np.zeros(4,np.float64);ps=np.zeros(4,np.float64);perf=np.zeros(5,np.float64)
  assert lib.trial_reconstruct(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.42,.61,1.7,
      scalar.ctypes.data,8,ss.ctypes.data)==0
  assert lib.trial_reconstruct_perf(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.42,.61,1.7,
      prod.ctypes.data,8,ps.ctypes.data,perf.ctypes.data)==0
  assert np.array_equal(scalar,prod),('reconstruct',cfa,int(np.count_nonzero(scalar!=prod)))
  assert np.array_equal(ss,ps),('stats',cfa,ss,ps)
  recon_cases.append({'cfa':cfa,'phaseNoiseMs':float(perf[0])})

# Informational host timing. Correctness, not speed, is the hard CI gate.
timings=[]
w,h=1536,1024
raw=rng.integers(500,62000,(h,w),np.uint16)
var=(15000+0.9*raw).astype(np.float32)
clip=np.zeros((h,w),np.uint8)
clip[::97,::89]=1
for rep in range(3):
  a=np.empty_like(raw);b=np.empty_like(raw)
  t=time.perf_counter();assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,a.ctypes.data,8)==0
  scalar=(time.perf_counter()-t)*1000
  t=time.perf_counter();assert fast(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,8)==0
  banded=(time.perf_counter()-t)*1000
  assert np.array_equal(a,b)
  timings.append({'rep':rep,'scalarMs':scalar,'bandedExactMs':banded})

receipt={
  'revision':'M9PHASENOISEPERF1A_BANDED_TERM_REUSE_EXACT',
  'bandRows':64,
  'parityCases':len(cases),
  'phaseNoiseByteExact':True,
  'structuredByteExact':True,
  'reconstructRgbByteExact':True,
  'reconstructStatsExact':True,
  'allFourCfaReconstruction':True,
  'candidateOrderChanged':False,
  'patchOrderChanged':False,
  'rawNoiseStrengthChanged':False,
  'fullFrameDistanceCacheAdded':False,
  'timings':timings,
  'scalarMedianMs':float(np.median([x['scalarMs'] for x in timings])),
  'bandedExactMedianMs':float(np.median([x['bandedExactMs'] for x in timings])),
  'timingInformationalOnly':True,
}
(OUT/'phasenoiseperf1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
