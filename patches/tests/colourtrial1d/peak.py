"""Isolated-process 12MP native working-set comparison; not an Android RSS claim."""
from pathlib import Path
import sys,ctypes as C,importlib.util,resource,time,hashlib,json
import numpy as np
spec=importlib.util.spec_from_file_location('base',Path(__file__).resolve().parents[1]/'colourtrial1c/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=Path(sys.argv[1]);lib=m.configure(C.CDLL(str(Path(sys.argv[2]).resolve())));start=time.monotonic();w,h=4096,3072
raw=np.empty((h,w),np.uint16)
for y in range(h):raw[y]=((np.arange(w,dtype=np.uint32)*2719+y*3923+32768)%65536).astype(np.uint16)
v=np.full((h,w),30000,np.float32);mask=np.zeros((h,w),np.uint8);out=np.empty((h,w,3),np.uint16);stats=np.empty(4,float)
assert lib.trial_reconstruct(raw.ctypes.data,v.ctypes.data,mask.ctypes.data,w,h,0,.37,.61,1.7,out.ctypes.data,8,stats.ctypes.data)==0
lib.trial_border(raw.ctypes.data,w,h,0,.37,.61,out.ctypes.data);cameraHash=hashlib.sha256(memoryview(out)).hexdigest()
del raw,v,mask
curve=np.frombuffer((root/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).copy();a=np.r_[np.ones(3),np.tile(np.eye(3).ravel(),5)].astype(float);ctx=lib.trial_context(a.ctypes.data,curve.ctypes.data)
if hasattr(lib,'trial_prepare_inplace'):
 lib.trial_prepare_inplace.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_double,C.c_int];assert lib.trial_prepare_inplace(ctx,out.ctypes.data,w,h,2**.5,128)==0;q=out
else:
 q=np.empty_like(out);assert lib.trial_prepare(ctx,out.ctypes.data,w,h,2**.5,q.ctypes.data,128)==0
qhash=hashlib.sha256(memoryview(q)).hexdigest();lib.trial_destroy(ctx)
print(json.dumps({'dimensions':[w,h],'workers':8,'camera16_sha256':cameraHash,'Q14_sha256':qhash,'host_peak_rss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_s':time.monotonic()-start}))
