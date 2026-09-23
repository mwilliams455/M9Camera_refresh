from pathlib import Path
import sys,ctypes as C,importlib.util,json
import numpy as np
spec=importlib.util.spec_from_file_location('base',Path(__file__).resolve().parents[1]/'colourtrial1c/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=Path(sys.argv[1]);lib=m.configure(C.CDLL(str(Path(sys.argv[2]).resolve())))
lib.trial_prepare_inplace.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_double,C.c_int]
rng=np.random.default_rng(82322);curve=np.frombuffer((root/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).copy()
ctx=np.r_[np.ones(3),np.array([[1.1,-.06,-.04],[-.07,1.11,-.04],[-.03,-.07,1.10]]).ravel(),np.tile(np.eye(3).ravel(),4)].astype(float)
c=lib.trial_context(ctx.ctypes.data,curve.ctypes.data);cases=0
for w,h in [(1,1),(1,9),(3,3),(129,385),(130,257),(4096,3072)]:
 raw=rng.integers(0,65536,(h,w,3),np.uint16);expected=np.empty_like(raw)
 assert lib.trial_prepare(c,raw.ctypes.data,w,h,2**.5,expected.ctypes.data,128)==0
 for band in ([2,31,128,384,h] if h<1000 else [128]):
  if band<2:continue
  got=raw.copy();assert lib.trial_prepare_inplace(c,got.ctypes.data,w,h,2**.5,band)==0
  assert np.array_equal(got,expected),(w,h,band)
  cases+=1
lib.trial_destroy(c);print(json.dumps({'in_place_exact_Q14_cases':cases,'includes_12MP':True}))
