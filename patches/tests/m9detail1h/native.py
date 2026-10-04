#!/usr/bin/env python3
"""Tile seams, all CFAs/origins, fallback, clipped patches and odd extents."""
from pathlib import Path
import sys,json
import numpy as np
from scipy.ndimage import gaussian_filter
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'research/detail1a'))
from detail1h import TiledDetail
from rb_domain import DomainProbe
from noise2 import Noise2
from noise2_guard import guarded

def run(build):
    t=TiledDetail(build);d=DomainProbe(build);noise=Noise2(build);rng=np.random.default_rng(92181);cases=[]
    for cfa in range(4):
        for h,w in [(24,25),(65,67),(127,129),(259,257)]:
            yy,xx=np.indices((h,w));rx=cfa&1;ry=cfa>>1;red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
            nr,nb=.37,.61;factor=np.where(red,nr,np.where(blue,nb,1.))
            s=10000+2000*np.sin(xx/9)+rng.normal(size=(h,w))*120
            sensor=np.clip(np.rint(s*factor+64),0,65535).astype(np.uint16);sensor[h//2,w//2]=65535
            v=np.empty((h,w),np.float32);norm=np.empty_like(sensor);black=np.array([64]*4,np.float32)
            profile=np.array([.0002,.000001,.00015,.0000008,.00025,.0000012])
            grid=np.ones((2,3,4));scale=1.
            for py in range(2):
                for px in range(2):
                    phase=np.s_[py::2,px::2];colour=0 if py==ry and px==rx else 2 if py!=ry and px!=rx else 1
                    signal=np.clip((sensor[phase].astype(np.float32)-64)/np.float32(65535-64),0,1)
                    norm[phase]=np.floor(signal*np.float32(65535)+np.float32(.5)).astype(np.uint16)
                    v[phase]=profile[2*colour]*signal+profile[2*colour+1];v[phase]*=16383.**2
            g,_,c,_=d.stages(norm,cfa,nr,nb)
            base=rng.integers(0,65536,(h,w,3),dtype=np.uint16)
            mask=(sensor<=64)|(sensor>=65535)
            ca,_=guarded(noise,c,g,cfa,nr,nb,v,mask)
            ref=d.consume(ca,base,cfa,nr,nb);fallback=d.consume(c,base,cfa,nr,nb)
            for tile in [32,64,256]:
                for oy in [0,1]:
                    actual,stats=t.apply(norm,sensor,base,cfa,nr,nb,black,65535,profile,grid,scale,tile=tile,origin_y=oy)
                    assert np.array_equal(actual,ref),(cfa,h,w,tile,oy,int(np.count_nonzero(actual!=ref)))
                    off,_=t.apply(norm,sensor,base,cfa,nr,nb,black,65535,profile,grid,scale,tile=tile,guard=False,origin_y=oy)
                    assert np.array_equal(off,fallback)
                    assert np.array_equal(actual[...,1],base[...,1])
                    cases.append(dict(cfa=cfa,shape=[h,w],tile=tile,origin_y=oy,rgb_samples=actual.size))
            if h==259:
                t.lib.detail1h_fail_guard_tile(2)
                recovered,stats=t.apply(norm,sensor,base,cfa,nr,nb,black,65535,profile,grid,scale,tile=64)
                assert stats['status']==2 and np.array_equal(recovered,fallback),'partial guard must recover full D'
    return dict(cases=cases,exact_guard_and_D_rgb_samples=sum(x['rgb_samples'] for x in cases),green_unchanged=True,
                injected_partial_frame_guard_failure_exact_D_all_cfa=True)

if __name__=='__main__':
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);r=run(out/'native')
    (out/'tile_checks.json').write_text(json.dumps(r,indent=2)+'\n');print('DETAIL1H exact tile cases',len(r['cases']),'RGB samples',r['exact_guard_and_D_rgb_samples'])
