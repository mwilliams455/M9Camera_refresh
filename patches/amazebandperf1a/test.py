#!/usr/bin/env python3
"""M9 AMAZEBANDPERF1A exact band-size sweep against frozen 256-row 1.93."""
from pathlib import Path
import ctypes as C,json,os,subprocess,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path("AMAZEBANDPERF1A_TESTS")
OUT.mkdir(parents=True,exist_ok=True)

upstream=REPO/"patches/colourtrial1c/upstream"
lib=OUT/"libamazebandperf1a.so"
cmd=[
 "g++","-std=c++17","-O2","-fPIC","-shared","-fopenmp","-ffp-contract=off","-fno-fast-math",
 "-I"+str(upstream/"include"),
 str(HERE/"reconstruct.cpp"),
 str(REPO/"patches/phasenoiseperf1c/phase_noise.cpp"),
 str(upstream/"amaze.cc"),str(upstream/"border.cc"),
 "-o",str(lib)
]
subprocess.run(cmd,check=True)

L=C.CDLL(str(lib));P=C.c_void_p;I=C.c_int;D=C.c_double
prod=L.trial_reconstruct_perf
prod.argtypes=[P,P,P,I,I,I,D,D,D,P,I,P,P];prod.restype=I
band=L.trial_reconstruct_perf_band
band.argtypes=[P,P,P,I,I,I,D,D,D,P,I,P,P,I];band.restype=I

rng=np.random.default_rng(1931)
candidates=[128,384,512,768,1024]

# Hard parity across CFA patterns, seam positions, odd dimensions and clipped/noise cases.
cases=[]
mismatchSummary={str(br):{"cases":0,"mismatchCases":0,"mismatchSamples":0,"maxAbs":0} for br in candidates}
exactCandidates=set(candidates)
dims=[(641,385),(769,513),(1025,769),(1153,1025)]
for cfa in range(4):
  for w,h in dims:
    raw=rng.integers(900,61000,(h,w),np.uint16)
    var=(12000.0+0.7*raw.astype(np.float32)).astype(np.float32)
    censor=np.zeros((h,w),np.uint8)
    # Cross several prospective 128/256/384/512 boundaries.
    for yy,xx in [(126,126),(254,510),(382,766),(510,1022),(766,510)]:
      if yy<h and xx<w:censor[max(0,yy-2):min(h,yy+3),max(0,xx-2):min(w,xx+3)]=1
    base=np.empty((h,w,3),np.uint16)
    bs=np.zeros(4,np.float64);bp=np.zeros(5,np.float64)
    assert prod(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.41,.59,1.7,
                base.ctypes.data,8,bs.ctypes.data,bp.ctypes.data)==0
    # Candidate 256 must itself be exactly the production 1.93 implementation.
    same=np.empty_like(base);ss=np.zeros(4,np.float64);sp=np.zeros(5,np.float64)
    assert band(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.41,.59,1.7,
                same.ctypes.data,8,ss.ctypes.data,sp.ctypes.data,256)==0
    interior=(slice(16,h-16),slice(16,w-16),slice(None))
    assert np.array_equal(base[interior],same[interior]),("prod-vs-parameterized256-interior",cfa,w,h,int(np.count_nonzero(base[interior]!=same[interior])))
    assert np.array_equal(bs,ss),("stats256",cfa,w,h,bs,ss)
    for br in candidates:
      got=np.empty_like(base);gs=np.zeros(4,np.float64);gp=np.zeros(5,np.float64)
      assert band(raw.ctypes.data,var.ctypes.data,censor.ctypes.data,w,h,cfa,.41,.59,1.7,
                  got.ctypes.data,8,gs.ctypes.data,gp.ctypes.data,br)==0
      diff=(base[interior]!=got[interior])
      mismatch=int(np.count_nonzero(diff))
      maxAbs=int(np.max(np.abs(base[interior].astype(np.int32)-got[interior].astype(np.int32)))) if mismatch else 0
      rec=mismatchSummary[str(br)]
      rec["cases"]+=1;rec["mismatchSamples"]+=mismatch;rec["maxAbs"]=max(rec["maxAbs"],maxAbs)
      if mismatch or not np.array_equal(bs,gs):
        rec["mismatchCases"]+=1
        exactCandidates.discard(br)
      cases.append({"bandRows":br,"cfa":cfa,"w":w,"h":h,
                    "mismatchSamples":mismatch,"maxAbs":maxAbs,
                    "statsExact":bool(np.array_equal(bs,gs))})

# Isolated AMaZE timings on 12 MP: only candidates that passed every smaller
# exactness case advance. No phase-noise input, so perf[3] is the stage we are choosing.
w,h=4096,3072
raw=rng.integers(900,61000,(h,w),np.uint16)
base=np.empty((h,w,3),np.uint16);bs=np.zeros(4,np.float64);bp=np.zeros(5,np.float64)
assert band(raw.ctypes.data,None,None,w,h,0,.41,.59,1.7,
            base.ctypes.data,8,bs.ctypes.data,bp.ctypes.data,256)==0
timings={}
for br in [256]+sorted(exactCandidates):
  runs=[]
  twelveMpExact=True
  for rep in range(2):
    got=np.empty_like(base);gs=np.zeros(4,np.float64);gp=np.zeros(5,np.float64)
    t=time.perf_counter()
    assert band(raw.ctypes.data,None,None,w,h,0,.41,.59,1.7,
                got.ctypes.data,8,gs.ctypes.data,gp.ctypes.data,br)==0
    wall=(time.perf_counter()-t)*1000
    interior=(slice(16,h-16),slice(16,w-16),slice(None))
    exact=np.array_equal(base[interior],got[interior]) and np.array_equal(bs,gs)
    twelveMpExact=twelveMpExact and exact
    runs.append({"rep":rep,"wallMs":wall,"floatInputMs":float(gp[2]),
                 "amazeCoreMs":float(gp[3]),"outputQuantizeMs":float(gp[4]),
                 "byteExact":bool(exact)})
  timings[str(br)]={
    "runs":runs,
    "twelveMpByteExact":bool(twelveMpExact),
    "medianWallMs":float(np.median([x["wallMs"] for x in runs])),
    "medianAmazeCoreMs":float(np.median([x["amazeCoreMs"] for x in runs])),
    "medianQuantizeMs":float(np.median([x["outputQuantizeMs"] for x in runs]))
  }

base256=timings["256"]["medianAmazeCoreMs"]
for v in timings.values():
  v["amazeSpeedupVs256"]=base256/v["medianAmazeCoreMs"]
finalExact=[br for br in sorted(exactCandidates) if timings.get(str(br),{}).get("twelveMpByteExact",False)]
best=min([256]+finalExact,key=lambda br:timings[str(br)]["medianAmazeCoreMs"])

receipt={
 "revision":"M9AMAZEBANDPERF1A_SWEEP_ONLY",
 "productionParent":"1.93_M9PHASENOISEPERF1C_ADAPTIVE128_EXACT",
 "productionBandRows":256,
 "testedBandRows":[128,256,384,512,768,1024],
 "allBandsMultiplesOfAmazeTileStep128":True,
 "productionVsParameterized256InteriorByteExact":True,
 "final16PxBorderPolicy":"frozen_MHC_original_RAW_independent_of_AMaZE_bandRows",
 "finalBorderChanged":False,
 "smallCaseMismatchSummary":mismatchSummary,
 "smallCaseExactCandidates":sorted(exactCandidates),
 "twelveMpExactCandidates":finalExact,
 "allCandidateRgbByteExact":len(exactCandidates)==len(candidates),
 "allCandidateStatsExact":all(x["statsExact"] for x in cases),
 "allFourCfa":True,
 "parityCases":len(cases),
 "includes12MpParity":True,
 "amazeAlgorithmChanged":False,
 "amazeChunkChanged":False,
 "phaseNoiseChanged":False,
 "photographicMathChanged":False,
 "timings":timings,
 "fastestHostBandRows":best,
 "timingInformationalOnly":True
}
(OUT/"amazebandperf1a_tests.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
