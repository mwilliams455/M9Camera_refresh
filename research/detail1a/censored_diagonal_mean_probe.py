"""M9DETAIL1L research: exclude censored Bayer anchors from the four-diagonal R/B carrier.

DETAIL1D/H currently averages all four diagonal opposite-colour differences even
when one or more source Bayer samples are at sensor white.  A clipped source no
longer carries its original colour magnitude.  This probe leaves the accepted
WB-normalized difference producer, native green/ISO160 Sharp, Noise2, exposure
and colour untouched and changes only that average: use the mean of unclipped
diagonal anchors when enough survive, otherwise retain D exactly.

Synthetic falsification only. No Android source/APK change.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.ndimage import gaussian_filter

from rb_domain import DomainProbe
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored

VARIANTS=('valid1','valid2','valid3','valid2_half','valid3_half','valid3_unsupported_pos','valid3_unsupported_pos_half','valid2_unsupported_pos_half')

def sh(a,dy,dx):
    return np.roll(np.roll(a,dy,axis=0),dx,axis=1)

def censored_carriers(probe,norm,sensor,cfa,nr,nb,white):
    green,diff,current,_=probe.stages(norm,cfa,nr,nb,shrink=True)
    ds=np.stack([sh(diff,dy,dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))],axis=0).astype(np.int64)
    ss=np.stack([sh(sensor,dy,dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))],axis=0)
    valid=ss<white
    count=valid.sum(axis=0)
    total=(ds*valid).sum(axis=0)
    # Python/NumPy // is floor division, matching the signed carrier's floor_div.
    mean=np.where(count>0,total//np.maximum(count,1),current.astype(np.int64))
    _,_,green_sites=cfa_masks(norm.shape,cfa)
    inner=np.zeros(norm.shape,bool); inner[3:-3,3:-3]=True
    rb=(~green_sites)&inner
    any_censored=valid.sum(axis=0)<4
    for minvalid in (1,2,3):
        active=rb&any_censored&(count>=minvalid)
        cand=np.where(active,mean,current).astype(np.int32)
        yield f'valid{minvalid}',cand,active
    for minvalid in (2,3):
        active=rb&any_censored&(count>=minvalid)
        half=((current.astype(np.int64)+mean)//2).astype(np.int32)
        cand=np.where(active,half,current).astype(np.int32)
        yield f'valid{minvalid}_half',cand,active

    # Positive-chroma support guard: only reduce a positive carrier when the
    # surviving unclipped anchors say the channel difference is non-positive.
    # This is channel evidence, not a magenta/hue classifier.
    exactly3=rb&any_censored&(count==3)
    unsupported3=exactly3&(current>0)&(mean<=0)&(mean<current)
    half3=((current.astype(np.int64)+mean)//2).astype(np.int32)
    yield 'valid3_unsupported_pos',np.where(unsupported3,mean,current).astype(np.int32),unsupported3
    yield 'valid3_unsupported_pos_half',np.where(unsupported3,half3,current).astype(np.int32),unsupported3

    at_least2=rb&any_censored&(count>=2)
    unsupported2=at_least2&(current>0)&(mean<=0)&(mean<current)
    half2=((current.astype(np.int64)+mean)//2).astype(np.int32)
    yield 'valid2_unsupported_pos_half',np.where(unsupported2,half2,current).astype(np.int32),unsupported2

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192)); n=np.array([.41796875,1.,.6435546875]); scale=1.6105431518598052
    rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43; mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma: scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa)
                        current=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        clipped=np.clip(scene,0,1); truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        cams={'D':dcam}; sf={}
                        for name,carrier,active in censored_carriers(probe,norm,sensor,cfa,n[0],n[2],1023):
                            cams[name]=probe.consume(carrier,base,cfa,n[0],n[2]); sf[name]=float(active.mean())
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                 support_fraction=sf,metrics={})
                        for name,cam in cams.items():
                            z=restored(cam,scale,n)[16:-16,16:-16]
                            chroma=z[...,[0,2]]-z[...,[1]]
                            pink=(chroma[...,0]>.02)&(chroma[...,1]>.02)
                            row['metrics'][name]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                pink_fraction=float(pink.mean()))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in VARIANTS:
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            coloured=np.array([r['subject']!='neutral' for r in rows])
            summary[mode][metric]=dict(
                cases_worse_than_D=int((delta>1e-12).sum()),
                coloured_cases_worse_than_D=int(((delta>1e-12)&coloured).sum()),
                max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()),
                worst_case_index=int(delta.argmax()))
        neutral=[r for r in rows if r['subject']=='neutral']
        d=np.array([r['metrics']['D']['pink_fraction'] for r in neutral])
        c=np.array([r['metrics'][mode]['pink_fraction'] for r in neutral])
        summary[mode]['neutral_false_pink']=dict(
            cases_improved=int((c<d-1e-15).sum()),cases_worse=int((c>d+1e-15).sum()),
            mean_D=float(d.mean()),mean_candidate=float(c.mean()),
            max_D=float(d.max()),max_candidate=float(c.max()))
        summary[mode]['mean_support_fraction']=float(np.mean([r['support_fraction'][mode] for r in rows]))
    return dict(schema='m9.detail1l.censored_diagonal_mean.v1',case_count=len(rows),cfas=cfas,
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        variants=list(VARIANTS),summary=summary,cases=rows,
        scope='Existing D producer, final native green/Sharp and consumer fixed. Only clipped diagonal source samples are excluded from the carrier average when min-valid count survives. No hue/scene logic, exposure, colour or JPEG mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native'); probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__': main()
