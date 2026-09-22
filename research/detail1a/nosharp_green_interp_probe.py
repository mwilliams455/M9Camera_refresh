"""M9DETAIL1W: no-Sharp factorial for green guidance vs R/B interpolation.

Sharp is deliberately disabled in the active diagnostic candidates.

Factorial axes:
  green guide:
    D   = DETAIL1D cardinal/diagonal green estimate
    MHC = exact native no-Sharp MHC green at native R/B sites
  colour interpolation:
    D   = DETAIL1D diagonal cross-phase carrier + current consumer
    DIR = direct separable bilinear interpolation from native same-colour
          R-G/B-G anchors, with signed floor at each half-step

Controls:
  MHC_nosharp = exact frozen native demosaic with Sharp correction forced to zero
  D_nosharp   = current DETAIL1D carrier/consumer on the same no-Sharp base
  D_sharp_ref = current DETAIL1D on the ordinary Sharp base, reference only

All candidates keep current Co=2 shrink and use the same no-Sharp final green.
No hue/subject/foliage classifier, no Noise2, no Android/APK change.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

MODES=('MHC_nosharp','D_nosharp','MHCguide_Dinterp',
       'Dguide_direct','MHCguide_direct','D_sharp_ref')

def q14(v):
    a=np.asarray(v,dtype=np.uint64)
    return ((a*16383+32767)//65535).astype(np.int64)

def q16(v):
    a=np.clip(np.asarray(v,dtype=np.int64),0,16383)
    return ((a*65535+8191)//16383).astype(np.uint16)

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

def floor2(a):
    a=np.asarray(a,np.int64)
    return np.where(a>=0,a//2,-((-a+1)//2))

class NativePair:
    def __init__(self,repo,assembled,build):
        build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        rel='app/src/main/cpp/m9color_jni.cpp'
        raw=(assembled/rel).read_bytes();h=hashlib.sha256(raw).hexdigest()
        assert h==manifest['frozen'][rel],(h,manifest['frozen'][rel])
        s=raw.decode()
        helpers=s[s.index('inline int64_t clipl'):s.index('// SKYCHROMA1A diagnostic only')]
        spatial=s[s.index('// SHARPNESS_CLOSURETEST1A'):s.index(
            'extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect')]
        assert spatial.count('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaic')==2
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        assert spatial.count(old)==1,'native Sharp block changed'
        variants={'sharp':spatial,'nosharp':spatial.replace(old,'const int corr=0;')}
        self.libs={};self.source_sha256=h
        for name,body in variants.items():
            cp=build/(name+'.cpp');so=build/(name+'.so')
            cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',
                            str(cp),'-o',str(so)],check=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,
                                 C.c_float,C.c_float,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int
            self.libs[name]=lib

    def render(self,name,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.libs[name].replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError((name,'native replay',rc))
        return out

def shrink_co(d,a):
    d=np.asarray(d,np.int64);a=np.asarray(a,np.int64)
    mag=np.abs(d)
    v=np.maximum(mag-(a>>2),0)
    return np.where(mag<a,np.where(d<0,-v,v),d)

def guide_diff(norm,cfa,nr,nb,guide,uncertainty):
    z=q14(norm)
    red,blue,green=cfa_masks(norm.shape,cfa)
    nc=np.where(red,nr,np.where(blue,nb,1.))
    rawc=llround(z.astype(np.float64)/nc)
    d=rawc-np.asarray(guide,np.int64)
    d=shrink_co(d,uncertainty)
    valid=red|blue
    valid[:2]=False;valid[-2:]=False;valid[:,:2]=False;valid[:,-2:]=False
    return np.where(valid,d,0).astype(np.int32)

def diagonal_carrier(diff,cfa):
    d=np.asarray(diff,np.int64)
    red,blue,green=cfa_masks(diff.shape,cfa)
    total=(np.roll(np.roll(d,1,0),1,1)+np.roll(np.roll(d,1,0),-1,1)+
           np.roll(np.roll(d,-1,0),1,1)+np.roll(np.roll(d,-1,0),-1,1))
    ca=total//4
    valid=(red|blue)
    valid[:3]=False;valid[-3:]=False;valid[:,:3]=False;valid[:,-3:]=False
    return np.where(valid,ca,0).astype(np.int32)

def direct_field(diff,py,px):
    """Signed-floor separable 2x Bayer-phase bilinear interpolation."""
    d=np.asarray(diff,np.int64);h,w=d.shape
    row=np.zeros((h,w),np.int64)
    ys=np.arange(h)[:,None];xs=np.arange(w)[None,:]
    phase_row=(ys&1)==py
    phase_col=(xs&1)==px
    exact=phase_row&phase_col
    row[exact]=d[exact]
    # Horizontal half positions are only meaningful on the native phase rows.
    mid=phase_row&~phase_col
    left=np.roll(d,1,1);right=np.roll(d,-1,1)
    hv=floor2(left+right)
    row[mid]=hv[mid]
    # Then vertical interpolation between completed native rows.
    out=row.copy()
    vm=~phase_row
    up=np.roll(row,1,0);down=np.roll(row,-1,0)
    vv=floor2(up+down)
    out[vm.repeat(w,axis=1)]=vv[vm.repeat(w,axis=1)]
    out[:2]=0;out[-2:]=0;out[:,:2]=0;out[:,-2:]=0
    return out

def direct_consume(diff,base,cfa,nr,nb):
    h,w=diff.shape
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    red_field=direct_field(diff,ry,rx)
    blue_field=direct_field(diff,1-ry,1-rx)
    sg=q14(base[...,1])
    out=np.array(base,copy=True)
    r=llround(nr*(sg+red_field))
    b=llround(nb*(sg+blue_field))
    out[...,0]=q16(r);out[...,2]=q16(b)
    # Match current consumer's untouched perimeter.
    out[:10]=base[:10];out[-10:]=base[-10:];out[:,:10]=base[:,:10];out[:,-10:]=base[:,-10:]
    assert np.array_equal(out[...,1],base[...,1])
    return out

def metrics(cam,truth,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16]
    t=truth[16:-16,16:-16]
    rd=np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)
    td=np.stack([t[...,0]-t[...,1],t[...,2]-t[...,1]],axis=-1)
    false_mag=(np.minimum(rd[...,0],rd[...,1])-np.minimum(td[...,0],td[...,1])>.02)
    rg=np.minimum(z[...,1]-z[...,0],z[...,1]-z[...,2])
    tg=np.minimum(t[...,1]-t[...,0],t[...,1]-t[...,2])
    false_green=(rg-tg>.02)
    return dict(scene_rgb_rms=float(np.sqrt(np.mean((z-t)**2))),
                chroma_rms=float(np.sqrt(np.mean((rd-td)**2))),
                false_magenta_excess_fraction=float(false_mag.mean()),
                false_green_excess_fraction=float(false_green.mean()))

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192))
    n=np.array([.41796875,1.,.6435546875])
    scale=1.6105431518598052
    rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43
            mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(np.float64)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)

                        base_no=native.render('nosharp',norm,n[0],n[2],cfa)
                        base_sh=native.render('sharp',norm,n[0],n[2],cfa)

                        gd,_,_,unc=probe.stages(norm,cfa,n[0],n[2],shrink=False)
                        _,dd,current,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        d_no=probe.consume(current,base_no,cfa,n[0],n[2])
                        d_sh=probe.consume(current,base_sh,cfa,n[0],n[2])

                        gmhc=q14(base_no[...,1]).astype(np.int64)
                        d_mhc=guide_diff(norm,cfa,n[0],n[2],gmhc,unc)
                        carrier_mhc=diagonal_carrier(d_mhc,cfa)
                        mhc_d=probe.consume(carrier_mhc,base_no,cfa,n[0],n[2])

                        d_direct=direct_consume(dd,base_no,cfa,n[0],n[2])
                        mhc_direct=direct_consume(d_mhc,base_no,cfa,n[0],n[2])

                        truth=np.clip(scene,0,1)
                        cams={
                            'MHC_nosharp':base_no,
                            'D_nosharp':d_no,
                            'MHCguide_Dinterp':mhc_d,
                            'Dguide_direct':d_direct,
                            'MHCguide_direct':mhc_direct,
                            'D_sharp_ref':d_sh,
                        }
                        mm={k:metrics(v,truth,scale,n) for k,v in cams.items()}
                        rb=red|blue
                        interior=rb.copy();interior[:4]=False;interior[-4:]=False;interior[:,:4]=False;interior[:,-4:]=False
                        gd_i=np.asarray(gd,np.int64)
                        guide_delta=gmhc-gd_i
                        rows.append(dict(
                            cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),
                            guide_mean_abs_q14=float(np.abs(guide_delta[interior]).mean()),
                            guide_p95_abs_q14=float(np.percentile(np.abs(guide_delta[interior]),95)),
                            metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode in MODES:
        summary[mode]={}
        for ref in ('D_nosharp','MHC_nosharp'):
            summary[mode][ref]={}
            for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
                a=np.array([r['metrics'][ref][key] for r in rows])
                b=np.array([r['metrics'][mode][key] for r in rows])
                delta=b-a
                summary[mode][ref][key]=dict(
                    cases_improved=int((delta<-1e-12).sum()),
                    cases_worse=int((delta>1e-12).sum()),
                    mean_reference=float(a.mean()),mean_candidate=float(b.mean()),
                    mean_change=float(delta.mean()),max_increase=float(delta.max()),
                    max_reduction=float((-delta).max()),
                    worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green=np.array([r['subject']=='green' for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),
                           ('clipped_green',clipped&green),('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                v=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_mean']=float(v.mean()) if v.size else 0.
            summary[mode][subset]=vals

    # Factorial diagnosis: compare guide swap at fixed D interpolation and
    # interpolation swap at fixed guide.
    contrasts={}
    pairs={
        'guide_effect_under_Dinterp':('D_nosharp','MHCguide_Dinterp'),
        'interp_effect_under_Dguide':('D_nosharp','Dguide_direct'),
        'guide_effect_under_direct':('Dguide_direct','MHCguide_direct'),
        'interp_effect_under_MHCguide':('MHCguide_Dinterp','MHCguide_direct'),
        'Sharp_reference_effect':('D_nosharp','D_sharp_ref'),
    }
    for name,(a,b) in pairs.items():
        contrasts[name]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            aa=np.array([r['metrics'][a][key] for r in rows])
            bb=np.array([r['metrics'][b][key] for r in rows])
            d=bb-aa
            contrasts[name][key]=dict(
                cases_improved=int((d<-1e-12).sum()),cases_worse=int((d>1e-12).sum()),
                mean_change=float(d.mean()),max_increase=float(d.max()),max_reduction=float((-d).max()))

    return dict(schema='m9.detail1w.nosharp_green_interp_factorial.v1',
                case_count=len(rows),cfas=list(cfas),neutral=n.tolist(),
                representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
                summary=summary,contrasts=contrasts,cases=rows,
                scope='Sharp disabled for active factorial candidates. Exact no-Sharp native MHC is control. D vs native-MHC green guidance and D cross-phase vs direct same-phase interpolation are isolated. Co shrink retained. No Noise2/hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativePair(repo,a.assembled,a.out/'native')
    probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(
        json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(contrasts=result['contrasts'],summary=result['summary']),indent=2))

if __name__=='__main__':main()
