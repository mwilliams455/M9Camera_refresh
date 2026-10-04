"""Independent vector reference and strict DNG gain-map reader for adapter 02."""
from pathlib import Path
import ctypes,struct
import numpy as np
ROOT=Path(__file__).resolve().parent

def parse_maps(payload,shape):
    h,w=shape;at=4
    if len(payload)<4 or struct.unpack_from('>I',payload)[0]!=4:raise ValueError('four GainMap opcodes required')
    maps={};geometry=None
    for _ in range(4):
        op,ver,flags,n=struct.unpack_from('>4I',payload,at);at+=16
        body=payload[at:at+n];at+=n
        if op!=9 or ver!=0x01030000 or n<80 or len(body)!=n:raise ValueError('unsupported opcode')
        top,left,bottom,right,plane,planes,rpitch,cpitch=struct.unpack_from('>8I',body)
        gh,gw=struct.unpack_from('>2I',body,32)
        geo=struct.unpack_from('>4d',body,40)
        mp,=struct.unpack_from('>I',body,72)
        if top not in [0,1] or left not in [0,1] or (bottom,right)!=(h,w) or (plane,planes,rpitch,cpitch,mp)!=(0,1,2,2,1):
            raise ValueError('requires full-area single-plane Bayer-phase maps')
        if n!=76+4*gh*gw or (top,left) in maps:raise ValueError('bad/duplicate phase map')
        if geometry is not None and geometry!=(gh,gw,geo):raise ValueError('map geometry mismatch')
        geometry=(gh,gw,geo);maps[top,left]=np.frombuffer(body,'>f4',offset=76).astype(np.float32).reshape(gh,gw)
    if at!=len(payload) or len(maps)!=4:raise ValueError('trailing payload or missing phases')
    return np.stack([maps[y,x] for y in range(2) for x in range(2)]),np.array(geometry[2],dtype=float)

def validate(raw,mode,strength,profile,black,white,grids,geo):
    a=np.asarray(raw);p=np.asarray(profile,dtype=float);b=np.asarray(black,dtype=float)
    g=np.asarray(grids,dtype=np.float32);geo=np.asarray(geo,dtype=float)
    if a.ndim!=2 or a.dtype!=np.uint16 or not a.size or max(a.shape)>32767:raise ValueError('uint16 mosaic required')
    if p.shape!=(4,2) or b.shape!=(4,) or g.ndim!=3 or g.shape[0]!=4 or min(g.shape[1:])<1 or max(g.shape[1:])>1024 or geo.shape!=(4,):raise ValueError('invalid calibration shape')
    if not all(np.isfinite(x).all() for x in [p,b,g,geo]) or not np.isfinite(white) or not 0<white<=65535:raise ValueError('nonfinite calibration')
    if (p[:,0]<=0).any() or (p<0).any() or (p>1).any() or (b<0).any() or (b>=white).any() or (g<1/64).any() or (g>64).any() or (geo[:2]<=0).any():raise ValueError('invalid calibration range')
    if mode not in [0,1,2] or not np.isfinite(strength) or not 0<=strength<=4 or a.max()>white:raise ValueError('invalid image or mode')
    if mode and min(a.shape)<=4*mode:raise ValueError('small mosaic')
    return tuple(np.ascontiguousarray(x) for x in [a,p,b,g,geo])

def gain_image(shape,grids,geo,frame_shape=None,origin=(0,0)):
    h,w=shape;fh,fw=frame_shape or shape;oy,ox=origin
    gh,gw=grids.shape[1:];out=np.empty(shape,dtype=float)
    for c in range(4):
        sy=(c//2-oy)%2;sx=(c%2-ox)%2
        fy=np.clip(((np.arange(sy,h,2)+oy+.5)/fh-geo[2])/geo[0],0,gh-1)
        fx=np.clip(((np.arange(sx,w,2)+ox+.5)/fw-geo[3])/geo[1],0,gw-1)
        y0=fy.astype(int);x0=fx.astype(int);y1=np.minimum(y0+1,gh-1);x1=np.minimum(x0+1,gw-1)
        dy=(fy-y0)[:,None];dx=(fx-x0)[None,:];g=grids[c].astype(float)
        a=g[y0[:,None],x0[None,:]]*(1-dy)+g[y1[:,None],x0[None,:]]*dy
        b=g[y0[:,None],x1[None,:]]*(1-dy)+g[y1[:,None],x1[None,:]]*dy
        out[sy::2,sx::2]=a*(1-dx)+b*dx
    return out

def native(raw,mode,strength,profile,black,white,grids,geo):
    a,p,b,g,geo=validate(raw,mode,strength,profile,black,white,grids,geo);out=np.empty_like(a)
    fn=ctypes.CDLL(str(ROOT/'libshaded_noise.so')).phone_noise_shaded
    u16=ctypes.POINTER(ctypes.c_uint16);pd=ctypes.POINTER(ctypes.c_double);pf=ctypes.POINTER(ctypes.c_float)
    fn.argtypes=[u16,u16,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_double,pd,pd,ctypes.c_double,pf,ctypes.c_int,ctypes.c_int,pd]
    fn.restype=ctypes.c_int
    rc=fn(a.ctypes.data_as(u16),out.ctypes.data_as(u16),a.shape[1],a.shape[0],mode,strength,p.ctypes.data_as(pd),
          b.ctypes.data_as(pd),white,g.ctypes.data_as(pf),g.shape[1],g.shape[2],geo.ctypes.data_as(pd))
    if rc:raise ValueError(f'native status {rc}')
    return out

def reference(raw,mode,strength,profile,black,white,grids,geo,diagnostics=False,frame_shape=None,origin=(0,0)):
    a,p,b,g,geo=validate(raw,mode,strength,profile,black,white,grids,geo)
    out=a.copy();gain=gain_image(a.shape,g,geo,frame_shape,origin)
    yy,xx=np.indices(a.shape);phase=((yy+origin[0])%2)*2+(xx+origin[1])%2;bl=b[phase];span=white-bl
    value=bl+gain*(a.astype(float)-bl);target=value.copy()
    if mode==0 or strength==0:return (out,{'target':target,'gain':gain,'eligible':np.zeros(a.shape,bool)}) if diagnostics else out
    variance=gain**2*span**2*(p[phase,0]*np.maximum(0,(a-bl)/span)+p[phase,1])
    margin=np.maximum(1,(gain+1)*span/65535)
    valid=(a>bl+margin)&(a<white-margin)&(value>bl+margin)&(value<white-margin)
    r=2*mode;k=np.array([1,2,1] if mode==1 else [1,2,2,2,1],dtype=float);den=k.sum()
    def pass_one(v,weights,axis):
        n=v.shape[axis]-2*r;result=None
        for i,w in enumerate(weights):
            slices=[slice(None)]*2;slices[axis]=slice(2*i,2*i+n)
            term=w*v[tuple(slices)];result=term if result is None else result+term
        return result
    axis0=1 if mode==1 else 0;axis1=1-axis0
    quantized=np.floor(value)
    first=np.floor(pass_one(quantized,k,axis0)/den)
    smooth=np.floor(pass_one(first,k,axis1)/den)
    first_var=pass_one(variance,k*k,axis0)/(den*den)
    center=.25 if mode==1 else .0625
    core=np.s_[r:-r,r:-r];v=value[core];var=pass_one(first_var,k*k,axis1)/(den*den)+(1-2*center)*variance[core]
    safe=np.ones(v.shape,bool)
    for dy in range(-r,r+1,2):
        for dx in range(-r,r+1,2):safe &= valid[r+dy:a.shape[0]-r+dy,r+dx:a.shape[1]-r+dx]
    q=quantized[core]
    distance=np.abs(q-smooth);threshold=strength*np.sqrt(var)
    active=safe&(distance>0)&(threshold>distance)
    alpha=np.maximum(0,1-distance/threshold)
    filtered=np.floor(q+alpha*(smooth-q))
    candidate=np.floor(a[core]+(filtered-q)/gain[core]+.5)
    projected=bl[core]+gain[core]*(candidate-bl[core])
    active&=(candidate>bl[core]+margin[core])&(candidate<white-margin[core])&(projected>bl[core]+margin[core])&(projected<white-margin[core])
    out[core]=np.where(active,candidate,a[core]).astype(np.uint16)
    target[core]=np.where(active,v+(filtered-q),v)
    eligible=np.zeros(a.shape,bool);eligible[core]=safe
    if diagnostics:return out,{'target':target,'gain':gain,'eligible':eligible,'active':active,'residual_variance':var}
    return out

def reference_strips(raw,mode,strength,profile,black,white,grids,geo,rows=64):
    """Full-frame independent reference, bounded work arrays plus two outputs."""
    out=np.empty_like(raw);target=np.empty(raw.shape,dtype=np.float32);gain=np.empty(raw.shape,dtype=np.float32)
    eligible=np.empty(raw.shape,bool);r=2*mode;h,w=raw.shape
    for top in range(0,h,rows):
        bottom=min(top+rows,h);start=max(0,top-r);end=min(bottom+r,h)
        # Tiny final stripes need enough context to meet the strict kernel size.
        start=min(start,max(0,end-(4*mode+1)))
        chunk,d=reference(raw[start:end],mode,strength,profile,black,white,grids,geo,True,raw.shape,(start,0))
        sl=np.s_[top-start:bottom-start]
        out[top:bottom]=chunk[sl];target[top:bottom]=d['target'][sl]
        gain[top:bottom]=d['gain'][sl];eligible[top:bottom]=d['eligible'][sl]
    return out,{'target':target,'gain':gain,'eligible':eligible}
