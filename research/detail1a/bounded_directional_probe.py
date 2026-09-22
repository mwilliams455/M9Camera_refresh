"""M9DETAIL1L: confidence-bounded directional colour-difference carrier.

The current D carrier averages all four diagonal colour-difference anchors.
DETAIL1L tests a minimal alternative: form the two diagonal pair estimates,
soft-weight them with the native pre-consumer green guide, but only use that
directional estimate when (a) diagonal disagreement is large and (b) green
anisotropy is moderate rather than extreme. Extreme anisotropy abstains because
the preceding self-contained screen localized false-magenta regressions there.

No hue, subject, foliage, wildlife, or rendered-pink classifier is used. Final
native green/ISO160 Sharp, exposure, colour, SAT2/curve02 and JPEG are unchanged.
Synthetic falsification only; no Android production source or APK change.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter
from rb_domain import DomainProbe
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored

MODES=('bounded100','protected512','protected900','protected1280')
CONF_MIN=.02
CONF_MAX=.28
DIFF_MIN=2048

def llround(v):
    v=np.asarray(v)
    return np.where(v>=0,np.floor(v+.5),np.ceil(v-.5)).astype(np.int64)

def directional_fields(diff,green,cfa):
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
    _,_,gm=cfa_masks(diff.shape,cfa)
    inner=np.zeros_like(gm);inner[3:-3,3:-3]=True
    gate=(~gm)&inner&(confidence>CONF_MIN)&(confidence<=CONF_MAX)&(disagreement>=DIFF_MIN)
    minabs=np.minimum(np.abs(p1),np.abs(p2))
    return soft,gate,confidence,disagreement,minabs

def candidate_carrier(current,soft,gate,alpha):
    out=current.astype(np.int64).copy()
    mixed=llround(out+alpha*(soft-out))
    out[gate]=mixed[gate]
    return out.astype(np.int32)

def metric(cam,truth,fixed,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16]
    t=truth[16:-16,16:-16];f=fixed[16:-16,16:-16]
    td=np.stack([t[...,0]-t[...,1],t[...,2]-t[...,1]],axis=-1)
    rd=np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)
    false=(np.minimum(rd[...,0],rd[...,1])-np.minimum(td[...,0],td[...,1])>.02)
    return dict(scene_rgb_rms=float(np.sqrt(np.mean((z-t)**2))),
                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-f[...,[0,2]])**2))),
                false_magenta_excess_fraction=float(false.mean()))

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
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
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa)
                        green,diff,current,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        soft,gate,confidence,disagreement,minabs=directional_fields(diff,green,cfa)
                        truth=np.clip(scene,0,1)
                        sg=base[...,1].astype(np.float64)/65535*scale
                        fixed=np.clip(truth-truth[...,[1]]+sg[...,None],0,1)
                        mm={'D':metric(dcam,truth,fixed,scale,n)}
                        changed={}
                        specs=[('bounded100',gate,1.),
                               ('protected512',gate&(minabs<=512),1.),
                               ('protected900',gate&(minabs<=900),1.),
                               ('protected1280',gate&(minabs<=1280),1.)]
                        for name,active,alpha in specs:
                            carrier=candidate_carrier(current,soft,active,alpha)
                            cam=probe.consume(carrier,base,cfa,n[0],n[2])
                            assert np.array_equal(cam[...,1],base[...,1])
                            mm[name]=metric(cam,truth,fixed,scale,n)
                            changed[name]=int(np.count_nonzero(carrier!=current))
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            hard_clip_fraction=float((sensor>=1023).mean()),gate_fraction=float(gate.mean()),
                            gate_confidence_mean=float(confidence[gate].mean()) if np.any(gate) else 0.,
                            gate_disagreement_mean=float(disagreement[gate].mean()) if np.any(gate) else 0.,
                            changed_carrier=changed,metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in MODES:
        summary[mode]={}
        for key in ('scene_rgb_rms','fixed_green_rb_rms','false_magenta_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows]);c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        summary[mode]['changed_carrier_total']=int(sum(r['changed_carrier'][mode] for r in rows))
        summary[mode]['mean_gate_fraction']=float(np.mean([r['gate_fraction'] for r in rows]))
    return dict(schema='m9.detail1l.bounded_directional.v2',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        confidence_min=CONF_MIN,confidence_max=CONF_MAX,disagreement_min=DIFF_MIN,strong_chroma_limits=[512,900,1280],
        summary=summary,cases=rows,
        scope='Current D exact outside gate. Gate uses only green anisotropy and diagonal colour-difference disagreement. Native green/Sharp exact. No hue/subject classifier and no Android/Leica parity claim.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__':main()
