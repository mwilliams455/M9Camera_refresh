"""Host access to the exact tiled/JNI compilation unit shipped by DETAIL1H."""
from pathlib import Path
import ctypes as C
import subprocess,struct
import numpy as np
import tifffile
from inputs import read

class TiledDetail:
    def __init__(self,build):
        build=Path(build);build.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
        so=build/'detail1h.so'
        subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-ffp-contract=off','-fno-fast-math',
            '-DM9DETAIL1H_HOST','-fPIC','-shared',str(repo/'patches/m9detail1h/m9detail1h.cpp'),
            str(Path(__file__).with_name('rb_domain.cpp')),str(Path(__file__).with_name('noise2_guard_native.cpp')),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()))
        self.lib.detail1h_host.argtypes=[C.c_void_p]*2+[C.c_int]*4+[C.c_void_p,C.c_int]+[C.c_void_p]*2+[C.c_int]*2+[C.c_double]*3+[C.c_int]*2+[C.c_void_p]*2
        self.lib.detail1h_host.restype=C.c_int
        self.lib.detail1h_variance.argtypes=[C.c_void_p]+[C.c_int]*4+[C.c_void_p,C.c_int]+[C.c_void_p]*2+[C.c_int]*2+[C.c_double]+[C.c_int]*2
        self.lib.detail1h_variance.restype=C.c_double

    def apply(self,norm,sensor,base,cfa,nr,nb,black,white,profile,gains,scale,tile=256,guard=True,origin_y=0):
        arrays=[np.ascontiguousarray(x,dtype=t) for x,t in [(norm,np.uint16),(sensor,np.uint16),(black,np.float32),
                (profile,np.float64),(gains,np.float64)]]
        n,s,b,p,g=arrays;h,w=n.shape;mh,mw,ch=g.shape;out=np.array(base,dtype=np.uint16,copy=True,order='C');stats=np.zeros(10,np.float64)
        assert s.shape==n.shape and out.shape==(h,w,3) and b.shape==(4,) and p.shape==(6,) and ch==4
        rc=self.lib.detail1h_host(n.ctypes.data,s.ctypes.data,w,h,cfa,origin_y,b.ctypes.data,white,p.ctypes.data,g.ctypes.data,mw,mh,
            scale,nr,nb,tile,int(guard),out.ctypes.data,stats.ctypes.data)
        if rc:raise ValueError('DETAIL1H native status '+str(rc))
        return out,dict(zip(['status','tiles','supported_rb_samples','changed_carrier_samples','max_abs_correction',
            'censored_samples','mean_confidence','mean_residual_variance14','scratch_budget_bytes','elapsed_ms'],stats.tolist()))

def dng_inputs(path):
    norm,meta,noise=read(path,with_noise=True)
    with tifffile.TiffFile(path) as tf:
        pg=tf.pages[0];sensor=pg.asarray();op=pg.tags[51009].value;pos=4;planes={}
        for _ in range(struct.unpack_from('>I',op)[0]):
            _,_,_,length=struct.unpack_from('>4I',op,pos);pos+=16;data=op[pos:pos+length];pos+=length
            f=struct.unpack_from('>10I4dI',data);y,x=f[:2];mh,mw=f[8:10]
            rawgrid=np.frombuffer(data,dtype='>f4',offset=76).astype(np.float64).reshape(mh,mw)
            colour=meta['cfa_pattern'][2*y+x];semantic=0 if colour==0 else 3 if colour==2 else 1+y
            planes[semantic]=rawgrid
    grid=np.stack([planes[i] for i in range(4)],axis=-1)
    common=np.exp(np.log(grid).sum(axis=2)*.25)
    gains=grid/common[:,:,None]*np.exp(meta['norm030_alpha']*np.log(common))[:,:,None]
    return norm,meta,noise,sensor,gains
