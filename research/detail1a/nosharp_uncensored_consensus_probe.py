"""M9DETAIL1Y: no-Sharp interpolation consensus protected by uncensored RAW anchors.

DETAIL1X showed that D-vs-direct common-chroma reconciliation can reduce false
magenta without magenta regressions, but can create false green on real coloured
fine structure.  This probe adds a symmetric measurement certificate.

Only fully uncensored native R/B difference anchors contribute evidence:
  - the colour CFA sample must be below sensor white
  - all cardinal green samples used by the D green guide must be below white

For each output pixel, local uncensored R and B anchor means form:
    measured_common = mean(R-G) + mean(B-G)

A D/direct interpolation conflict may be reconciled only when this measured
local evidence is available AND does not strongly support the current D common
chroma sign. Positive and negative chroma are treated symmetrically.

Sharp and Noise2 remain disabled. D opponent R-vs-B hue component stays exact
to integer parity. No hue/subject/foliage classifier and no Android/APK change.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter,convolve

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

MIN_COUNT=2
SPECS={
    'r4_t64_a25':dict(radius=4,threshold=64,alpha=.25),
    'r4_t128_a25':dict(radius=4,threshold=128,alpha=.25),
    'r4_t256_a25':dict(radius=4,threshold=256,alpha=.25),
    'r4_t512_a25':dict(radius=4,threshold=512,alpha=.25),
    'r8_t64_a25':dict(radius=8,threshold=64,alpha=.25),
    'r8_t128_a25':dict(radius=8,threshold=128,alpha=.25),
    'r8_t256_a25':dict(radius=8,threshold=256,alpha=.25),
    'r8_t512_a25':dict(radius=8,threshold=512,alpha=.25),
    'r4_t128_a50':dict(radius=4,threshold=128,alpha=.50),
    'r8_t128_a50':dict(radius=8,threshold=128,alpha=.50),
}

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
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        assert spatial.count(old)==1
        variants={'nosharp':spatial.replace(old,'const int corr=0;')}
        self.libs={};self.source_sha256=h
        for name,body in variants.items():
            cp=build/(name+'.cpp');so=build/(name+'.so')
            cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',
                            str(cp),'-o',str(so)],check=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,
                                 C.c_float,C.c_float,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int;self.libs[name]=lib

    def render(self,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.libs['nosharp'].replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError(('native noSharp',rc))
        return out

def phase_field(src,py,px):
    a=np.asarray(src,np.int64);h,w=a.shape
    ys=np.arange(h)[:,None];xs=np.arange(w)[None,:]
    prow=(ys&1)==py;pcol=(xs&1)==px
    row=np.zeros((h,w),np.int64)
    exact=prow&pcol;row[exact]=a[exact]
    mid=prow&~pcol
    hv=floor2(np.roll(a,1,1)+np.roll(a,-1,1));row[mid]=hv[mid]
    out=row.copy()
    vm=(~prow).repeat(w,axis=1)
    vv=floor2(np.roll(row,1,0)+np.roll(row,-1,0));out[vm]=vv[vm]
    out[:2]=0;out[-2:]=0;out[:,:2]=0;out[:,-2:]=0
    return out

def fields_from_D(carrier,cfa):
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    return phase_field(carrier,1-ry,1-rx),phase_field(carrier,ry,rx)

def fields_direct(diff,cfa):
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    return phase_field(diff,ry,rx),phase_field(diff,1-ry,1-rx)

def fields_to_rgb(rfield,bfield,base,nr,nb):
    sg=q14(base[...,1]);out=np.array(base,copy=True)
    out[...,0]=q16(llround(nr*(sg+rfield)))
    out[...,2]=q16(llround(nb*(sg+bfield)))
    out[:10]=base[:10];out[-10:]=base[-10:];out[:,:10]=base[:,:10];out[:,-10:]=base[:,-10:]
    assert np.array_equal(out[...,1],base[...,1])
    return out

def uncensored_masks(sensor,cfa,white=1023):
    red,blue,green=cfa_masks(sensor.shape,cfa)
    clipped=sensor>=white
    gclip=(np.roll(clipped,1,0)|np.roll(clipped,-1,0)|
           np.roll(clipped,1,1)|np.roll(clipped,-1,1))
    valid_r=red&~clipped&~gclip
    valid_b=blue&~clipped&~gclip
    for m in (valid_r,valid_b):
        m[:2]=False;m[-2:]=False;m[:,:2]=False;m[:,-2:]=False
    return valid_r,valid_b

def local_common(diff_unshrunk,sensor,cfa,radius):
    vr,vb=uncensored_masks(sensor,cfa)
    k=np.ones((2*radius+1,2*radius+1),np.float64)
    d=np.asarray(diff_unshrunk,np.float64)
    sr=convolve(d*vr,k,mode='constant',cval=0.)
    sb=convolve(d*vb,k,mode='constant',cval=0.)
    cr=convolve(vr.astype(np.float64),k,mode='constant',cval=0.)
    cb=convolve(vb.astype(np.float64),k,mode='constant',cval=0.)
    mr=np.divide(sr,cr,out=np.zeros_like(sr),where=cr>0)
    mb=np.divide(sb,cb,out=np.zeros_like(sb),where=cb>0)
    available=(cr>=MIN_COUNT)&(cb>=MIN_COUNT)
    return mr+mb,available,cr,cb

def reconcile(rD,bD,rI,bI,measured_common,available,spec):
    sD=rD.astype(np.int64)+bD.astype(np.int64)
    oD=rD.astype(np.int64)-bD.astype(np.int64)
    sI=rI.astype(np.int64)+bI.astype(np.int64)
    conflict=((sD==0)|(sI==0)|((sD<0)&(sI>0))|((sD>0)&(sI<0)))
    same_sign=((measured_common>0)&(sD>0))|((measured_common<0)&(sD<0))
    protect=available&same_sign&(np.abs(measured_common)>=spec['threshold'])
    gate=conflict&available&~protect
    target=llround(sD+spec['alpha']*(sI-sD))
    s=sD.copy();s[gate]=target[gate]
    r=llround((s+oD)/2.);b=llround((s-oD)/2.)
    assert np.max(np.abs((r-b)-oD))<=1
    return r,b,gate,protect,conflict,available

def metrics(cam,truth,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16];t=truth[16:-16,16:-16]
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
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[];d_parity=True
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(np.float64)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)

                        base=native.render(norm,n[0],n[2],cfa)
                        _,diff_unshrunk,_,_=probe.stages(norm,cfa,n[0],n[2],shrink=False)
                        _,diff,carrier,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(carrier,base,cfa,n[0],n[2])
                        rD,bD=fields_from_D(carrier,cfa)
                        dcheck=fields_to_rgb(rD,bD,base,n[0],n[2])
                        d_parity &= np.array_equal(dcheck,dcam)
                        assert np.array_equal(dcheck,dcam)
                        rI,bI=fields_direct(diff,cfa)
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        evidence_cache={}
                        for name,spec in SPECS.items():
                            key=spec['radius']
                            if key not in evidence_cache:
                                evidence_cache[key]=local_common(diff_unshrunk,sensor,cfa,key)
                            measured,avail,cr,cb=evidence_cache[key]
                            r,b,gate,protect,conflict,available=reconcile(rD,bD,rI,bI,measured,avail,spec)
                            cam=fields_to_rgb(r,b,base,n[0],n[2])
                            mm[name]=metrics(cam,truth,scale,n)
                            stats[name]=dict(
                                gate_fraction=float(gate.mean()),
                                protect_fraction=float(protect.mean()),
                                conflict_fraction=float(conflict.mean()),
                                evidence_available_fraction=float(available.mean()),
                                changed_pixels=int(gate.sum()),
                                protected_pixels=int(protect.sum()),
                                mean_abs_measured_common=float(np.abs(measured[available]).mean()) if np.any(available) else 0.,
                                mean_red_anchor_count=float(cr.mean()),
                                mean_blue_anchor_count=float(cb.mean()))
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm,gates=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode,spec in SPECS.items():
        summary[mode]={'spec':spec}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows]);c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green=np.array([r['subject']=='green' for r in rows])
        mag=np.array([r['subject'] in ('magenta','bright_magenta') for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),
                           ('clipped_green',clipped&green),('clipped_magenta',clipped&mag),
                           ('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                d=np.array([r['metrics']['D'][key] for r in rows])[sel]
                c=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_cases_improved']=int((c<d-1e-12).sum())
                vals[key+'_cases_worse']=int((c>d+1e-12).sum())
                vals[key+'_mean_D']=float(d.mean()) if d.size else 0.
                vals[key+'_mean_candidate']=float(c.mean()) if c.size else 0.
            summary[mode][subset]=vals
        summary[mode]['gate']=dict(
            mean_gate_fraction=float(np.mean([r['gates'][mode]['gate_fraction'] for r in rows])),
            mean_protect_fraction=float(np.mean([r['gates'][mode]['protect_fraction'] for r in rows])),
            mean_evidence_available_fraction=float(np.mean([r['gates'][mode]['evidence_available_fraction'] for r in rows])),
            changed_pixels_total=int(sum(r['gates'][mode]['changed_pixels'] for r in rows)),
            protected_pixels_total=int(sum(r['gates'][mode]['protected_pixels'] for r in rows)))

    strict=[m for m in SPECS
            if summary[m]['false_magenta_excess_fraction']['cases_worse']==0
            and summary[m]['false_green_excess_fraction']['cases_worse']==0]
    return dict(schema='m9.detail1y.nosharp_uncensored_consensus.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,min_uncensored_anchor_count=MIN_COUNT,specs=SPECS,
        d_field_rgb_byte_parity=bool(d_parity),strict_zero_false_chroma_regression=strict,
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Sharp disabled. D/direct interpolation conflict correction is protected symmetrically by local common chroma estimated only from fully uncensored native R/B anchors. D opponent component preserved to <=1 q14 parity unit. No Noise2/hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativePair(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(d_field_rgb_byte_parity=result['d_field_rgb_byte_parity'],
        strict_zero_false_chroma_regression=result['strict_zero_false_chroma_regression'],
        summary=result['summary']),indent=2))

if __name__=='__main__':main()
