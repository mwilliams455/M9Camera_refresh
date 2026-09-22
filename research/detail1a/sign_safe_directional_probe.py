"""M9DETAIL1U: sign-safe directional R/B carrier correction.

DETAIL1T showed that directional evidence can reduce false magenta but a free
directional update can also create small false-green excursions.  This probe
forbids that polarity trade at the carrier itself.

The directional target uses the same two diagonal colour-difference estimates
and native-green anisotropy as DETAIL1L/T.  Under the original conservative
safe gate, the target is projected onto the closed interval between the current
carrier value and zero:

    current > 0 : target = clamp(soft, 0, current)
    current < 0 : target = clamp(soft, current, 0)
    current = 0 : unchanged

Thus the operation can only reduce carrier magnitude toward neutral.  It cannot
strengthen existing chroma or cross zero into the opposite colour.  Strong
measured colour is still protected by the original min(|p1|,|p2|) <= 900 gate.

Variants compare the exact original gate globally and with exact same gate plus
RAW clipping support (any-channel or green-only, radius2/4), at 75/100% strength.
No hue, subject, foliage or wildlife classifier. Current D is exact outside the
gate; native green/ISO160 Sharp and downstream rendering are unchanged.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter

from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

CONF_MIN=.02
CONF_MAX=.28
DISAGREEMENT_MIN=2048
STRONG_COLOUR_LIMIT=900

SPECS={
    'global75':dict(clip='none',radius=0,alpha=.75),
    'global100':dict(clip='none',radius=0,alpha=1.),
    'any2_75':dict(clip='any',radius=2,alpha=.75),
    'any4_75':dict(clip='any',radius=4,alpha=.75),
    'any4_100':dict(clip='any',radius=4,alpha=1.),
    'green2_75':dict(clip='green',radius=2,alpha=.75),
    'green4_75':dict(clip='green',radius=4,alpha=.75),
    'green4_100':dict(clip='green',radius=4,alpha=1.),
}

def llround(v):
    v=np.asarray(v,np.float64)
    return np.where(v>=0,np.floor(v+.5),np.ceil(v-.5)).astype(np.int64)

def fields(diff,green,cfa):
    d=diff.astype(np.int64);g=green.astype(np.int64)
    dnw=np.roll(np.roll(d,1,0),1,1);dne=np.roll(np.roll(d,1,0),-1,1)
    dsw=np.roll(np.roll(d,-1,0),1,1);dse=np.roll(np.roll(d,-1,0),-1,1)
    p1=(dnw+dse)//2;p2=(dne+dsw)//2
    gnw=np.roll(np.roll(g,1,0),1,1);gne=np.roll(np.roll(g,1,0),-1,1)
    gsw=np.roll(np.roll(g,-1,0),1,1);gse=np.roll(np.roll(g,-1,0),-1,1)
    c1=np.abs(gnw-gse)+np.abs(((gnw+gse)//2)-g)
    c2=np.abs(gne-gsw)+np.abs(((gne+gsw)//2)-g)
    w1=1./(1.+c1.astype(np.float64));w2=1./(1.+c2.astype(np.float64))
    soft=np.floor((w1*p1+w2*p2)/(w1+w2)).astype(np.int64)
    confidence=np.abs(c1-c2)/(c1+c2+1.)
    disagreement=np.abs(p1-p2)
    minabs=np.minimum(np.abs(p1),np.abs(p2))
    red,blue,gm=cfa_masks(diff.shape,cfa)
    inner=np.zeros_like(gm);inner[3:-3,3:-3]=True
    rb=(red|blue)&inner
    base_gate=(rb&(confidence>CONF_MIN)&(confidence<=CONF_MAX)&
               (disagreement>=DISAGREEMENT_MIN)&(minabs<=STRONG_COLOUR_LIMIT))
    return soft,confidence,disagreement,minabs,base_gate

def clip_support(sensor,cfa,spec,white=1023):
    if spec['clip']=='none':
        return np.ones(sensor.shape,bool)
    _,_,green=cfa_masks(sensor.shape,cfa)
    clipped=sensor>=white
    seed=clipped if spec['clip']=='any' else clipped&green
    return maximum_filter(seed.astype(np.uint8),
                          size=2*spec['radius']+1,mode='constant')>0

def project_toward_zero(current,soft):
    cur=current.astype(np.int64);s=soft.astype(np.int64)
    # For positive values use [0,current]; for negative use [current,0].
    target=np.where(cur>0,np.clip(s,0,np.maximum(cur,0)),
                    np.where(cur<0,np.clip(s,np.minimum(cur,0),0),0))
    return target.astype(np.int64)

def candidate(current,soft,base_gate,sensor,cfa,spec):
    gate=base_gate&clip_support(sensor,cfa,spec)
    cur=current.astype(np.int64)
    target=project_toward_zero(cur,soft)
    mixed=llround(cur+spec['alpha']*(target-cur))
    out=cur.copy();out[gate]=mixed[gate]
    # Hard invariants: no sign crossing and no magnitude growth at changed sites.
    changed=gate&(out!=cur)
    if np.any(changed):
        assert np.all(cur[changed]*out[changed]>=0)
        assert np.all(np.abs(out[changed])<=np.abs(cur[changed]))
    return out.astype(np.int32),gate,changed

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
                        if sigma:
                            scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],
                                         np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)

                        base=native.render(norm,n[0],n[2],cfa)
                        green,diff,current,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        soft,conf,dis,minabs,base_gate=fields(diff,green,cfa)
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)}
                        stats={}
                        for name,spec in SPECS.items():
                            ca,gate,changed=candidate(current,soft,base_gate,sensor,cfa,spec)
                            cam=probe.consume(ca,base,cfa,n[0],n[2])
                            assert np.array_equal(cam[...,1],base[...,1])
                            mm[name]=metrics(cam,truth,scale,n)
                            stats[name]=dict(
                                gate_fraction=float(gate.mean()),
                                changed_fraction=float(changed.mean()),
                                changed_carrier_samples=int(changed.sum()),
                                maximum_abs_correction=int(np.max(np.abs(ca.astype(np.int64)-current.astype(np.int64)))),
                                gate_confidence_mean=float(conf[gate].mean()) if np.any(gate) else 0.,
                                gate_disagreement_mean=float(dis[gate].mean()) if np.any(gate) else 0.,
                                gate_minabs_mean=float(minabs[gate].mean()) if np.any(gate) else 0.)
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,
                                         background=bgname,subject=subject,
                                         raw_clipped_fraction=float((sensor>=1023).mean()),
                                         metrics=mm,gates=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode in SPECS:
        summary[mode]={'spec':SPECS[mode]}
        for key in ('scene_rgb_rms','chroma_rms',
                    'false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows])
            c=np.array([r['metrics'][mode][key] for r in rows])
            delta=c-d
            summary[mode][key]=dict(
                cases_improved=int((delta<-1e-12).sum()),
                cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),
                mean_change=float(delta.mean()),
                max_increase=float(delta.max()),
                max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),
                best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green_subject=np.array([r['subject']=='green' for r in rows])
        magenta_subject=np.array([r['subject'].isin(['magenta','bright_magenta']) if False else False for r in rows])
        # Explicit subsets without relying on numpy string helper tricks.
        magenta_subject=np.array([r['subject'] in ('magenta','bright_magenta') for r in rows])
        for subset,sel in [
            ('clipped',clipped),
            ('clipped_neutral',clipped&neutral),
            ('clipped_green_subject',clipped&green_subject),
            ('clipped_magenta_subject',clipped&magenta_subject),
            ('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                d=np.array([r['metrics']['D'][key] for r in rows])[sel]
                c=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_mean_D']=float(d.mean()) if d.size else 0.
                vals[key+'_mean_candidate']=float(c.mean()) if c.size else 0.
                vals[key+'_cases_worse']=int((c>d+1e-12).sum())
                vals[key+'_cases_improved']=int((c<d-1e-12).sum())
            summary[mode][subset]=vals
        summary[mode]['gate']=dict(
            mean_gate_fraction=float(np.mean([r['gates'][mode]['gate_fraction'] for r in rows])),
            mean_changed_fraction=float(np.mean([r['gates'][mode]['changed_fraction'] for r in rows])),
            changed_carrier_total=int(sum(r['gates'][mode]['changed_carrier_samples'] for r in rows)),
            maximum_abs_correction=max(r['gates'][mode]['maximum_abs_correction'] for r in rows))

    strict=[m for m in SPECS
            if summary[m]['false_magenta_excess_fraction']['cases_worse']==0
            and summary[m]['false_green_excess_fraction']['cases_worse']==0]
    return dict(schema='m9.detail1u.sign_safe_directional.v1',
                case_count=len(rows),cfas=list(cfas),
                neutral=n.tolist(),representation_scale=scale,
                confidence_min=CONF_MIN,confidence_max=CONF_MAX,
                disagreement_min=DISAGREEMENT_MIN,
                strong_colour_limit=STRONG_COLOUR_LIMIT,
                specs=SPECS,strict_zero_false_chroma_regression=strict,
                backgrounds=BACKGROUNDS,subjects=SUBJECTS,
                summary=summary,cases=rows,
                scope='Directional target projected between current carrier and zero. Carrier magnitude can only decrease and sign cannot flip. Current D exact outside gate. Optional clip support uses original sensor censor state. Native green/Sharp and downstream rendering exact; no hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native')
    probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(
        json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(strict_zero_false_chroma_regression=result['strict_zero_false_chroma_regression'],
                          summary=result['summary']),indent=2))

if __name__=='__main__':
    main()
