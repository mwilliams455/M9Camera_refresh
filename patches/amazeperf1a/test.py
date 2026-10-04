#!/usr/bin/env python3
"""Exact parity + host timing for AMAZEPERF1A parallel peripheral stages."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('AMAZEPERF1A_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=REPO/'patches/tests/colourtrial1d'
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int;D=C.c_double

varp=lib.trial_variance_parallel
varp.argtypes=[P,I,I,I,I,P,I,P,P,I,I,D,P,P,I];varp.restype=I
reconp=lib.trial_reconstruct_perf
reconp.argtypes=[P,P,P,I,I,I,D,D,D,P,I,P,P];reconp.restype=I

rng=np.random.default_rng(189)
profile=np.array([2.5e-4,6.4e-7,2.53e-4,5.6e-7,2.54e-4,6.6e-7],np.float64)
black=np.array([64,64,64,64],np.float32)
mw,mh=17,13;scale=1.56
gains=np.empty((mh,mw,4),np.float64)
for y in range(mh):
  for x in range(mw):
    r=((x/(mw-1)-.5)**2+(y/(mh-1)-.5)**2)
    v=min(scale,1.0+.48*r)
    gains[y,x]=[v*.995,v*.99,v*.99,v]
gains=np.minimum(gains,scale).reshape(-1)

# Exact variance-transport parity across CFA/origin phases.
variance_cases=[]
for cfa in range(4):
  w,h=769,513
  sensor=rng.integers(64,1024,(h,w),np.uint16)
  # Explicit censored samples exercise exact mask parity.
  sensor[20:25,30:35]=64;sensor[200:205,400:405]=1023
  a=np.empty((h,w),np.float32);am=np.empty((h,w),np.uint8)
  b=np.empty_like(a);bm=np.empty_like(am)
  assert lib.trial_variance(sensor.ctypes.data,w,h,cfa,1,black.ctypes.data,1023,
      profile.ctypes.data,gains.ctypes.data,mw,mh,scale,a.ctypes.data,am.ctypes.data)==0
  assert varp(sensor.ctypes.data,w,h,cfa,1,black.ctypes.data,1023,
      profile.ctypes.data,gains.ctypes.data,mw,mh,scale,b.ctypes.data,bm.ctypes.data,8)==0
  assert np.array_equal(a,b),('variance parity',cfa,np.max(np.abs(a.astype(float)-b)))
  assert np.array_equal(am,bm),('censor parity',cfa)
  variance_cases.append(cfa)

# Exact reconstruction parity. Frozen scalar trial_reconstruct remains the oracle;
# optimized path uses the same phase_noise and AMaZE call but parallelizes only
# independent peripheral rows.
recon_cases=[]
for cfa in range(4):
  w,h=641,513
  raw=rng.integers(900,61000,(h,w),np.uint16)
  var=np.full((h,w),28000,np.float32)
  censor=np.zeros((h,w),np.uint8);censor[100:105,200:205]=1
  scalar=np.empty((h,w,3),np.uint16);fast=np.empty_like(scalar)
  ss=np.zeros(4,np.float64);fs=np.zeros(4,np.float64);perf=np.zeros(5,np.float64)
  assert lib.trial_reconstruct(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.41,.59,1.7,
      scalar.ctypes.data,8,ss.ctypes.data)==0
  assert reconp(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.41,.59,1.7,
      fast.ctypes.data,8,fs.ctypes.data,perf.ctypes.data)==0
  assert np.array_equal(scalar,fast),('reconstruct parity',cfa,int(np.count_nonzero(scalar!=fast)))
  assert np.array_equal(ss,fs),('reconstruct stats parity',cfa,ss,fs)
  assert np.all(np.isfinite(perf)) and np.all(perf>=0)
  recon_cases.append({'cfa':cfa,'perfMs':perf.tolist()})

# Informational host timings on a larger frame. Quality is gated by byte parity,
# not by these host numbers.
w,h=1536,1024
sensor=rng.integers(64,1024,(h,w),np.uint16)
va=np.empty((h,w),np.float32);ma=np.empty((h,w),np.uint8)
vb=np.empty_like(va);mb=np.empty_like(ma)
vt=[]
for rep in range(3):
  t=time.perf_counter();assert lib.trial_variance(sensor.ctypes.data,w,h,0,0,black.ctypes.data,1023,
      profile.ctypes.data,gains.ctypes.data,mw,mh,scale,va.ctypes.data,ma.ctypes.data)==0
  scalarMs=(time.perf_counter()-t)*1000
  t=time.perf_counter();assert varp(sensor.ctypes.data,w,h,0,0,black.ctypes.data,1023,
      profile.ctypes.data,gains.ctypes.data,mw,mh,scale,vb.ctypes.data,mb.ctypes.data,8)==0
  parallelMs=(time.perf_counter()-t)*1000
  assert np.array_equal(va,vb) and np.array_equal(ma,mb)
  vt.append({'rep':rep,'scalarVarianceMs':scalarMs,'parallelVarianceMs':parallelMs})

raw=rng.integers(900,61000,(h,w),np.uint16)
var=np.full((h,w),28000,np.float32);censor=np.zeros((h,w),np.uint8)
rt=[]
for rep in range(2):
  scalar=np.empty((h,w,3),np.uint16);fast=np.empty_like(scalar)
  ss=np.zeros(4,np.float64);fs=np.zeros(4,np.float64);perf=np.zeros(5,np.float64)
  t=time.perf_counter();assert lib.trial_reconstruct(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,0,.41,.59,1.7,
      scalar.ctypes.data,8,ss.ctypes.data)==0
  scalarMs=(time.perf_counter()-t)*1000
  t=time.perf_counter();assert reconp(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,0,.41,.59,1.7,
      fast.ctypes.data,8,fs.ctypes.data,perf.ctypes.data)==0
  fastMs=(time.perf_counter()-t)*1000
  assert np.array_equal(scalar,fast) and np.array_equal(ss,fs)
  rt.append({'rep':rep,'scalarReconstructMs':scalarMs,'parallelPeripheralReconstructMs':fastMs,
             'phaseNoiseMs':float(perf[0]),'quarterBlendMs':float(perf[1]),
             'floatInputMs':float(perf[2]),'amazeCoreMs':float(perf[3]),
             'outputQuantizeMs':float(perf[4])})

receipt={
  'revision':'M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT',
  'workers':8,
  'varianceByteExact':True,
  'varianceMaskExact':True,
  'reconstructRgbByteExact':True,
  'reconstructStatsExact':True,
  'cfaParityCases':len(recon_cases),
  'amazeAlgorithmChanged':False,
  'amazeChunk':2,
  'phaseNoiseChanged':False,
  'varianceTiming':vt,
  'varianceScalarMedianMs':float(np.median([x['scalarVarianceMs'] for x in vt])),
  'varianceParallelMedianMs':float(np.median([x['parallelVarianceMs'] for x in vt])),
  'reconstructTiming':rt,
  'reconstructScalarMedianMs':float(np.median([x['scalarReconstructMs'] for x in rt])),
  'reconstructParallelPeripheralMedianMs':float(np.median([x['parallelPeripheralReconstructMs'] for x in rt])),
  'timingInformationalOnly':True,
}
(OUT/'amazeperf1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
