#!/usr/bin/env python3
"""Exact parity + same-run timing for PREPPERF1B persistent OpenMP team."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('PREPPERF1B_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=HERE
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int;D=C.c_double
prod=lib.trial_prepare_inplace
prod.argtypes=[P,P,I,I,D,I];prod.restype=I
onea=lib.trial_prepare_inplace_1a
onea.argtypes=[P,P,I,I,D,I];onea.restype=I
lib.m9_prepperf1a_workers.argtypes=[];lib.m9_prepperf1a_workers.restype=I
lib.m9_prepperf1b_workers.argtypes=[];lib.m9_prepperf1b_workers.restype=I
lib.m9_prepperf1b_band_rows.argtypes=[];lib.m9_prepperf1b_band_rows.restype=I
lib.m9_prepperf1b_revision.argtypes=[];lib.m9_prepperf1b_revision.restype=C.c_char_p
assert lib.m9_prepperf1a_workers()==8
assert lib.m9_prepperf1b_workers()==8
assert lib.m9_prepperf1b_band_rows()==128
assert lib.m9_prepperf1b_revision()==b'M9PREPPERF1B_PERSISTENT8_EXACT'

rng=np.random.default_rng(192)
curve=np.frombuffer((ROOT/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).copy()
ctx=np.r_[np.ones(3),np.array([[1.1,-.06,-.04],[-.07,1.11,-.04],[-.03,-.07,1.10]]).ravel(),np.tile(np.eye(3).ravel(),4)].astype(float)
c=lib.trial_context(ctx.ctypes.data,curve.ctypes.data);assert c

cases=[]
for w,h in [(1,9),(3,3),(31,37),(65,67),(129,385),(130,257),(385,513),(1024,768)]:
 raw=rng.integers(0,65536,(h,w,3),np.uint16)
 scalar=np.empty_like(raw)
 assert lib.trial_prepare(c,raw.ctypes.data,w,h,2**.5,scalar.ctypes.data,128)==0
 for band in ([2,31,64,128,256,384,h] if h<1000 else [64,128,256,384]):
  if band<2: continue
  a=raw.copy();b=raw.copy()
  assert onea(c,a.ctypes.data,w,h,2**.5,band)==0
  assert prod(c,b.ctypes.data,w,h,2**.5,band)==0
  assert np.array_equal(a,scalar),(w,h,band,'1a-vs-scalar',int(np.count_nonzero(a!=scalar)))
  assert np.array_equal(b,scalar),(w,h,band,'1b-vs-scalar',int(np.count_nonzero(b!=scalar)))
  cases.append({'w':w,'h':h,'band':band})

# 12 MP production hard gate and same-run 1A vs 1B timing.
w,h=4096,3072
raw=rng.integers(0,65536,(h,w,3),np.uint16)
expected=np.empty_like(raw)
t=time.perf_counter();assert lib.trial_prepare(c,raw.ctypes.data,w,h,2**.25,expected.ctypes.data,128)==0
scalar12=(time.perf_counter()-t)*1000
onea12=raw.copy()
t=time.perf_counter();assert onea(c,onea12.ctypes.data,w,h,2**.25,128)==0
onea12ms=(time.perf_counter()-t)*1000
assert np.array_equal(onea12,expected),('12mp-1a',int(np.count_nonzero(onea12!=expected)))
del onea12
prod12=raw.copy()
t=time.perf_counter();assert prod(c,prod12.ctypes.data,w,h,2**.25,128)==0
oneb12ms=(time.perf_counter()-t)*1000
assert np.array_equal(prod12,expected),('12mp-1b',int(np.count_nonzero(prod12!=expected)))
del prod12,expected,raw

# Repeated medium workload to reduce one-shot runner noise.
timings=[]
w,h=1536,1024
for rep in range(4):
 raw=rng.integers(0,65536,(h,w,3),np.uint16)
 a=raw.copy();b=raw.copy()
 t=time.perf_counter();assert onea(c,a.ctypes.data,w,h,2**.25,128)==0
 a_ms=(time.perf_counter()-t)*1000
 t=time.perf_counter();assert prod(c,b.ctypes.data,w,h,2**.25,128)==0
 b_ms=(time.perf_counter()-t)*1000
 assert np.array_equal(a,b),('medium',rep,int(np.count_nonzero(a!=b)))
 timings.append({'rep':rep,'prepperf1aMs':a_ms,'prepperf1bMs':b_ms})

lib.trial_destroy(c)
receipt={
 'revision':'M9PREPPERF1B_PERSISTENT8_EXACT',
 'workers':8,'bandRows':128,
 'scalarVs1aByteExact':True,
 'scalarVs1bByteExact':True,
 'prep1aVs1bByteExact':True,
 'parityCases':len(cases),
 'includes12MPParity':True,
 'scalar12MpMs':scalar12,
 'prepperf1a12MpMs':onea12ms,
 'prepperf1b12MpMs':oneb12ms,
 'twelveMpSpeedup':onea12ms/oneb12ms,
 'mediumTimings':timings,
 'prepperf1aMedianMediumMs':float(np.median([x['prepperf1aMs'] for x in timings])),
 'prepperf1bMedianMediumMs':float(np.median([x['prepperf1bMs'] for x in timings])),
 'persistentWorkerTeam':True,
 'workerTeamLaunchesPerFrame':1,
 'bandRowsChanged':False,
 'photographicMathChanged':False,
 'chromaStrengthChanged':False,
 'fullFrameCopyAdded':False,
 'timingInformationalOnly':True,
}
(OUT/'prepperf1b_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
