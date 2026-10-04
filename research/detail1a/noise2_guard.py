"""DETAIL1F: bounded mobile Noise2 probe, not recovered Leica adaptation logic.

Retains the recovered mode1 smoothing target, estimates noise in the actual
carrier-residual domain, and preserves the input where detail or clipping makes
that target unreliable. DNG NoiseProfile remains an unverified noise estimate.
"""
import numpy as np
from scipy.signal import convolve2d
from scipy.ndimage import convolve,uniform_filter,maximum_filter
from noise2 import parameters

def carrier_kernel():
    k=np.zeros((5,5),float)
    for dy in [-1,1]:
        for dx in [-1,1]:
            k[2+dy,2+dx]+=.25
            for gy,gx in [(-1,0),(1,0),(0,-1),(0,1)]:k[2+dy+gy,2+dx+gx]-=1/16
    return k

def residual_kernel():
    k=carrier_kernel();h=np.outer([1,0,2,0,1],[1,0,2,0,1])/16
    result=-convolve2d(k,h,mode='full');result[2:7,2:7]+=k
    return result

def residual_variance(raw_variance14,cfa,nr,nb):
    v=np.array(raw_variance14,dtype=np.float64,copy=True)
    rx=int(cfa in [1,3]);ry=int(cfa in [2,3])
    v[ry::2,rx::2]/=nr**2;v[1-ry::2,1-rx::2]/=nb**2
    # Squared *combined* kernel accounts for shared raw samples/covariance.
    # Linear unshrunk model: Co is nonlinear and has no claimed exact variance.
    return np.maximum(convolve(v,residual_kernel()**2,mode='constant'),0).astype(np.float32)

def guarded(noise,carrier,green,cfa,nr,nb,raw_variance14,censored=None,strength=1.):
    if strength not in (.5,1.,2.):raise ValueError('Only the three audited profile sensitivity factors are supported')
    c=np.ascontiguousarray(carrier,dtype=np.int32);g=np.ascontiguousarray(green,dtype=np.uint16)
    v=np.asarray(raw_variance14)
    if c.shape!=g.shape or v.shape!=c.shape or not np.all(np.isfinite(v)) or np.any(v<0):raise ValueError('invalid variance or shape')
    _,smooth,_=noise.apply(c,g,cfa,parameters(0,nr,nb))
    vr=residual_variance(v,cfa,nr,nb)*strength;res=c.astype(float)-smooth
    confidence=np.zeros(c.shape,np.float32);rx=int(cfa in [1,3]);ry=int(cfa in [2,3])
    for py,px in [(ry,rx),(1-ry,1-rx)]:
        phase=np.s_[py::2,px::2];vv=vr[phase];r=res[phase]
        energy=uniform_filter(r*r,size=5,mode='constant')
        expected=uniform_filter(vv.astype(float),size=5,mode='constant')
        # Local residual energy beyond the noise model protects colour structure.
        trust=np.clip(2-energy/np.maximum(expected,1e-12),0,1)
        weight=np.clip(1-np.abs(r)/(2*np.sqrt(np.maximum(vv,1e-12))),0,1)
        confidence[phase]=np.where(vv>0,trust*weight,0)
    # Co support3 + mode1 radius2 + consumer1. Keep unsafe samples at DETAIL1D.
    if censored is not None:
        if np.shape(censored)!=c.shape:raise ValueError('invalid censor mask')
        confidence[maximum_filter(np.asarray(censored,dtype=np.uint8),size=13)>0]=0
    confidence[:10]=0;confidence[-10:]=0;confidence[:,:10]=0;confidence[:,-10:]=0
    # Round the correction, not the result, retaining sign symmetry and exact bypass.
    correction=np.rint(-confidence*res).astype(np.int32);out=c+correction
    assert np.all(np.abs(correction.astype(float))<=np.sqrt(vr)*.5+.50001)
    assert np.all(out>=np.minimum(c,smooth)) and np.all(out<=np.maximum(c,smooth))
    mask=np.zeros(c.shape,bool)
    mask[ry::2,rx::2]=True;mask[1-ry::2,1-rx::2]=True;mask[:10]=False;mask[-10:]=False;mask[:,:10]=False;mask[:,-10:]=False
    stats=dict(profile_variance_factor=strength,mode=1,changed_carrier_pct=float(np.mean(correction[mask]!=0)*100),
        mean_confidence=float(confidence[mask].mean()),residual_sigma_quantiles=np.percentile(np.sqrt(vr[mask]),[10,50,90]).tolist(),
        max_abs_correction=int(np.abs(correction.astype(np.int64)).max()),
        detail_or_clip_bypass_pct=float(np.mean(confidence[mask]==0)*100),bounded_to_smoothing_target=True)
    return out,stats
