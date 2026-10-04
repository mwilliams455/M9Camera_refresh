#!/usr/bin/env python3
"""Exact parity + informational timing for PREPPERF1A."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('PREPPERF1A_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Build with the COLOURTRIAL1D host wrapper so trial_prepare_inplace is exported.
m.HERE=REPO/'patches/tests/colourtrial1d'
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int;D=C.c_double
lib.trial_prepare_inplace.argtypes=[P,P,I,I,D,I]
lib.trial_prepare_inplace.restype=I
lib.partial_chroma_parallel.argtypes=[P,I,I,D,P,I]
lib.partial_chroma_parallel.restype=I
lib.m9_prepperf1a_workers.argtypes=[]
lib.m9_prepperf1a_workers.restype=I
assert lib.m9_prepperf1a_workers()==8

rng=np.random.default_rng(188)
curve=np.frombuffer((ROOT/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).copy()
ctx=np.r_[np.ones(3),np.array([[1.1,-.06,-.04],[-.07,1.11,-.04],[-.03,-.07,1.10]]).ravel(),np.tile(np.eye(3).ravel(),4)].astype(float)
c=lib.trial_context(ctx.ctypes.data,curve.ctypes.data)
assert c

cases=[]
for w,h in [(1,9),(3,3),(65,67),(129,385),(130,257),(385,513),(1024,768)]:
    raw=rng.integers(0,65536,(h,w,3),np.uint16)
    expected=np.empty_like(raw)
    assert lib.trial_prepare(c,raw.ctypes.data,w,h,2**.5,expected.ctypes.data,128)==0
    for band in ([2,31,128,384,h] if h<1000 else [128]):
        if band<2: continue
        got=raw.copy()
        assert lib.trial_prepare_inplace(c,got.ctypes.data,w,h,2**.5,band)==0
        assert np.array_equal(got,expected),(w,h,band,int(np.count_nonzero(got!=expected)))
        cases.append([w,h,band])

# The added parallel chroma entry must be byte-identical to the untouched scalar oracle.
for w,h in [(3,3),(129,131),(513,259)]:
    src=rng.integers(0,16384,(h,w,3),np.uint16)
    scalar=np.empty_like(src);parallel=np.empty_like(src)
    assert lib.partial_chroma(src.ctypes.data,w,h,.25,scalar.ctypes.data)==0
    assert lib.partial_chroma_parallel(src.ctypes.data,w,h,.25,parallel.ctypes.data,8)==0
    assert np.array_equal(scalar,parallel),(w,h,int(np.count_nonzero(scalar!=parallel)))

# One 12 MP exact parity case guards the production geometry and every 128-row seam.
w,h=4096,3072
raw12=rng.integers(0,65536,(h,w,3),np.uint16)
expected12=np.empty_like(raw12)
t0=time.perf_counter();assert lib.trial_prepare(c,raw12.ctypes.data,w,h,2**.25,expected12.ctypes.data,128)==0
scalar12=(time.perf_counter()-t0)*1000.0
got12=raw12.copy()
t0=time.perf_counter();assert lib.trial_prepare_inplace(c,got12.ctypes.data,w,h,2**.25,128)==0
parallel12=(time.perf_counter()-t0)*1000.0
assert np.array_equal(got12,expected12),('12MP parity',int(np.count_nonzero(got12!=expected12)))
del raw12,expected12,got12

# Repeated medium frame timing is informational only; correctness is the hard gate.
w,h=1536,1024
timing=[]
for rep in range(3):
    raw=rng.integers(0,65536,(h,w,3),np.uint16)
    expected=np.empty_like(raw)
    t0=time.perf_counter();assert lib.trial_prepare(c,raw.ctypes.data,w,h,2**.25,expected.ctypes.data,128)==0
    scalar=(time.perf_counter()-t0)*1000.0
    got=raw.copy()
    t0=time.perf_counter();assert lib.trial_prepare_inplace(c,got.ctypes.data,w,h,2**.25,128)==0
    parallel=(time.perf_counter()-t0)*1000.0
    assert np.array_equal(got,expected)
    timing.append({'rep':rep,'scalarOutOfPlaceMs':scalar,'parallelInPlaceMs':parallel})

lib.trial_destroy(c)
receipt={
  'revision':'M9PREPPERF1A_PARALLEL8_EXACT',
  'workers':8,
  'inPlaceVsFrozenScalarByteExact':True,
  'partialChromaParallelVsScalarByteExact':True,
  'parityCases':len(cases),
  'includes12MPParity':True,
  'scalar12MpMs':scalar12,
  'parallel12MpMs':parallel12,
  'mediumTimings':timing,
  'scalarMedianMediumMs':float(np.median([x['scalarOutOfPlaceMs'] for x in timing])),
  'parallelMedianMediumMs':float(np.median([x['parallelInPlaceMs'] for x in timing])),
  'timingInformationalOnly':True,
  'photographicMathChanged':False,
  'fullFrameCopyAdded':False,
}
(OUT/'prepperf1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
