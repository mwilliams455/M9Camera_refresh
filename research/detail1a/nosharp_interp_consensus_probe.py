"""M9DETAIL1X: reconcile two no-Sharp R/B interpolation estimates in common/opponent space.

DETAIL1W proved:
- D green guidance == native no-Sharp MHC green guidance at the R/B anchors.
- The interpolation operator is the active variable.
- D cross-phase interpolation tends false magenta.
- Direct same-phase interpolation removes most false magenta but tends false green.

This probe derives both full-resolution colour-difference fields from the same
measured DETAIL1D anchors, then decomposes them into:
    sum      = (R-G) + (B-G)       # 2x common magenta/green component
    opponent = (R-G) - (B-G)       # red-vs-blue hue component

The opponent component remains EXACTLY the current D value. Only the common
component is reconciled where D and direct interpolation disagree in sign.
No Sharp, Noise2, hue/subject/foliage classifier or Android/APK change.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

SPECS={
    'conflict25':dict(kind='blend',alpha=.25,min_dis=0),
    'conflict50':dict(kind='blend',alpha=.50,min_dis=0),
    'conflict75':dict(kind='blend',alpha=.75,min_dis=0),
    'conflict100':dict(kind='blend',alpha=1.0,min_dis=0),
    'conflict_zero':dict(kind='zero',alpha=0.,min_dis=0),
    'conflict64_50':dict(kind='blend',alpha=.50,min_dis=64),
    'conflict256_50':dict(kind='blend',alpha=.50,min_dis=256),
    'all25':dict(kind='allblend',alpha=.25,min_dis=0),
    'all50':dict(kind='allblend',alpha=.50,min_dis=0),
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
        if rc:raise RuntimeError((name,rc))
        return out

def phase_field(src,py,px):
    """Exact signed-floor separable phase interpolation."""
    a=np.asarray(src,np.int64);h,w=a.shape
    ys=np.arange(h)[:,None];xs=np.arange(w)[None,:]
    prow=(ys&1)==py;pcol=(xs&1)==px
    row=np.zeros((h,w),np.int64)
    exact=prow&pcol
    row[exact]=a[exact]
    mid=prow&~pcol
    hv=floor2(np.roll(a,1,1)+np.roll(a,-1,1))
    row[mid]=hv[mid]
    out=row.copy()
    vm=(~prow).repeat(w,axis=1)
    vv=floor2(np.roll(row,1,0)+np.roll(row,-1,0))
    out[vm]=vv[vm]
    out[:2]=0;out[-2:]=0;out[:,:2]=0;out[:,-2:]=0
    return out

def fields_from_D(carrier,cfa):
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    # Matches rb_domain_consume: R reads opposite red phase, B opposite blue phase.
    r=phase_field(carrier,1-ry,1-rx)
    b=phase_field(carrier,ry,rx)
    return r,b

def fields_direct(diff,cfa):
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    return phase_field(diff,ry,rx),phase_field(diff,1-ry,1-rx)

def fields_to_rgb(rfield,bfield,base,nr,nb):
    sg=q14(base[...,1])
    out=np.array(base,copy=True)
    out[...,0]=q16(llround(nr*(sg+rfield)))
    out[...,2]=q16(llround(nb*(sg+bfield)))
    out[:10]=base[:10];out[-10:]=base[-10:];out[:,:10]=base[:,:10];out[:,-10:]=base[:,-10:]
    assert np.array_equal(out[...,1],base[...,1])
    return out

def reconcile(rD,bD,rI,bI,spec):
    sD=rD.astype(np.int64)+bD.astype(np.int64)
    oD=rD.astype(np.int64)-bD.astype(np.int64)
    sI=rI.astype(np.int64)+bI.astype(np.int64)
    disagreement=np.abs(sD-sI)
    conflict=((sD==0)|(sI==0)|((sD<0)&(sI>0))|((sD>0)&(sI<0)))
    if spec['kind']=='allblend':
        gate=disagreement>=spec['min_dis']
        target=llround(sD+spec['alpha']*(sI-sD))
    else:
        gate=conflict&(disagreement>=spec['min_dis'])
        if spec['kind']=='zero':
            target=np.zeros_like(sD)
        elif spec['kind']=='blend':
            target=llround(sD+spec['alpha']*(sI-sD))
        else:
            raise ValueError(spec['kind'])
    s=sD.copy();s[gate]=target[gate]
    r=llround((s+oD)/2.)
    b=llround((s-oD)/2.)
    # Opponent preservation must be exact modulo unavoidable integer parity.
    opp_new=r-b
    assert np.max(np.abs(opp_new-oD))<=1
    return r,b,gate,disagreement

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
    n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
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

                        base=native.render('nosharp',norm,n[0],n[2],cfa)
                        _,diff,carrier,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(carrier,base,cfa,n[0],n[2])
                        rD,bD=fields_from_D(carrier,cfa)
                        dcam2=fields_to_rgb(rD,bD,base,n[0],n[2])
                        d_parity &= np.array_equal(dcam2,dcam)
                        assert np.array_equal(dcam2,dcam),'D field reconstruction parity failed'

                        rI,bI=fields_direct(diff,cfa)
                        direct=fields_to_rgb(rI,bI,base,n[0],n[2])
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n),'direct':metrics(direct,truth,scale,n)}
                        stats={}
                        for name,spec in SPECS.items():
                            r,b,gate,dis=reconcile(rD,bD,rI,bI,spec)
                            cam=fields_to_rgb(r,b,base,n[0],n[2])
                            mm[name]=metrics(cam,truth,scale,n)
                            stats[name]=dict(gate_fraction=float(gate.mean()),
                                changed_pixels=int(np.count_nonzero(gate)),
                                disagreement_mean=float(dis[gate].mean()) if np.any(gate) else 0.,
                                disagreement_max=int(dis[gate].max()) if np.any(gate) else 0)
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm,gates=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode in SPECS:
        summary[mode]={'spec':SPECS[mode]}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows])
            c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),
                cases_worse=int((delta>1e-12).sum()),mean_D=float(d.mean()),
                mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
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
        summary[mode]['gate']=dict(mean_gate_fraction=float(np.mean([r['gates'][mode]['gate_fraction'] for r in rows])),
            changed_pixels_total=int(sum(r['gates'][mode]['changed_pixels'] for r in rows)))

    strict=[m for m in SPECS
            if summary[m]['false_magenta_excess_fraction']['cases_worse']==0
            and summary[m]['false_green_excess_fraction']['cases_worse']==0]
    return dict(schema='m9.detail1x.nosharp_interp_consensus.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,specs=SPECS,
        d_field_rgb_byte_parity=bool(d_parity),strict_zero_false_chroma_regression=strict,
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Sharp disabled. Two interpolation estimates from identical D colour anchors are reconciled only in their common R/B-vs-G component; D opponent R-vs-B component preserved to <=1 q14 parity unit. No Noise2/hue/subject classifier or APK mutation.')

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
