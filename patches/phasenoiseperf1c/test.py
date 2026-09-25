#!/usr/bin/env python3
"""Exact parity + adaptive dirty-tile timing for PHASENOISEPERF1C."""
from pathlib import Path
import ctypes as C,importlib.util,json,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('PHASENOISEPERF1C_TESTS')
OUT.mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('base',REPO/'patches/tests/colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=REPO/'patches/tests/colourtrial1d'
so,_=m.build(ROOT,OUT)
lib=m.configure(C.CDLL(str(so)))
P=C.c_void_p;I=C.c_int
oneb=lib.phase_noise_symtile_exact
oneb.argtypes=[P,P,P,I,I,P,I];oneb.restype=I
onec=lib.phase_noise_symtile_adaptive_exact
onec.argtypes=[P,P,P,I,I,P,I];onec.restype=I
banded=lib.phase_noise_banded_exact
banded.argtypes=[P,P,P,I,I,P,I];banded.restype=I
lib.m9_phasenoiseperf1c_outer_tile_rows.argtypes=[];lib.m9_phasenoiseperf1c_outer_tile_rows.restype=I
lib.m9_phasenoiseperf1c_outer_tile_cols.argtypes=[];lib.m9_phasenoiseperf1c_outer_tile_cols.restype=I
lib.m9_phasenoiseperf1c_dirty_subtile_cols.argtypes=[];lib.m9_phasenoiseperf1c_dirty_subtile_cols.restype=I
lib.trial_reconstruct.argtypes=[P,P,P,I,I,I,C.c_double,C.c_double,C.c_double,P,I,P]
lib.trial_reconstruct.restype=I
lib.trial_reconstruct_perf.argtypes=[P,P,P,I,I,I,C.c_double,C.c_double,C.c_double,P,I,P,P]
lib.trial_reconstruct_perf.restype=I
assert lib.m9_phasenoiseperf1c_outer_tile_rows()==64
assert lib.m9_phasenoiseperf1c_outer_tile_cols()==512
assert lib.m9_phasenoiseperf1c_dirty_subtile_cols()==128

rng=np.random.default_rng(193)
cases=[]

# Broad exactness matrix, including clipped and invalid variance samples.
for w,h in [(16,16),(31,37),(65,67),(129,131),(257,193),(513,257),(641,513),(1031,777)]:
    raw=rng.integers(0,65536,(h,w),np.uint16)
    var=np.exp(rng.uniform(np.log(20.0),np.log(180000.0),(h,w))).astype(np.float32)
    clip=np.zeros((h,w),np.uint8)
    if h>20 and w>20:
        clip[7::23,9::29]=1
        var[8::31,11::37]=0
    for workers in [1,2,4,8]:
        scalar=np.empty_like(raw);b=np.empty_like(raw);c=np.empty_like(raw)
        assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,scalar.ctypes.data,workers)==0
        assert oneb(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,workers)==0
        assert onec(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,c.ctypes.data,workers)==0
        assert np.array_equal(scalar,b),(w,h,workers,'1b')
        assert np.array_equal(scalar,c),(w,h,workers,'1c',int(np.count_nonzero(scalar!=c)))
        cases.append({'w':w,'h':h,'workers':workers})

# Stress both outer 512-column and dirty 128-column boundaries.
w,h=1547,839
yy,xx=np.indices((h,w))
raw=np.clip(10000+13*xx+7*yy+3100*np.sin(xx/11.0)+2200*np.cos(yy/17.0)+rng.normal(0,850,(h,w)),0,65535).astype(np.uint16)
var=(9000+0.82*raw).astype(np.float32)
clip=np.zeros((h,w),np.uint8)
for x in [127,128,129,255,256,257,511,512,513,639,640,641,1023,1024,1025]: clip[100:135,x]=1
for y in [63,64,65,127,128,129,767,768]: clip[y,300:350]=1
var[400:430,800:850]=0
scalar=np.empty_like(raw);b=np.empty_like(raw);c=np.empty_like(raw)
assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,scalar.ctypes.data,8)==0
assert oneb(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,b.ctypes.data,8)==0
assert onec(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,w,h,c.ctypes.data,8)==0
assert np.array_equal(scalar,b)
assert np.array_equal(scalar,c),('adaptive seams',int(np.count_nonzero(scalar!=c)))

def timed_case(label,raw,var,clip,reps=3):
    out=[]
    for rep in range(reps):
        b=np.empty_like(raw);c=np.empty_like(raw)
        t=time.perf_counter();assert oneb(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,raw.shape[1],raw.shape[0],b.ctypes.data,8)==0
        bms=(time.perf_counter()-t)*1000
        t=time.perf_counter();assert onec(raw.ctypes.data,var.ctypes.data,clip.ctypes.data,raw.shape[1],raw.shape[0],c.ctypes.data,8)==0
        cms=(time.perf_counter()-t)*1000
        assert np.array_equal(b,c),(label,rep,int(np.count_nonzero(b!=c)))
        out.append({'rep':rep,'symtile1bMs':bms,'adaptive1cMs':cms})
    return {'label':label,'runs':out,
            'symtile1bMedianMs':float(np.median([x['symtile1bMs'] for x in out])),
            'adaptive1cMedianMs':float(np.median([x['adaptive1cMs'] for x in out]))}

# 12 MP hard parity and timing: clean, clustered highlights, and sparse censoring.
w,h=4096,3072
raw=rng.integers(900,61000,(h,w),np.uint16)
var=(12000.0+0.8*raw.astype(np.float32)).astype(np.float32)

clip_clean=np.zeros((h,w),np.uint8)
t12_clean=timed_case('12mp_clean',raw,var,clip_clean,2)

clip_cluster=np.zeros((h,w),np.uint8)
# Synthetic localized bright-window/highlight geometry, deliberately not derived
# from any private photograph.
clip_cluster[220:1080,2700:4050]=1
clip_cluster[1760:2210,80:920]=1
clip_cluster[2420:2760,3150:3920]=1
t12_cluster=timed_case('12mp_clustered_censor',raw,var,clip_cluster,2)

clip_sparse=np.zeros((h,w),np.uint8);clip_sparse[::211,::223]=1
t12_sparse=timed_case('12mp_sparse_censor',raw,var,clip_sparse,2)

# Direct scalar parity for one production-size clustered case.
scalar12=np.empty_like(raw);c12=np.empty_like(raw)
assert lib.phase_noise(raw.ctypes.data,var.ctypes.data,clip_cluster.ctypes.data,w,h,scalar12.ctypes.data,8)==0
assert onec(raw.ctypes.data,var.ctypes.data,clip_cluster.ctypes.data,w,h,c12.ctypes.data,8)==0
assert np.array_equal(scalar12,c12),('12mp-scalar-vs-1c',int(np.count_nonzero(scalar12!=c12)))
del scalar12,c12

# End-to-end reconstruction exactness across all CFA layouts. Production perf
# reconstruction is expected to route through 1C.
recon=[]
for cfa in range(4):
    w2,h2=385,321
    rr=rng.integers(900,61000,(h2,w2),np.uint16)
    vv=np.exp(rng.uniform(np.log(100.0),np.log(90000.0),(h2,w2))).astype(np.float32)
    cc=np.zeros((h2,w2),np.uint8);cc[30:70,80:125]=1
    scalar=np.empty((h2,w2,3),np.uint16);prod=np.empty_like(scalar)
    ss=np.zeros(4,np.float64);ps=np.zeros(4,np.float64);perf=np.zeros(5,np.float64)
    assert lib.trial_reconstruct(rr.ctypes.data,vv.ctypes.data,cc.ctypes.data,w2,h2,cfa,.42,.61,1.7,
        scalar.ctypes.data,8,ss.ctypes.data)==0
    assert lib.trial_reconstruct_perf(rr.ctypes.data,vv.ctypes.data,cc.ctypes.data,w2,h2,cfa,.42,.61,1.7,
        prod.ctypes.data,8,ps.ctypes.data,perf.ctypes.data)==0
    assert np.array_equal(scalar,prod),('reconstruct',cfa,int(np.count_nonzero(scalar!=prod)))
    assert np.array_equal(ss,ps),('stats',cfa,ss,ps)
    recon.append({'cfa':cfa,'phaseNoiseMs':float(perf[0])})

receipt={
 'revision':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT',
 'outerTileRows':64,'outerTileCols':512,'dirtySubtileCols':128,
 'parityCases':len(cases),
 'scalarVs1bByteExact':True,
 'scalarVs1cByteExact':True,
 'outerAndSubtileSeamsByteExact':True,
 'twelveMpClusteredScalarByteExact':True,
 'reconstructRgbByteExact':True,
 'reconstructStatsExact':True,
 'allFourCfaReconstruction':True,
 'timingCases':[t12_clean,t12_cluster,t12_sparse],
 'candidateAccumulationOrderChanged':False,
 'patchAccumulationOrderChanged':False,
 'rawNoiseStrengthChanged':False,
 'fullFrameWeightCacheAdded':False,
 'photographicMathChanged':False,
 'timingInformationalOnly':True,
}
(OUT/'phasenoiseperf1c_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
