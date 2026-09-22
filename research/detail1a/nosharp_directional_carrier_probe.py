"""M9DETAIL2A: no-Sharp directional construction of the DETAIL1D R/B carrier.

DETAIL1W proved D's green guide is not the active fault. DETAIL1Y/Z then showed
that post-interpolation consensus needs increasingly broad evidence and still
misses one thin bright-cool branch fixture. This probe moves to the exact D
operation that mixes across that geometry:

    carrier = (dNW + dNE + dSW + dSE) / 4

At each opposite-phase carrier site, form the two diagonal pair estimates:
    p1 = (dNW + dSE)/2
    p2 = (dNE + dSW)/2

Use the no-Sharp green geometry at the same sites to estimate which diagonal
stays on the same spatial structure. Test hard/soft directional targets, with
optional raw-clip locality and sign-safe projection between current carrier and
zero. Sharp and Noise2 stay disabled. No hue/subject/foliage classifier.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

SPECS={
    'soft_c05_d64_a50':dict(kind='soft',conf=.05,dmin=64,alpha=.50,clip=0,safe=False),
    'hard_c05_d64_a50':dict(kind='hard',conf=.05,dmin=64,alpha=.50,clip=0,safe=False),
    'safe_soft_c05_d64_a50':dict(kind='soft',conf=.05,dmin=64,alpha=.50,clip=0,safe=True),
    'safe_hard_c05_d64_a50':dict(kind='hard',conf=.05,dmin=64,alpha=.50,clip=0,safe=True),
    'safe_soft_c10_d256_a100':dict(kind='soft',conf=.10,dmin=256,alpha=1.,clip=0,safe=True),
    'safe_hard_c10_d256_a100':dict(kind='hard',conf=.10,dmin=256,alpha=1.,clip=0,safe=True),
    'clip4_safe_soft_c05_d64_a100':dict(kind='soft',conf=.05,dmin=64,alpha=1.,clip=4,safe=True),
    'clip4_safe_hard_c05_d64_a100':dict(kind='hard',conf=.05,dmin=64,alpha=1.,clip=4,safe=True),
    'clip2_safe_soft_c05_d64_a100':dict(kind='soft',conf=.05,dmin=64,alpha=1.,clip=2,safe=True),
    'clip2_safe_hard_c05_d64_a100':dict(kind='hard',conf=.05,dmin=64,alpha=1.,clip=2,safe=True),
}

def floor2(a):
    a=np.asarray(a,np.int64)
    return np.where(a>=0,a//2,-((-a+1)//2))

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

class NativeNoSharp:
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
        body=spatial.replace(old,'const int corr=0;')
        cp=build/'nosharp.cpp';so=build/'nosharp.so'
        cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
        subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',
                        str(cp),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
        self.lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,
                                  C.c_float,C.c_float,C.c_void_p,C.c_int]
        self.lib.replay.restype=C.c_int;self.source_sha256=h

    def render(self,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.lib.replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError(('native noSharp replay',rc))
        return out

def directional(diff,green,cfa):
    d=np.asarray(diff,np.int64);g=np.asarray(green,np.int64)
    nw=np.roll(np.roll(d,1,0),1,1);ne=np.roll(np.roll(d,1,0),-1,1)
    sw=np.roll(np.roll(d,-1,0),1,1);se=np.roll(np.roll(d,-1,0),-1,1)
    p1=floor2(nw+se);p2=floor2(ne+sw)

    gnw=np.roll(np.roll(g,1,0),1,1);gne=np.roll(np.roll(g,1,0),-1,1)
    gsw=np.roll(np.roll(g,-1,0),1,1);gse=np.roll(np.roll(g,-1,0),-1,1)
    c1=np.abs(gnw-gse)+np.abs(floor2(gnw+gse)-g)
    c2=np.abs(gne-gsw)+np.abs(floor2(gne+gsw)-g)

    hard=np.where(c1<c2,p1,np.where(c2<c1,p2,floor2(p1+p2)))
    w1=1./(1.+c1.astype(np.float64));w2=1./(1.+c2.astype(np.float64))
    soft=llround((w1*p1+w2*p2)/(w1+w2))
    conf=np.abs(c1-c2)/(c1+c2+1.)
    dis=np.abs(p1-p2)
    red,blue,gm=cfa_masks(diff.shape,cfa)
    rb=red|blue
    rb[:3]=False;rb[-3:]=False;rb[:,:3]=False;rb[:,-3:]=False
    return hard,soft,conf,dis,rb

def project_safe(target,current):
    t=np.asarray(target,np.int64);c=np.asarray(current,np.int64)
    return np.where(c>0,np.clip(t,0,c),np.where(c<0,np.clip(t,c,0),0))

def candidate(current,hard,soft,conf,dis,rb,sensor,spec):
    target=soft if spec['kind']=='soft' else hard
    gate=rb&(conf>=spec['conf'])&(dis>=spec['dmin'])
    if spec['clip']:
        clipped=sensor>=1023
        support=maximum_filter(clipped.astype(np.uint8),
                               size=2*spec['clip']+1,mode='constant')>0
        gate&=support
    mixed=llround(current.astype(np.int64)+spec['alpha']*(target-current))
    if spec['safe']:
        mixed=project_safe(mixed,current)
    out=current.astype(np.int64).copy()
    out[gate]=mixed[gate]
    return out.astype(np.int32),gate

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
    rows=[]
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
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)

                        base=native.render(norm,n[0],n[2],cfa)
                        green,diff,current,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        hard,soft,conf,dis,rb=directional(diff,green,cfa)
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        for name,spec in SPECS.items():
                            ca,gate=candidate(current,hard,soft,conf,dis,rb,sensor,spec)
                            cam=probe.consume(ca,base,cfa,n[0],n[2])
                            assert np.array_equal(cam[...,1],base[...,1])
                            mm[name]=metrics(cam,truth,scale,n)
                            stats[name]=dict(
                                gate_fraction=float(gate.mean()),
                                changed_carrier_samples=int(np.count_nonzero(ca!=current)),
                                confidence_mean=float(conf[gate].mean()) if np.any(gate) else 0.,
                                disagreement_mean=float(dis[gate].mean()) if np.any(gate) else 0.)
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm,gates=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode,spec in SPECS.items():
        summary[mode]={'spec':spec}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            a=np.array([r['metrics']['D'][key] for r in rows])
            b=np.array([r['metrics'][mode][key] for r in rows]);delta=b-a
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),
                cases_worse=int((delta>1e-12).sum()),mean_D=float(a.mean()),
                mean_candidate=float(b.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green_sub=np.array([r['subject']=='green' for r in rows])
        mag=np.array([r['subject'] in ('magenta','bright_magenta') for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),
                           ('clipped_green',clipped&green_sub),('clipped_magenta',clipped&mag),
                           ('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                a=np.array([r['metrics']['D'][key] for r in rows])[sel]
                b=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_cases_improved']=int((b<a-1e-12).sum())
                vals[key+'_cases_worse']=int((b>a+1e-12).sum())
                vals[key+'_mean_D']=float(a.mean()) if a.size else 0.
                vals[key+'_mean_candidate']=float(b.mean()) if b.size else 0.
            summary[mode][subset]=vals
        summary[mode]['gate']=dict(
            mean_gate_fraction=float(np.mean([r['gates'][mode]['gate_fraction'] for r in rows])),
            changed_carrier_total=int(sum(r['gates'][mode]['changed_carrier_samples'] for r in rows)))

    strict=[m for m in SPECS
            if summary[m]['false_magenta_excess_fraction']['cases_worse']==0
            and summary[m]['false_green_excess_fraction']['cases_worse']==0]
    return dict(schema='m9.detail2a.nosharp_directional_carrier.v1',
        case_count=len(rows),cfas=list(cfas),neutral=n.tolist(),representation_scale=scale,
        specs=SPECS,strict_zero_false_chroma_regression=strict,
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Sharp/Noise2 disabled. Replaces only D four-diagonal carrier average with green-geometry directional pair estimates under explicit gates; sign-safe variants cannot strengthen or invert carrier chroma. No hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativeNoSharp(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(strict_zero_false_chroma_regression=result['strict_zero_false_chroma_regression'],
        summary=result['summary']),indent=2))

if __name__=='__main__':main()
