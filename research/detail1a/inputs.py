"""Recreate the current NORM030 input from Android DNG metadata.

Requires four complete Android OpcodeList2 GainMaps. Their stored grid values
reconstruct the physical LensShadingMap; the app's NORM030 decomposition and
whole-frame interpolation are applied, rather than blindly applying all opcodes.
This is an offline metadata replay, not proof of capture-time HAL parity.
"""
import struct
import numpy as np
import tifffile

PATTERNS={(0,1,1,2):0,(1,0,2,1):1,(1,2,0,1):2,(2,1,1,0):3}

def rational(t):
    v=t.value
    if t.dtype in (5,10):
        a=np.asarray(v,np.float64).reshape(-1,2);return a[:,0]/a[:,1]
    return np.atleast_1d(v).astype(float)

def read(path,with_noise=False):
    with tifffile.TiffFile(path) as tf:
        pg=tf.pages[0]; tags=pg.tags; raw=pg.asarray()
        h,w=raw.shape; pattern=tuple(tags['CFAPattern'].value); cfa=PATTERNS[pattern]
        black=rational(tags['BlackLevel']);white=int(rational(tags['WhiteLevel'])[0]);neutral=rational(tags['AsShotNeutral'])
        assert len(black)==4 and len(neutral)==3 and np.all(neutral>0)
        opcode=tags[51009].value;pos=4;planes={};descriptors=[]
        for _ in range(struct.unpack_from('>I',opcode)[0]):
            op,version,flags,n=struct.unpack_from('>4I',opcode,pos);pos+=16;b=opcode[pos:pos+n];pos+=n
            assert op==9,'Only the four Android GainMaps are supported'
            fields=struct.unpack_from('>10I4dI',b)
            top,left,bottom,right,plane,plane_count,row_pitch,col_pitch,mh,mw,dy,dx,oy,ox,mp=fields
            assert top in (0,1) and left in (0,1) and row_pitch==col_pitch==2 and plane_count==mp==1
            assert plane==0 and bottom==h-1 and right==w-1 and oy==ox==0
            assert abs(dy-1/(mh-1))<1e-12 and abs(dx-1/(mw-1))<1e-12
            assert (top,left) not in planes and len(b)==76+4*mh*mw
            planes[top,left]=np.frombuffer(b,dtype='>f4',offset=76).astype(np.float64).reshape(mh,mw)
            descriptors.append(list(fields))
        assert len(planes)==4 and pos==len(opcode)
        grid=np.stack([planes[y,x] for y,x in [(0,0),(0,1),(1,0),(1,1)]],axis=-1)
        # Metadata matters: record actual ISO; no device-specific x2 correction here.
        meta=dict(name=path.name,model=tags['Model'].value,iso=int(rational(tags['ISOSpeedRatings'])[0]),
                  exposure_seconds=float(rational(tags['ExposureTime'])[0]),cfa=cfa,cfa_pattern=list(pattern),
                  neutral=neutral.tolist(),white=white,black=black.tolist(),shape=[h,w],
                  focal_length_mm=float(rational(tags['FocalLength'])[0]),
                  noise_profile=list(tags['NoiseProfile'].value) if 'NoiseProfile' in tags else None,
                  gainmap_shape=list(grid.shape),gainmap_max=float(grid.max()))
    assert np.all(np.isfinite(grid)) and np.all(grid>0)
    if with_noise:
        profile=np.asarray(meta['noise_profile'],dtype=float)
        if profile.shape!=(6,) or not np.all(np.isfinite(profile)) or np.any(profile<0):
            raise ValueError('A finite nonnegative three-plane DNG NoiseProfile is required')
        profile=profile.reshape(3,2);variance=np.empty(raw.shape,np.float32);censored=np.empty(raw.shape,bool)
    # Same geometric-mean common gain and outside-center median as Java.
    common=np.exp(np.log(grid).sum(axis=2)*.25)
    mh,mw=common.shape;yy,xx=np.indices((mh,mw))
    outside=~((xx>=mw*.25)&(xx<mw*.75)&(yy>=mh*.25)&(yy<mh*.75))
    outside_ev=float(np.median(np.log(common[outside])/np.log(2.0)))
    alpha=1.0 if outside_ev<=1e-12 else min(1.0,max(0.0,.30/outside_ev))
    decomposed=grid/common[:,:,None]*np.exp(alpha*np.log(common))[:,:,None]
    scale=float(decomposed.max())
    # Normalize using float32 operations, matching normalizeRangeNative.
    norm=np.empty(raw.shape,np.uint16)
    for y in range(2):
        for x in range(2):
            k=y*2+x;bl=np.float32(black[k]);den=np.float32(max(1.0,np.float32(white)-bl))
            v=np.clip((raw[y::2,x::2].astype(np.float32)-bl)/den,np.float32(0),np.float32(1))
            norm[y::2,x::2]=np.floor(v*np.float32(65535)+np.float32(.5)).astype(np.uint16)
            if with_noise:
                slope,offset=profile[pattern[k]]
                variance[y::2,x::2]=slope*v+offset
                censored[y::2,x::2]=(raw[y::2,x::2]>=white)|(raw[y::2,x::2]<=bl)
    # Coordinates span the full image before any crop. Quantize only after shading.
    xg=np.arange(w)*(mw-1.0)/(w-1.0);xi=np.floor(xg).astype(int);xj=np.minimum(mw-1,xi+1);xf=xg-xi
    for y in range(h):
        yg=y*(mh-1.0)/(h-1.0);yi=int(np.floor(yg));yj=min(mh-1,yi+1);yf=yg-yi
        p=(y&1)*2+(np.arange(w)&1)
        g0=decomposed[yi,xi,p]+xf*(decomposed[yi,xj,p]-decomposed[yi,xi,p])
        g1=decomposed[yj,xi,p]+xf*(decomposed[yj,xj,p]-decomposed[yj,xi,p])
        gain=g0+yf*(g1-g0)
        v=(norm[y].astype(np.float64)/65535.0)*gain/scale
        assert v.min()>=-1e-12 and v.max()<=1+1e-12
        norm[y]=np.floor(np.clip(v,0,1)*65535+.5).astype(np.uint16)
        if with_noise:variance[y]*=(gain/scale*16383.)**2
    meta.update(norm030_alpha=alpha,norm030_outside_ev=outside_ev,representation_scale=scale)
    return (norm,meta,dict(raw_variance14=variance,censored=censored)) if with_noise else (norm,meta)
