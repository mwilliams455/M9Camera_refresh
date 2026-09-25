#!/usr/bin/env python3
"""Byte-exact parity + timing for PHASENOISEPERF1B symmetric reuse."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('PHASENOISEPERF1B_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=REPO/'patches/tests/colourtrial1d'
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int
banded=lib.phase_noise_banded_exact
banded.argtypes=[P,P,P,I,I,P,I];banded.restype=I
sym=lib.phase_noise_symmetric_exact
sym.argtypes=[P,P,P,I,I,P,I];sym.restype=I
lib.m9_phasenoiseperf1b_tile_rows.argtypes=[];lib.m9_phasenoiseperf1b_tile_rows.restype=I
lib.m9_phasenoiseperf1b_tile_cols.argtypes=[];lib.m9_phasenoiseperf1b_tile_cols.restype=I
lib.trial_reconstruct_perf.argtypes=[P,P,P,I,I,I,C.c_double,C.c_double,C.c_double,P,I,P,P]
lib.trial_reconstruct_perf.restype=I
assert lib.m9_phasenoiseperf1b_tile_rows()==32
assert lib.m9_phasenoiseperf1b_tile_cols()==256

rng=np.random.default_rng(191)
cases=[]
for w,h in [(16,16),(31,37),(65,67),(129,131),(257,193),(513,321),(641,513)]:
  raw=rng.integers(0,65536,(h,w),np.uint16)
  var=np.exp(rng.uniform(np.log(20.0),np.log(180000.0),(h,w))).astype(np.float32)
  clip=np.zeros((h,w),np.uint8)
  if h>20 and w>20:
    clip[7::23,9::29]=1
    var[8::31,11::37]=0
  for workers in [1,2,4,8]:
    scalar=np.empty_like(raw);onea=np.empty_like(raw);oneb=np.empty_like(raw)
    assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,scalar.ctypes.data,workers)==0
    assert banded(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,onea.ctypes.data,workers)==0
    assert sym(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,oneb.ctypes.data,workers)==0
    assert np.array_equal(scalar,onea),(w,h,workers,'1a')
    assert np.array_equal(scalar,oneb),(w,h,workers,'1b',int(np.count_nonzero(scalar!=oneb)),
        int(np.max(np.abs(scalar.astype(np.int32)-oneb.astype(np.int32)))))
    cases.append({'w':w,'h':h,'workers':workers,'changed':int(np.count_nonzero(oneb!=raw))})

# Tile-boundary-heavy structured scene: exercises 32-row and 256-column seams.
w,h=1031,779
yy,xx=np.indices((h,w))
base=10000+17*xx+8*yy
raw=np.clip(base+2100*np.sin(xx/11.0)+1600*np.cos(yy/17.0)+rng.normal(0,650,(h,w)),0,65535).astype(np.uint16)
var=(9000+0.75*raw).astype(np.float32)
clip=np.zeros((h,w),np.uint8)
clip[100:140,250:330]=1
clip[511:520,767:775]=1
var[500:525,700:740]=0
scalar=np.empty_like(raw);onea=np.empty_like(raw);oneb=np.empty_like(raw)
assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,scalar.ctypes.data,8)==0
assert banded(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,onea.ctypes.data,8)==0
assert sym(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,oneb.ctypes.data,8)==0
assert np.array_equal(scalar,onea)
assert np.array_equal(scalar,oneb),('structured',int(np.count_nonzero(scalar!=oneb)))

# Full production reconstruction parity for every CFA. Production trial_reconstruct_perf
# is routed through 1B; scalar trial_reconstruct remains the frozen oracle.
recon=[]
for cfa in range(4):
  w,h=385,321
  raw=rng.integers(900,61000,(h,w),np.uint16)
  var=np.exp(rng.uniform(np.log(100.0),np.log(90000.0),(h,w))).astype(np.float32)
  censor=np.zeros((h,w),np.uint8);censor[30:35,80:87]=1
  scalarRgb=np.empty((h,w,3),np.uint16);prodRgb=np.empty_like(scalarRgb)
  ss=np.zeros(4,np.float64);ps=np.zeros(4,np.float64);perf=np.zeros(5,np.float64)
  assert lib.trial_reconstruct(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.42,.61,1.7,
      scalarRgb.ctypes.data,8,ss.ctypes.data)==0
  assert lib.trial_reconstruct_perf(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.42,.61,1.7,
      prodRgb.ctypes.data,8,ps.ctypes.data,perf.ctypes.data)==0
  assert np.array_equal(scalarRgb,prodRgb),('reconstruct',cfa,int(np.count_nonzero(scalarRgb!=prodRgb)))
  assert np.array_equal(ss,ps),('stats',cfa,ss,ps)
  recon.append({'cfa':cfa,'phaseNoiseMs':float(perf[0])})

# Informational host timing: compare scalar, 1A and 1B on the same 1.5 MP workload.
timings=[]
w,h=1536,1024
raw=rng.integers(500,62000,(h,w),np.uint16)
var=(15000+0.9*raw).astype(np.float32)
clip=np.zeros((h,w),np.uint8);clip[::97,::89]=1
for rep in range(2):
  a=np.empty_like(raw);b=np.empty_like(raw);c=np.empty_like(raw)
  t=time.perf_counter();assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,a.ctypes.data,8)==0
  scalarMs=(time.perf_counter()-t)*1000
  t=time.perf_counter();assert banded(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,8)==0
  oneaMs=(time.perf_counter()-t)*1000
  t=time.perf_counter();assert sym(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,c.ctypes.data,8)==0
  onebMs=(time.perf_counter()-t)*1000
  assert np.array_equal(a,b) and np.array_equal(a,c)
  timings.append({'rep':rep,'scalarMs':scalarMs,'perf1aMs':oneaMs,'perf1bMs':onebMs})

receipt={
 'revision':'M9PHASENOISEPERF1B_SYMMETRIC_WEIGHT_REUSE_EXACT',
 'tileRows':32,'tileCols':256,'canonicalDirections':12,'candidateDirections':24,
 'parityCases':len(cases),
 'scalarVs1aByteExact':True,
 'scalarVs1bByteExact':True,
 'structuredTileBoundaryByteExact':True,
 'reconstructRgbByteExact':True,
 'reconstructStatsExact':True,
 'allFourCfaReconstruction':True,
 'candidateAccumulationOrderChanged':False,
 'patchAccumulationOrderChanged':False,
 'rawNoiseStrengthChanged':False,
 'fullFrameWeightCacheAdded':False,
 'timings':timings,
 'scalarMedianMs':float(np.median([x['scalarMs'] for x in timings])),
 'perf1aMedianMs':float(np.median([x['perf1aMs'] for x in timings])),
 'perf1bMedianMs':float(np.median([x['perf1bMs'] for x in timings])),
 'timingInformationalOnly':True,
}
(OUT/'phasenoiseperf1b_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
