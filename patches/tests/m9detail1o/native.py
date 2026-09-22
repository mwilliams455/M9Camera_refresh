#!/usr/bin/env python3
"""DETAIL1O integrated native test: tile seams, guard interaction, common50 oracle."""
from pathlib import Path
import ctypes as C,sys,subprocess,json
import numpy as np

repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'research/detail1a'))
from rb_domain import DomainProbe
from noise2 import Noise2
from noise2_guard import guarded
from common_mode_censor_probe import certificate_constraints,interpolated_fields,reconstruct,llround

class Native1O:
    def __init__(self,assembled,build):
        build.mkdir(parents=True,exist_ok=True)
        so=build/'detail1o.so'
        subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror',
            '-ffp-contract=off','-fno-fast-math','-DM9DETAIL1H_HOST','-fPIC','-shared',
            str(assembled/'app/src/main/cpp/m9detail1h.cpp'),
            str(repo/'research/detail1a/rb_domain.cpp'),
            str(repo/'research/detail1a/noise2_guard_native.cpp'),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()))
        self.lib.detail1h_host.argtypes=[C.c_void_p]*2+[C.c_int]*4+[C.c_void_p,C.c_int]+[C.c_void_p]*2+[C.c_int]*2+[C.c_double]*3+[C.c_int]*2+[C.c_void_p]*2
        self.lib.detail1h_host.restype=C.c_int
        self.lib.detail1h_fail_guard_tile.argtypes=[C.c_int]
    def apply(self,norm,sensor,base,cfa,nr,nb,black,white,profile,gains,scale,tile=64,guard=True,origin_y=0):
        n=np.ascontiguousarray(norm,np.uint16);s=np.ascontiguousarray(sensor,np.uint16)
        b=np.ascontiguousarray(black,np.float32);p=np.ascontiguousarray(profile,np.float64);g=np.ascontiguousarray(gains,np.float64)
        h,w=n.shape;mh,mw,ch=g.shape;out=np.array(base,np.uint16,copy=True,order='C');stats=np.zeros(15,np.float64)
        rc=self.lib.detail1h_host(n.ctypes.data,s.ctypes.data,w,h,cfa,origin_y,b.ctypes.data,white,p.ctypes.data,g.ctypes.data,mw,mh,scale,nr,nb,tile,int(guard),out.ctypes.data,stats.ctypes.data)
        if rc:raise RuntimeError(('DETAIL1O native',rc))
        names=['status','tiles','supported_rb_samples','changed_carrier_samples','max_abs_correction',
               'censored_samples','mean_confidence','mean_residual_variance14','scratch_budget_bytes','elapsed_ms',
               'common_pixels','common_max_q14','common_sum_q14','certificate_support_pixels','color_abstained_pixels']
        return out,dict(zip(names,stats.tolist()))

def variance(sensor,cfa,black,white,profile,scale=1.):
    h,w=sensor.shape;yy,xx=np.indices((h,w));rx=cfa&1;ry=cfa>>1
    red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
    colour=np.where(red,0,np.where(blue,2,1));p=(yy%2)*2+(xx%2)
    signal=np.clip((sensor.astype(np.float32)-black[p])/np.maximum(1,np.float32(white)-black[p]),0,1)
    v=np.empty((h,w),np.float64)
    for ch in range(3):v[colour==ch]=profile[2*ch]*signal[colour==ch]+profile[2*ch+1]
    return v*(16383./scale)**2

def oracle(norm,sensor,base,cfa,nr,nb,black,white,profile,scale,probe,noise,guard):
    green,_,carrier,_=probe.stages(norm,cfa,nr,nb,shrink=True)
    selected=carrier
    if guard:
        rv=variance(sensor,cfa,np.asarray(black),white,np.asarray(profile),scale)
        yy,xx=np.indices(sensor.shape);p=(yy%2)*2+(xx%2)
        cens=(sensor<=np.asarray(black)[p])|(sensor>=white)
        selected,_=guarded(noise,carrier,green,cfa,nr,nb,rv,cens)
    current=probe.consume(selected,base,cfa,nr,nb)
    _,bounds,support=certificate_constraints(probe,norm,sensor,cfa,nr,nb,black,white)
    fields=interpolated_fields(selected,cfa)
    hi0,hi1=bounds[0][1],bounds[1][1];av0,av1=bounds[0][2],bounds[1][2]
    joint=support&av0&av1&(fields[0]>hi0)&(fields[1]>hi1)
    common=np.where(joint,np.minimum(fields[0]-hi0,fields[1]-hi1),0)
    corr=llround(common*.5)
    out=reconstruct(base,[fields[0]-corr,fields[1]-corr],nr,nb)
    return out,current,corr,joint

def run(assembled,out):
    out.mkdir(parents=True,exist_ok=True);native=Native1O(assembled,out/'build');probe=DomainProbe(out/'build');noise=Noise2(out/'build')
    rng=np.random.default_rng(92231);rows=[];total=0
    nr,nb=.41796875,.6435546875;black=np.array([64]*4,np.float32);white=1023
    profile=np.array([2.7e-5,4.4e-7,3.1e-5,3.7e-7,2.6e-5,4.5e-7],np.float64)
    grid=np.ones((1,1,4),np.float64);scale=1.
    for cfa in range(4):
        rx=cfa&1;ry=cfa>>1
        for h,w in [(65,67),(127,129),(259,257)]:
            yy,xx=np.indices((h,w));red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
            # Bright sky + thin dark/green-like branches, with deterministic hard clipping.
            lum=np.where(((xx+yy*.43)%15)<4,.045,1.35)
            factor=np.where(red,nr,np.where(blue,nb,1.))
            physical=np.minimum(lum*factor,1.)
            sensor=np.clip(np.floor(64+physical*(white-64)+.5),64,white).astype(np.uint16)
            # Add low-level texture away from hard white while retaining known censor geometry.
            jitter=rng.integers(-2,3,(h,w));sensor=np.clip(sensor.astype(np.int32)+np.where(sensor<white,jitter,0),64,white).astype(np.uint16)
            norm=np.floor((sensor.astype(float)-64)/(white-64)*65535+.5).astype(np.uint16)
            base=rng.integers(0,65536,(h,w,3),dtype=np.uint16)
            # Preserve a plausible native sharp green rather than random full-range green.
            base[...,1]=np.clip(np.floor((lum/1.35)*50000+5000),0,65535).astype(np.uint16)
            for guard in (False,True):
                expected,current,corr,joint=oracle(norm,sensor,base,cfa,nr,nb,black,white,profile,scale,probe,noise,guard)
                for tile in (32,64,128,256):
                    actual,stats=native.apply(norm,sensor,base,cfa,nr,nb,black,white,profile,grid,scale,tile=tile,guard=guard)
                    if not np.array_equal(actual,expected):
                        raise AssertionError((cfa,h,w,guard,tile,int(np.count_nonzero(actual!=expected)),np.max(np.abs(actual.astype(int)-expected.astype(int)))))
                    assert np.array_equal(actual[...,1],base[...,1])
                    assert int(stats['common_pixels'])==int(np.count_nonzero(corr[10:-10,10:-10]))
                    rows.append(dict(cfa=cfa,shape=[h,w],guard=guard,tile=tile,common_pixels=int(stats['common_pixels']),support=int(stats['certificate_support_pixels'])))
                    total+=actual.size
            # Forced guard failure must recompute full D+common50, never mixed H/O.
            native.lib.detail1h_fail_guard_tile(1)
            recovered,stats=native.apply(norm,sensor,base,cfa,nr,nb,black,white,profile,grid,scale,tile=64,guard=True)
            fallback,_,_,_=oracle(norm,sensor,base,cfa,nr,nb,black,white,profile,scale,probe,noise,False)
            assert stats['status']==2 and np.array_equal(recovered,fallback)
    result=dict(schema='m9.detail1o.integrated_native.v1',cases=len(rows),rgb_samples=total,
                exact_python_common50_oracle=True,all_four_cfa=True,green_exact=True,
                guard_on_off_exact=True,tile_sizes=[32,64,128,256],forced_guard_failure_exact_D_common50=True,
                rows=rows)
    (out/'native_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('M9DETAIL1O INTEGRATED NATIVE PASS',len(rows),'cases',total,'RGB samples')
if __name__=='__main__':
    run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
