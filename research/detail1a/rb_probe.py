"""Arithmetic and CFA checks for the partial DETAIL1C R/B reconstruction probe."""
from pathlib import Path
import ctypes as C
import subprocess
import numpy as np

def q14(z):return (z.astype(np.int64)*16383+32767)//65535
def q16(z):return ((np.clip(z,0,16383).astype(np.int64)*65535+8191)//16383).astype(np.uint16)

class RbProbe:
    def __init__(self,build):
        build=Path(build);build.mkdir(parents=True,exist_ok=True);so=build/'rb_probe.so'
        subprocess.run(['g++','-std=c++17','-O2','-fPIC','-shared',str(Path(__file__).with_suffix('.cpp')),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()))
        self.lib.rb_stages.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int]+[C.c_void_p]*4
        self.lib.rb_stages.restype=None
        self.lib.rb_consume.restype=None
        self.lib.rb_consume.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_void_p]
    def stages(self,raw,cfa,shrink=True):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        arrays=[np.empty((h,w),dtype=t) for t in [np.uint16,np.int16,np.int16,np.uint16]]
        self.lib.rb_stages(raw.ctypes.data,w,h,cfa,shrink,*[z.ctypes.data for z in arrays])
        return arrays
    def consume(self,carrier,base,cfa):
        carrier=np.ascontiguousarray(carrier,dtype=np.int16);base=np.ascontiguousarray(base,dtype=np.uint16)
        h,w=carrier.shape;out=np.empty_like(base)
        self.lib.rb_consume(carrier.ctypes.data,base.ctypes.data,w,h,cfa,out.ctypes.data)
        return out

def addressed_consumer(d,g,border=10):
    """Two pointer traversals transcribed from ffa03410, distinct from C++ per-pixel code."""
    h,w=d.shape;planes=[]
    for phase in range(2):
        p=np.full((h,w),-99999,np.int64)
        for j in range(h//2-border):
            for i in range(w//2-border):
                y=border+phase+2*j;x=border+phase+2*i;s=2 if phase==0 else -2
                a,b,c,e=[int(v) for v in [d[y,x],d[y,x+s],d[y+s,x],d[y+s,x+s]]]
                top=(a+b)//2;bottom=(c+e)//2
                entries=[(y,x,a),(y,x+1,top),(y+1,x,(a+c)//2),(y+1,x+1,(top+bottom)//2)] if phase==0 else [
                    (y,x-1,top),(y,x,a),(y-1,x-1,(top+bottom)//2),(y-1,x,(a+c)//2)]
                for yy,xx,v in entries:p[yy,xx]=np.clip(int(g[yy,xx])+v,0,16383)
        planes.append(p)
    return planes

def checks(probe):
    rng=np.random.default_rng(92126);samples=0
    for shape in [(48,52),(64,66),(63,69)]:
        d=rng.integers(-16383,16384,shape,dtype=np.int16);g=rng.integers(0,16384,shape,dtype=np.uint16)
        base=np.repeat(q16(g)[...,None],3,axis=2);planes=addressed_consumer(d,g)
        for cfa in [0,3]:
            out=q14(probe.consume(d,base,cfa))
            for channel,plane in zip([2,0] if cfa==0 else [0,2],planes):
                mask=plane!=-99999
                assert np.array_equal(out[...,channel][mask],plane[mask]),('address oracle',shape,cfa,channel)
                samples+=int(mask.sum())
    shape=(68,72);yy,xx=np.indices(shape)
    for cfa in range(4):
        rx=cfa in [1,3];ry=cfa in [2,3];r=((xx%2)==rx)&((yy%2)==ry);b=((xx%2)!=rx)&((yy%2)!=ry);g=~(r|b)
        for vals in [(4096,4096,4096),(1000,7000,12000),(15000,3000,1800),(0,16383,0)]:
            raw=q16(np.where(r,vals[0],np.where(b,vals[2],vals[1])))
            gr,di,ca,un=probe.stages(raw,cfa);base=np.zeros((*shape,3),np.uint16);base[...,1]=q16(gr)
            out=probe.consume(ca,base,cfa)
            assert np.all(out[10:-10,10:-10]==q16(np.array(vals)))
            assert np.all(un[4:-4,4:-4]==0)
        raw=rng.integers(0,65536,shape,dtype=np.uint16);z=q14(raw)
        card=lambda a:sum(np.roll(a,s,axis=k) for k,s in [(0,-1),(0,1),(1,-1),(1,1)])
        diag=lambda a:sum(np.roll(np.roll(a,dy,0),dx,1) for dy in [-1,1] for dx in [-1,1])
        eg=np.where(g,(4*z+diag(z))//8,card(z)//4);res=np.where(g,np.abs(eg-z),0);eu=np.where(g,0,card(res))
        for shrink in [False,True]:
            ed=np.where(g,0,z-eg)
            if shrink:ed=np.where(np.abs(ed)<eu,np.sign(ed)*np.maximum(np.abs(ed)-(eu//4),0),ed)
            ec=np.where(g,0,diag(ed)//4);arrays=probe.stages(raw,cfa,shrink)
            for actual,expected in zip(arrays,[eg,ed,ec,eu]):
                assert np.array_equal(actual[4:-4,4:-4],expected[4:-4,4:-4]),('producer oracle',cfa,shrink)
        base=rng.integers(0,65536,(*shape,3),dtype=np.uint16);out=probe.consume(arrays[2],base,cfa)
        assert np.array_equal(out[...,1],base[...,1])
        mask=np.ones(shape,bool);mask[10:-10,10:-10]=False
        assert np.array_equal(out[mask],base[mask])
    # Translation changes RGGB to the appropriate crop-local phase, not colour identity.
    raw=rng.integers(0,65536,(80,84),dtype=np.uint16);base=rng.integers(0,65536,(80,84,3),dtype=np.uint16)
    out=probe.consume(probe.stages(raw,0)[2],base,0)
    for dy,dx,cfa in [(0,1,1),(1,0,2),(1,1,3)]:
        crop=raw[dy:,dx:];co=probe.consume(probe.stages(crop,cfa)[2],base[dy:,dx:],cfa)
        assert np.array_equal(co[12:-12,12:-12],out[dy:,dx:][12:-12,12:-12])
    return dict(addressed_consumer_samples=samples,producer_integer_oracle_all_four_cfa=True,
        constant_colour_cases=16,cfa_crop_translation=True,green_unchanged=True,border10_unchanged=True,
        blackfin_hardware_equivalence=False,noise2_implemented=False)

if __name__=='__main__':
    import json,sys
    print(json.dumps(checks(RbProbe(Path(sys.argv[1]))),indent=2))
