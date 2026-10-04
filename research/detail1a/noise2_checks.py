"""Noise2 arithmetic, CFA isolation, known-colour noise/detail and neutral edges."""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import convolve1d,gaussian_filter
from native import Native
from rb_probe import q16
from rb_domain import DomainProbe
from noise2 import Noise2,parameters

def oracle(c,g,cfa,p,lut,rounding):
    weights={1:[1,2,1],2:[1,2,2,2,1],3:[1,2,3,4,3,2,1]}[p['mode']]
    kernel=np.zeros(2*len(weights)-1);kernel[::2]=weights;kernel/=sum(weights)
    rnd=(np.rint if rounding==1 else lambda x:np.floor(x+.5)) if p['mode']==2 else np.floor
    sm=rnd(convolve1d(rnd(convolve1d(c.astype(float),kernel,axis=1)),kernel,axis=0)).astype(np.int64)
    v=np.abs(c.astype(np.int64)-sm)*lut[g>>6]//16;T=p['threshold'];Q=p['attenuation'];z=v//T
    out=np.where(v<T,(v*c+(T-v)*sm)//T,np.where(z<Q,(Q-z)*c//Q,0))
    yy,xx=np.indices(c.shape);rx=cfa in [1,3];ry=cfa in [2,3]
    mask=((xx%2==rx)==(yy%2==ry));b=p['carrier_border'];mask[:b]=False;mask[-b:]=False;mask[:,:b]=False;mask[:,-b:]=False
    return np.where(mask,out,c),np.where(mask,sm,c),mask

def arithmetic(probe):
    rng=np.random.default_rng(92131);samples=0;count=np.zeros(3,dtype=int)
    for shape in [(70,74),(69,75)]:
        for cfa in range(4):
            c=rng.integers(-90000,90001,shape,dtype=np.int32);g=rng.integers(0,16384,shape,dtype=np.uint16)
            for slot in [0,5,9]:
                p=parameters(slot,.37,.61)
                for rnd in [1,2]:
                    out,sm,counts=probe.apply(c,g,cfa,p,rnd);expect,es,mask=oracle(c,g,cfa,p,probe.lut,rnd)
                    assert np.array_equal(out,expect) and np.array_equal(sm,es)
                    assert np.array_equal(out[~mask],c[~mask]);samples+=int(mask.sum());count+=list(counts.values())
    # Exercise exactly T and Q*T transitions, negative floor division, all brightness bins.
    for slot in [0,5,9]:
        p=parameters(slot,1.,1.);T=p['threshold'];Q=p['attenuation']
        for sign in [-1,1]:
            v=np.array([0,1,T-1,T,T+1,2*T-1,2*T,Q*T-1,Q*T,Q*T+1],np.int32)
            c=sign*(v+111);m=np.full(v.shape,sign*111,np.int32);g=np.zeros(v.shape,np.uint16);out=np.empty_like(c)
            probe.lib.noise2_blend(c.ctypes.data,m.ctypes.data,g.ctypes.data,len(c),probe.lut.ctypes.data,p['shift'],p['qshift'],out.ctypes.data,None)
            z=v//T;ex=np.where(v<T,(v.astype(np.int64)*c+(T-v)*m)//T,np.where(z<Q,(Q-z)*c//Q,0))
            assert np.array_equal(out,ex)
    # A constant true colour must not be desaturated, including values outside int16.
    flat=0
    for cfa in range(4):
        for slot in [0,5,9]:
            yy,xx=np.indices((48,54));c=np.where(xx%2,45000,-12000).astype(np.int32);g=np.full(c.shape,4000,np.uint16)
            out,_,_=probe.apply(c,g,cfa,parameters(slot,.25,.5));assert np.array_equal(out,c);flat+=1
    for slot in [11,12,-1]:
        try:parameters(slot,1.,1.)
        except ValueError:pass
        else:raise AssertionError('unsupported slot accepted')
    assert np.all(count>0)
    return dict(independent_filter_blend_samples=samples,all_four_cfas=True,odd_dimensions=True,all_branches=count.tolist(),
        signed_threshold_boundary_cases=60,constant_colour_headroom_cases=flat,unsupported_slots_rejected=True)

def synthetic(native,domain,noise):
    yy,xx=np.indices((96,160));core=np.s_[16:-16,16:-16];edges=[]
    for cfa in range(4):
        rx=cfa in [1,3];ry=cfa in [2,3];red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
        for nr,nb in [(.25,.5),(.37,.61),(.8,1.5)]:
            factor=np.where(red,nr,np.where(blue,nb,1.))
            for shape in ['vertical','horizontal','diagonal']:
                coord=xx if shape=='vertical' else yy*1.7 if shape=='horizontal' else xx+yy*.7
                lum=gaussian_filter(np.where(coord>80.,8000.,800.),2.);raw=q16(np.floor(lum*factor+.5))
                base=native.render(raw,nr,nb,cfa,candidate=False);g,_,c,_=domain.stages(raw,cfa,nr,nb)
                variants=[('corrected',c)]+[(f'noise_slot{s}',noise.apply(c,g,cfa,parameters(s,nr,nb))[0]) for s in [0,5,9]]
                row=dict(cfa=cfa,nr=nr,nb=nb,shape=shape,variants={})
                for name,ca in variants:
                    cam=domain.consume(ca,base,cfa,nr,nb);assert np.array_equal(cam[...,1],base[...,1])
                    z=cam[core].astype(float)/65535*16383;error=z[:,:,[0,2]]/np.array([nr,nb])-z[:,:,[1]]
                    row['variants'][name]=dict(rms=float(np.sqrt(np.mean(error**2))),max=float(np.max(np.abs(error))))
                edges.append(row)
    rng=np.random.default_rng(9021);scenes=[];cfa=0;nr,nb=.37,.61
    red=(xx%2==0)&(yy%2==0);blue=(xx%2==1)&(yy%2==1);factor=np.where(red,nr,np.where(blue,nb,1.))
    for name in ['neutral','flat_colour','colour_edge','fine_colour']:
        d=np.zeros_like(xx,dtype=float) if name=='neutral' else np.full_like(xx,1200.,dtype=float) if name=='flat_colour' else (
            np.where(xx>80,1400.,-1400.) if name=='colour_edge' else 1000*np.sin(xx*2*np.pi/16))
        scene=np.stack([4096+d,np.full_like(d,4096),4096-d],axis=-1)
        raw14=(4096+np.where(red,d,np.where(blue,-d,0)))*factor
        noisy=raw14+rng.normal(0,100,raw14.shape)*np.where(red|blue,factor,0)
        raw=q16(np.clip(np.floor(noisy+.5),0,16383));base=native.render(raw,nr,nb,cfa,candidate=False)
        g,_,c,_=domain.stages(raw,cfa,nr,nb)
        variants=[('corrected',c)]+[(f'noise_slot{s}',noise.apply(c,g,cfa,parameters(s,nr,nb))[0]) for s in [0,5,9]]
        row=dict(name=name,input_rb_noise_sigma_green14=100,variants={})
        for key,ca in variants:
            out=domain.consume(ca,base,cfa,nr,nb).astype(float)/65535*16383/np.array([nr,1,nb]);err=out[core][:,:,[0,2]]-scene[core][:,:,[0,2]]
            row['variants'][key]=dict(true_rb_rms=float(np.sqrt(np.mean(err**2))))
        scenes.append(row)
    return dict(neutral_edge_cases=36,neutral_edges=edges,known_colour_scenes=scenes,
        worst_neutral_rms_ratio={f'noise_slot{s}':max(r['variants'][f'noise_slot{s}']['rms']/r['variants']['corrected']['rms'] for r in edges) for s in [0,5,9]})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);ap.add_argument('header',type=Path);a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];noise=Noise2(a.out/'native');domain=DomainProbe(a.out/'native')
    report=dict(arithmetic=arithmetic(noise),synthetic=synthetic(Native(repo,repo/'PhotonCamera',a.header,a.out/'native'),domain,noise))
    (a.out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(arithmetic=report['arithmetic'],neutral=report['synthetic']['worst_neutral_rms_ratio'],colour=report['synthetic']['known_colour_scenes']),indent=2))
