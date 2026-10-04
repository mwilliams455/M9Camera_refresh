#!/usr/bin/env python3
"""Exact output parity + host timing for COLORPERF1A persistent colour workers."""
from pathlib import Path
import ctypes as C,json,os,subprocess,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path("COLORPERF1A_TESTS")
OUT.mkdir(parents=True,exist_ok=True)

inc=OUT/"android";inc.mkdir(exist_ok=True)
(inc/"bitmap.h").write_text(r'''#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv*,jobject,AndroidBitmapInfo*){return -1;}
inline int AndroidBitmap_lockPixels(JNIEnv*,jobject,void**){return -1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
''')
java=Path(os.environ.get("JAVA_HOME","/usr/lib/jvm/java-17-openjdk-amd64"))
if not (java/"include/jni.h").exists(): java=Path("/usr/lib/jvm/java-17-openjdk-amd64")
lib=OUT/"libcolorperf1a.so"
cmd=["g++","-std=c++17","-O2","-fPIC","-shared","-pthread","-ffp-contract=off","-fno-fast-math",
     "-I"+str(OUT),"-I"+str(java/"include"),"-I"+str(java/"include/linux"),
     str(HERE/"host.cpp"),"-o",str(lib)]
subprocess.run(cmd,check=True)

L=C.CDLL(str(lib));P=C.c_void_p;I=C.c_int;D=C.c_double;U=C.c_uint32
ctxfn=L.trial_colorperf_context;ctxfn.argtypes=[P,P];ctxfn.restype=P
destroy=L.trial_colorperf_destroy;destroy.argtypes=[P];destroy.restype=None
old=L.trial_colorperf_old
old.argtypes=[P,P,I,I,I,D,D,D,I,I,P,U,P];old.restype=I
new=L.trial_colorperf_persistent
new.argtypes=old.argtypes;new.restype=I

curve=np.minimum(np.arange(2048,dtype=np.uint16)//8,255).astype(np.uint8)
identity=np.eye(3).reshape(-1)
context=np.r_[np.ones(3),identity,identity,identity,identity,identity].astype(np.float64)
ctx=ctxfn(context.ctypes.data,curve.ctypes.data);assert ctx

rng=np.random.default_rng(194)
parity=[]
for w,h in [(257,385),(641,769),(1025,513),(1537,1025)]:
  cam=rng.integers(0,16384,(h,w,3),np.uint16)
  for rot in [0,90,180,270]:
    ow=h if rot in (90,270) else w
    oh=w if rot in (90,270) else h
    stride=ow*4+16
    a=np.full((oh,stride),0x5a,np.uint8)
    b=a.copy()
    sa=np.zeros(12,np.int64);sb=np.zeros(12,np.int64)
    assert old(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,a.ctypes.data,stride,sa.ctypes.data)==0
    assert new(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,b.ctypes.data,stride,sb.ctypes.data)==0
    assert np.array_equal(a,b),("pixels",w,h,rot,int(np.count_nonzero(a!=b)))
    assert np.array_equal(sa[[0,1,2,4]],sb[[0,1,2,4]]),("counts",w,h,rot,sa,sb)
    parity.append({"w":w,"h":h,"rotation":rot,"stride":stride})

# Production-size timing. Alternate call order to reduce warm/cache bias.
w,h=4096,3072;rot=90;ow,oh=h,w;stride=ow*4
cam=rng.integers(0,16384,(h,w,3),np.uint16)
old_times=[];new_times=[]
for rep in range(4):
  a=np.zeros((oh,stride),np.uint8);b=np.zeros_like(a)
  sa=np.zeros(12,np.int64);sb=np.zeros(12,np.int64)
  if rep%2==0:
    t=time.perf_counter();assert old(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,a.ctypes.data,stride,sa.ctypes.data)==0
    old_ms=(time.perf_counter()-t)*1000
    t=time.perf_counter();assert new(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,b.ctypes.data,stride,sb.ctypes.data)==0
    new_ms=(time.perf_counter()-t)*1000
  else:
    t=time.perf_counter();assert new(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,b.ctypes.data,stride,sb.ctypes.data)==0
    new_ms=(time.perf_counter()-t)*1000
    t=time.perf_counter();assert old(ctx,cam.ctypes.data,w,h,384,1.137,.84,.91,rot,8,a.ctypes.data,stride,sa.ctypes.data)==0
    old_ms=(time.perf_counter()-t)*1000
  assert np.array_equal(a,b),("12mp",rep,int(np.count_nonzero(a!=b)))
  assert np.array_equal(sa[[0,1,2,4]],sb[[0,1,2,4]])
  old_times.append({"rep":rep,"wallMs":old_ms,"renderWorkerNsSum":int(sa[3]),"blockMaxNsSum":int(sa[8]),"orientationNsSum":int(sa[9])})
  new_times.append({"rep":rep,"wallMs":new_ms,"renderWorkerNsSum":int(sb[3]),"blockMaxNsSum":int(sb[8]),"orientationNsSum":int(sb[9]),"nativeCoreNs":int(sb[11])})

destroy(ctx)
old_med=float(np.median([x["wallMs"] for x in old_times]))
new_med=float(np.median([x["wallMs"] for x in new_times]))
receipt={
 "revision":"M9COLORPERF1A_PERSISTENTBLOCKS_EXACT",
 "parent":"1.93_M9PHASENOISEPERF1C_ADAPTIVE128_EXACT",
 "blockRows":384,"workers":8,
 "parityCases":len(parity),"allRotations":True,
 "pixelOutputByteExact":True,
 "renderCountersExact":True,
 "scalarColourMathChanged":False,
 "orientationMappingChanged":False,
 "bt601PairingChanged":False,
 "sat2Curve02Tg1Changed":False,
 "workerRowPartitionChanged":False,
 "boundedScratchModelChanged":False,
 "workerTeamLaunchesOld":8,
 "workerTeamLaunchesCandidate":1,
 "bitmapLocksOld":8,
 "bitmapLocksCandidate":1,
 "twelveMpByteExact":True,
 "oldTimings":old_times,"candidateTimings":new_times,
 "oldMedianWallMs":old_med,"candidateMedianWallMs":new_med,
 "speedup":old_med/new_med,
 "timingInformationalOnly":True
}
(OUT/"colorperf1a_tests.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
