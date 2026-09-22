"""Exact scalar/vector oracle for the M9DETAIL1P native clipped-anchor guard."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np

def cfa_masks(shape,cfa):
    y,x=np.ogrid[:shape[0],:shape[1]]
    rx,ry=cfa&1,cfa>>1
    red=(x%2==rx)&(y%2==ry)
    blue=(x%2!=rx)&(y%2!=ry)
    return red,blue,~(red|blue)

def reference(diff,sensor,full_w,source_x,source_y,cfa,white,nr,nb,carrier):
    h,w=diff.shape
    out=carrier.copy()
    active=np.zeros((h,w),np.uint8)
    reduction=np.zeros((h,w),np.int32)
    red,blue,_=cfa_masks(diff.shape,cfa)
    target=np.where(blue,nr,np.where(red,nb,1.0))
    valid=np.zeros((4,h,w),bool)
    ds=np.zeros((4,h,w),np.int32)
    for k,(dy,dx) in enumerate(((-1,-1),(-1,1),(1,-1),(1,1))):
        shifted=np.roll(np.roll(diff,dy,0),dx,1)
        ds[k]=shifted
        # np.roll's sign is opposite source indexing: output[y,x]=input[y-dy,x-dx].
        yy=np.arange(h)[:,None]+source_y-dy
        xx=np.arange(w)[None,:]+source_x-dx
        valid[k]=(sensor[yy,xx] < white)
    count=valid.sum(0)
    survivors=np.all(np.where(valid,ds<=0,True),axis=0)
    inner=np.zeros((h,w),bool);inner[3:-3,3:-3]=True
    mask=inner&(red|blue)&(target<=.78)&(carrier>0)&(count==3)&survivors
    out[mask]=out[mask]//2
    active[mask]=1
    reduction[mask]=carrier[mask]-out[mask]
    return out,active,reduction

class Native:
    def __init__(self,build):
        build.mkdir(parents=True,exist_ok=True)
        src=Path(__file__).with_suffix('.cpp');so=build/'guard.so'
        subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-fPIC','-shared',
                        str(src),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()))
        self.fn=self.lib.m9_fringe_half_guard
        self.fn.argtypes=[C.c_void_p,C.c_void_p]+[C.c_int]*8+[C.c_double]*2+[C.c_void_p]*3
        self.fn.restype=C.c_int
    def apply(self,diff,sensor,sx,sy,cfa,white,nr,nb,carrier):
        diff=np.ascontiguousarray(diff,np.int32);sensor=np.ascontiguousarray(sensor,np.uint16)
        carrier=np.ascontiguousarray(carrier,np.int32).copy()
        h,w=diff.shape;fh,fw=sensor.shape
        active=np.zeros((h,w),np.uint8);reduction=np.zeros((h,w),np.int32)
        rc=self.fn(diff.ctypes.data,sensor.ctypes.data,fw,fh,sx,sy,w,h,cfa,white,nr,nb,
                   carrier.ctypes.data,active.ctypes.data,reduction.ctypes.data)
        if rc<0:raise RuntimeError(rc)
        assert rc==int(active.sum())
        return carrier,active,reduction

def run(native):
    rng=np.random.default_rng(92325);rows=[];samples=0
    neutrals=[(.41796875,.6435546875),(.28,.48),(.62,.78),(.78,.78),(.781,.781),(1.,1.)]
    for cfa in range(4):
      for sy in range(2):
       for sx in range(2):
        # local CFA must include crop-origin phase exactly as the tiled caller does.
        phase=((cfa&1)^(sx&1))+2*((cfa>>1)^(sy&1))
        for nr,nb in neutrals:
         for rep in range(8):
            h,w=41+2*(rep%3),43+2*((rep+1)%3);fh,fw=h+sy+5,w+sx+7
            diff=rng.integers(-24000,24001,(h,w),dtype=np.int32)
            carrier=rng.integers(-16000,16001,(h,w),dtype=np.int32)
            sensor=rng.integers(64,1024,(fh,fw),dtype=np.uint16)
            # Force a mixture of 0/1/2+ censored diagonals and positive carriers.
            sensor[rng.random((fh,fw))<.07]=1023
            # deterministic positive-carrier injection without shape mismatch
            pos=rng.random((h,w))<.35
            carrier[pos]=rng.integers(1,12001,size=int(pos.sum()),dtype=np.int32)
            expected=reference(diff,sensor,fw,sx,sy,phase,1023,nr,nb,carrier)
            actual=native.apply(diff,sensor,sx,sy,phase,1023,nr,nb,carrier)
            for a,e in zip(actual,expected):assert np.array_equal(a,e),(cfa,sx,sy,nr,nb,rep)
            # Inactive data and all non-carrier inputs are immutable by API.
            assert np.array_equal(actual[0][actual[1]==0],carrier[actual[1]==0])
            samples+=h*w;rows.append(dict(cfa=cfa,phase=phase,origin=[sx,sy],neutral=[nr,nb],
                                          changed=int(actual[1].sum())))
    # Direct boundary construction: .78 can change, .781 cannot.
    h=w=21;fh=fw=25;diff=np.zeros((h,w),np.int32);sensor=np.full((fh,fw),500,np.uint16);carrier=np.zeros((h,w),np.int32)
    cfa=0;red,blue,_=cfa_masks((h,w),cfa)
    gy,gx=np.indices((h,w))
    y,x=np.argwhere(blue&(gy>4)&(gy<h-5)&(gx>4)&(gx<w-5))[0]
    carrier[y,x]=101
    # one red diagonal censored; other surviving red differences non-positive
    sensor[y+1,x+1]=1023
    a=native.apply(diff,sensor,0,0,cfa,1023,.78,1.,carrier)
    assert a[0][y,x]==50 and a[1][y,x]==1 and a[2][y,x]==51
    b=native.apply(diff,sensor,0,0,cfa,1023,.781,1.,carrier)
    assert b[0][y,x]==101 and b[1][y,x]==0
    return dict(cases=len(rows),array_samples=samples,all_four_cfa=True,all_crop_origin_parities=True,
                neutral_boundary_078_inclusive=True,neutral_0781_exact_fallback=True,
                inactive_carrier_exact=True,oracle='independent NumPy source-indexing reference')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);native=Native(a.out/'native');result=run(native)
    result['cpp_sha256']=hashlib.sha256(Path(__file__).with_suffix('.cpp').read_bytes()).hexdigest()
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
