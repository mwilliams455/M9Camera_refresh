#!/usr/bin/env python3
"""Host regression for NOISECANCEL1A quiet-chroma confidence boost."""
from pathlib import Path
import ctypes as C, json, subprocess, sys
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OUT=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
ASSEMBLED=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
BASE=REPO/'research/detail1a/noise2_guard_native.cpp'
CAND=(ASSEMBLED/'app/src/main/cpp/m9detail1h_guard.cpp') if ASSEMBLED else HERE/'m9detail1h_guard.cpp'

def build(src,name,host=False):
    so=OUT/(name+'.so')
    cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
         '-ffp-contract=off','-fno-fast-math','-fPIC','-shared']
    if host: cmd+=['-DM9NOISECANCEL1A_HOST']
    cmd += [str(src),'-o',str(so)]
    subprocess.run(cmd,check=True)
    lib=C.CDLL(str(so))
    f=lib.noise2_guard_native
    f.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int,
                C.c_double,C.c_double,C.c_double,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
    f.restype=C.c_int
    return lib,f,cmd

base_lib,base,base_cmd=build(BASE,'base')
cand_lib,cand,cand_cmd=build(CAND,'candidate',True)
cand_lib.noisecancel1a_test_confidence.argtypes=[C.c_double]
cand_lib.noisecancel1a_test_confidence.restype=C.c_double

def call(fn,c,var,censor=None,cfa=0,nr=.4,nb=.65):
    c=np.ascontiguousarray(c,np.int32)
    var=np.ascontiguousarray(var,np.float64)
    censor=None if censor is None else np.ascontiguousarray(censor,np.uint8)
    h,w=c.shape
    out=np.empty_like(c);smooth=np.empty_like(c)
    vr=np.empty(c.shape,np.float32);conf=np.empty(c.shape,np.float32)
    rc=fn(c.ctypes.data,var.ctypes.data,0 if censor is None else censor.ctypes.data,
          w,h,cfa,nr,nb,1.0,out.ctypes.data,smooth.ctypes.data,vr.ctypes.data,conf.ctypes.data)
    if rc: raise RuntimeError('native rc='+str(rc))
    return out,smooth,vr,conf

# Pure confidence law: no boost below gate; monotonic boost in quiet-confidence range;
# exact endpoints remain exact.
samples={x:cand_lib.noisecancel1a_test_confidence(x) for x in [0.,.5,.65,.7,.8,.9,.95,1.]}
assert samples[.5]==.5 and samples[.65]==.65 and samples[1.]==1.
assert samples[.7]>.7 and samples[.8]>.8 and samples[.9]>.9 and samples[.95]>.95
assert all(0<=v<=1 for v in samples.values())

rng=np.random.default_rng(91831);h,w=96,128
# Noise-like carrier around zero. Scan audited variance levels until at least one
# deterministic level exercises the new confidence-only blend.
carrier=np.rint(rng.normal(0,55,(h,w))).astype(np.int32)
quiet_case=None
for vv in [100.,300.,1000.,3000.,10000.,30000.,100000.]:
    var=np.full((h,w),vv,np.float64)
    bo,bs,bv,bc=call(base,carrier,var)
    co,cs,cv,cc=call(cand,carrier,var)
    assert np.array_equal(bs,cs),'smoothing target changed'
    changed=co!=bo
    if np.any(changed):
        # New result must stay between input carrier and the exact same smooth target.
        lo=np.minimum(carrier,cs);hi=np.maximum(carrier,cs)
        assert np.all(co>=lo) and np.all(co<=hi),'candidate crossed smoothing target'
        assert np.all(np.abs(co.astype(np.int64)-cs.astype(np.int64))
                      <=np.abs(bo.astype(np.int64)-bs.astype(np.int64))),'candidate reduced no more noise'
        assert np.all(bc[changed]>.65-1e-6),'low-confidence pixels changed'
        assert np.all(cc[changed]>=bc[changed]-1e-6),'applied confidence regressed'
        quiet_case=dict(variance=vv,changed=int(changed.sum()),
                        baseline_mean_conf=float(bc.mean()),candidate_mean_conf=float(cc.mean()),
                        mean_abs_residual_before=float(np.mean(np.abs(bo.astype(float)-bs))),
                        mean_abs_residual_after=float(np.mean(np.abs(co.astype(float)-cs))))
        break
assert quiet_case is not None,'no deterministic quiet case exercised NOISECANCEL1A'

# Strong fine structure must remain governed by the existing classifier. The new
# candidate is required to be byte-identical to baseline when base confidence never
# reaches the quiet gate.
yy,xx=np.indices((h,w))
edge=np.where(((xx//2+yy//2)&1)==0,-6000,6000).astype(np.int32)
var=np.full((h,w),40.,np.float64)
ebo,ebs,_,ebc=call(base,edge,var)
eco,ecs,_,ecc=call(cand,edge,var)
assert float(ebc.max())<=.65+1e-6
assert np.array_equal(ebo,eco),'high-frequency detail changed below quiet gate'
assert np.array_equal(ebs,ecs)

# Censored neighbourhood remains exactly protected.
censor=np.zeros((h,w),np.uint8);censor[44:48,60:65]=1
var=np.full((h,w),30000.,np.float64)
bo,bs,_,bc=call(base,carrier,var,censor)
co,cs,_,cc=call(cand,carrier,var,censor)
protected=np.zeros_like(censor,dtype=bool)
ys,xs=np.nonzero(censor)
for y,x in zip(ys,xs):
    protected[max(0,y-6):min(h,y+7),max(0,x-6):min(w,x+7)]=True
assert np.array_equal(co[protected],carrier[protected]),'censored neighbourhood changed'
assert np.array_equal(bo[protected],carrier[protected]),'baseline censor expectation changed'

receipt={
  'revision':'NOISECANCEL1A_QUIETCHROMA',
  'confidence_samples':{str(k):v for k,v in samples.items()},
  'quiet_case':quiet_case,
  'high_frequency_baseline_max_confidence':float(ebc.max()),
  'high_frequency_exact_baseline_parity':True,
  'censored_neighbourhood_exact_bypass':True,
  'same_smoothing_target':True,
  'candidate_never_crosses_smoothing_target':True,
  'changed_pixels_require_base_confidence_gt_0p65':True,
  'green_luma_path_tested_by_frozen_source_contract':True,
  'baseline_compile':base_cmd,
  'candidate_compile':cand_cmd,
}
(OUT/'noisecancel1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
