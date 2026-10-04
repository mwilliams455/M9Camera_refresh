"""DETAIL1D: align colour differences with green, without double-applying WB."""
from pathlib import Path
import ctypes as C
import subprocess
import numpy as np
from rb_probe import RbProbe,q14,q16

class DomainProbe:
    def __init__(self,build):
        build=Path(build);build.mkdir(parents=True,exist_ok=True);so=build/'rb_domain.so'
        subprocess.run(['g++','-std=c++17','-O2','-fPIC','-shared',str(Path(__file__).with_suffix('.cpp')),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()))
        self.lib.rb_domain_stages.argtypes=[C.c_void_p]+[C.c_int]*4+[C.c_double]*2+[C.c_void_p]*4
        self.lib.rb_domain_consume.argtypes=[C.c_void_p]*2+[C.c_int]*3+[C.c_double]*2+[C.c_void_p]
        self.lib.rb_domain_stages.restype=None;self.lib.rb_domain_consume.restype=None
    @staticmethod
    def validate(nr,nb):
        # All normalized raw values must fit the wider signed difference plane.
        assert all(np.isfinite(n) and n>0 and 16383*max(n,1/n) < 2**30 for n in [nr,nb]),'invalid neutral ratios'
    def stages(self,raw,cfa,nr,nb,shrink=True):
        self.validate(nr,nb);raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        arrays=[np.empty((h,w),dtype=t) for t in [np.uint16,np.int32,np.int32,np.uint16]]
        self.lib.rb_domain_stages(raw.ctypes.data,w,h,cfa,shrink,nr,nb,*[z.ctypes.data for z in arrays])
        return arrays
    def consume(self,carrier,base,cfa,nr,nb):
        self.validate(nr,nb);carrier=np.ascontiguousarray(carrier,dtype=np.int32);base=np.ascontiguousarray(base,dtype=np.uint16)
        h,w=carrier.shape;out=np.empty_like(base)
        self.lib.rb_domain_consume(carrier.ctypes.data,base.ctypes.data,w,h,cfa,nr,nb,out.ctypes.data)
        return out

def checks(probe,old):
    rng=np.random.default_rng(92127);unity=0;flat=0;headroom=0;consumer_samples=0
    for cfa in range(4):
        yy,xx=np.indices((70,74));rx=cfa in [1,3];ry=cfa in [2,3]
        r=(xx%2==rx)&(yy%2==ry);b=(xx%2!=rx)&(yy%2!=ry);g=~(r|b)
        raw=rng.integers(0,65536,(70,74),dtype=np.uint16);base=rng.integers(0,65536,(70,74,3),dtype=np.uint16)
        for shrink in [False,True]:
            a=probe.stages(raw,cfa,1.,1.,shrink);o=old.stages(raw,cfa,shrink)
            assert all(np.array_equal(x,y) for x,y in zip(a,o))
            assert np.array_equal(probe.consume(a[2],base,cfa,1.,1.),old.consume(o[2],base,cfa));unity+=1
        for nr,nb in [(.25,.5),(.4,.7),(1.5,.8),(1.,1.)]:
            for vals in [(2000,2000,2000),(13000,2000,11000),(300,12000,500)]:
                z=np.where(r,vals[0],np.where(b,vals[2],vals[1]));raw=q16(z)
                a=probe.stages(raw,cfa,nr,nb);base=np.zeros((70,74,3),np.uint16);base[...,1]=q16(a[0])
                out=q14(probe.consume(a[2],base,cfa,nr,nb))
                # Constant non-neutral colours can meet the Co gate only if uncertainty !=0; here it is zero.
                assert np.max(np.abs(out[10:-10,10:-10]-np.array(vals)))<=1;flat+=1
                if vals==(13000,2000,11000) and nr==.25:
                    assert a[1].max()>32767 and out[20,20,0]>12000;headroom+=1
        # Vectorized independent producer equations, unequal channel ratios.
        raw=rng.integers(0,65536,(70,74),dtype=np.uint16);z=q14(raw);nr,nb=.37,.61
        card=lambda a:sum(np.roll(a,s,axis=k) for k,s in [(0,-1),(0,1),(1,-1),(1,1)])
        diag=lambda a:sum(np.roll(np.roll(a,dy,0),dx,1) for dy in [-1,1] for dx in [-1,1])
        eg=np.where(g,(4*z+diag(z))//8,card(z)//4);a=np.where(g,0,card(np.where(g,np.abs(eg-z),0)))
        d=np.where(g,0,np.floor(z/np.where(r,nr,nb)+.5).astype(np.int64)-eg)
        d=np.where(np.abs(d)<a,np.sign(d)*np.maximum(np.abs(d)-a//4,0),d);ca=np.where(g,0,diag(d)//4)
        got=probe.stages(raw,cfa,nr,nb)
        for actual,expected in zip(got,[eg,d,ca,a]):assert np.array_equal(actual[4:-4,4:-4],expected[4:-4,4:-4])
        base=rng.integers(0,65536,(70,74,3),dtype=np.uint16);out=probe.consume(got[2],base,cfa,nr,nb)
        assert np.array_equal(out[...,1],base[...,1]);mask=np.ones((70,74),bool);mask[10:-10,10:-10]=False
        assert np.array_equal(out[mask],base[mask])
        # Wider signed consumer, unequal WB scales and delayed camera-domain clamps.
        ca=rng.integers(-30000,60001,(70,74),dtype=np.int32);gg=q14(base[...,1])
        actual=q14(probe.consume(ca,base,cfa,nr,nb))
        for channel,ax,ay,nc in [(0,1-int(rx),1-int(ry),nr),(2,int(rx),int(ry),nb)]:
            horizontal=np.where(xx%2==ax,ca,(np.roll(ca.astype(np.int64),1,1)+np.roll(ca.astype(np.int64),-1,1))//2)
            interpolated=np.where(yy%2==ay,horizontal,(np.roll(horizontal,1,0)+np.roll(horizontal,-1,0))//2)
            expected=np.clip(np.floor(nc*(gg+interpolated)+.5),0,16383).astype(np.int64)
            assert np.array_equal(actual[10:-10,10:-10,channel],expected[10:-10,10:-10])
            consumer_samples+=expected[10:-10,10:-10].size
    return dict(unity_neutral_exact_old_probe_cases=unity,flat_colour_cases=flat,wider_difference_headroom_cases=headroom,
                independent_producer_all_cfa=True,independent_wider_consumer_samples=consumer_samples,
                green_unchanged=True,border10_unchanged=True,noise2_implemented=False)

if __name__=='__main__':
    import json,sys
    path=Path(sys.argv[1]);print(json.dumps(checks(DomainProbe(path),RbProbe(path)),indent=2))
