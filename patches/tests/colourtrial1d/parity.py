"""Exact final-camera RGB parity including the frozen original-RAW MHC border."""
from pathlib import Path
import sys,ctypes as C,json,importlib.util
import numpy as np
spec=importlib.util.spec_from_file_location('base',Path(__file__).resolve().parents[1]/'colourtrial1c/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a,b=[m.configure(C.CDLL(str(Path(x).resolve()))) for x in sys.argv[1:3]]
rng=np.random.default_rng(91866);checks=[]
for w,h in [(64,64),(65,67),(127,128),(128,129),(129,255),(258,256),(255,257),(257,511),(385,513),(64,1025)]:
 raw=rng.integers(0,65536,(h,w),np.uint16);v=np.full((h,w),30000,np.float32);mask=(raw>65000).astype(np.uint8)
 for cfa in range(4):
  for noise in [False,True]:
   outs=[]
   for lib,workers in [(a,1),(b,8)]:
    out=np.empty((h,w,3),np.uint16);stats=np.empty(4,float)
    rc=lib.trial_reconstruct(raw.ctypes.data,v.ctypes.data if noise else None,mask.ctypes.data if noise else None,w,h,cfa,.37,.61,1.7,out.ctypes.data,workers,stats.ctypes.data)
    assert rc==0,rc
    lib.trial_border(raw.ctypes.data,w,h,cfa,.37,.61,out.ctypes.data)
    outs.append(out)
   assert np.array_equal(*outs), (w,h,cfa,noise,int(np.count_nonzero(outs[0]!=outs[1])))
   checks.append([w,h,cfa,noise])
print(json.dumps({'exact_camera_parity_cases':len(checks),'old_workers':1,'new_workers':8,'dimensions':checks[::8]}))
