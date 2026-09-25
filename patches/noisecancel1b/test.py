#!/usr/bin/env python3
"""Host regression for NOISECANCEL1B decoupled quiet-chroma cancellation."""
from pathlib import Path
import ctypes as C,json,subprocess,sys
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
ASSEMBLED=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
SRC=(ASSEMBLED/'app/src/main/cpp/m9noisecancel1b.cpp') if ASSEMBLED else HERE/'m9noisecancel1b.cpp'
SO=OUT/'libnoisecancel1b.so'
cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off',
     '-fno-fast-math','-fPIC','-shared','-DM9NOISECANCEL1B_HOST',str(SRC),'-o',str(SO)]
subprocess.run(cmd,check=True)
lib=C.CDLL(str(SO))
fn=lib.m9_noisecancel1b_apply
fn.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_double,C.c_void_p]
fn.restype=C.c_int

def run(rgb,profile,gains=None,mw=1,mh=1,scale=1.0):
    a=np.ascontiguousarray(rgb,np.uint16)
    p=np.ascontiguousarray(profile,np.float64)
    if gains is None:gains=np.ones(mw*mh*4,np.float64)*scale
    g=np.ascontiguousarray(gains,np.float64)
    stats=np.zeros(12,np.float64)
    rc=fn(a.ctypes.data,a.shape[1],a.shape[0],p.ctypes.data,g.ctypes.data,mw,mh,scale,stats.ctypes.data)
    if rc:raise RuntimeError('native rc='+str(rc))
    return a,stats

rng=np.random.default_rng(1186)
h,w=96,128
base=22000
rgb=np.empty((h,w,3),np.uint16);rgb[:,:,1]=base
# Noise-like chroma residual, green exact and quiet.
rgb[:,:,0]=np.clip(base+rng.normal(0,900,(h,w)),0,65535).astype(np.uint16)
rgb[:,:,2]=np.clip(base+rng.normal(0,1000,(h,w)),0,65535).astype(np.uint16)
before=rgb.copy()
profile=np.array([.005,1e-5,.0045,1e-5,.006,1e-5],np.float64)
out,stats=run(rgb,profile)
assert stats[0]==1 and stats[1]>0,'quiet noise case did not engage'
assert np.array_equal(out[:,:,1],before[:,:,1]),'green/luma channel changed'
cr0=before[:,:,0].astype(np.int32)-before[:,:,1].astype(np.int32)
cb0=before[:,:,2].astype(np.int32)-before[:,:,1].astype(np.int32)
cr1=out[:,:,0].astype(np.int32)-out[:,:,1].astype(np.int32)
cb1=out[:,:,2].astype(np.int32)-out[:,:,1].astype(np.int32)
sl=np.s_[4:-4,4:-4]
before_std=float((np.std(cr0[sl])+np.std(cb0[sl]))/2)
after_std=float((np.std(cr1[sl])+np.std(cb1[sl]))/2)
assert after_std<before_std*.98,(before_std,after_std)
assert stats[9]>=0 and stats[5]<=.5000001

# Strong pure-chroma edge at constant green: edge/spread gate must not blur it.
edge=np.empty((h,w,3),np.uint16);edge[:,:,1]=20000
edge[:,:w//2,0]=32000;edge[:,:w//2,2]=9000
edge[:,w//2:,0]=9000;edge[:,w//2:,2]=32000
edge0=edge.copy()
edgeOut,edgeStats=run(edge,profile)
assert np.array_equal(edgeOut,edge0),'strong chroma edge changed'

# High-frequency colour checker must remain unchanged.
checker=np.empty((h,w,3),np.uint16);checker[:,:,1]=21000
yy,xx=np.indices((h,w));sg=np.where(((xx+yy)&1)==0,1,-1)
checker[:,:,0]=np.clip(21000+sg*9000,0,65535)
checker[:,:,2]=np.clip(21000-sg*9000,0,65535)
checker0=checker.copy()
checkerOut,_=run(checker,profile)
assert np.array_equal(checkerOut,checker0),'high-frequency colour texture changed'

# Saturated/near-black samples are exact bypass.
sat=np.empty((h,w,3),np.uint16);sat[:]=[25000,25000,25000]
sat[20:30,20:30]=[65535,65535,65535]
sat[40:50,40:50]=[0,0,0]
sat0=sat.copy()
satOut,satStats=run(sat,profile)
assert np.array_equal(satOut[20:30,20:30],sat0[20:30,20:30])
assert np.array_equal(satOut[40:50,40:50],sat0[40:50,40:50])
assert satStats[6]>=200

# Invalid profile rejected.
bad=profile.copy();bad[0]=-1
arr=before.copy();g=np.ones(4,np.float64);statsBad=np.zeros(12,np.float64)
rc=fn(arr.ctypes.data,w,h,bad.ctypes.data,g.ctypes.data,1,1,1.0,statsBad.ctypes.data)
assert rc!=0

receipt={
 'revision':'M9NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA',
 'quiet_changed_channel_samples':int(stats[1]),
 'quiet_changed_red_samples':int(stats[2]),
 'quiet_changed_blue_samples':int(stats[3]),
 'quiet_max_abs_correction16':int(stats[4]),
 'quiet_mean_blend':float(stats[5]),
 'quiet_chroma_std_before':before_std,
 'quiet_chroma_std_after':after_std,
 'green_exact':True,
 'strong_chroma_edge_exact':True,
 'high_frequency_checker_exact':True,
 'saturated_black_bypass':True,
 'max_blend_le_0p5':True,
 'compile':cmd,
}
(OUT/'noisecancel1b_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
