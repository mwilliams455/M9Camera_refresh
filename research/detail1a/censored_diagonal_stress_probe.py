"""M9DETAIL1M research: stress the zero-regression censored-diagonal rule.

Extends DETAIL1L's two promising exactly-three-anchor / unsupported-positive
variants across several WB neutrals and a deterministic Camera2 noise model.
Final native green/ISO160 Sharp, exposure, colour and JPEG remain untouched.
No Android source or APK change.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter

from rb_domain import DomainProbe
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from censored_diagonal_mean_probe import censored_carriers

VARIANTS=('valid3_unsupported_pos','valid3_unsupported_pos_half')
NEUTRALS=(
    ('capture',[0.41796875,1.,0.6435546875]),
    ('warm',[0.28,1.,0.48]),
    ('cool',[0.62,1.,0.78]),
    ('unity',[1.,1.,1.]),
)
RGB_PROFILE=np.array([
    [0.00002661066294125,4.351414460641375e-7],
    [0.000031248508540855,3.669826853873275e-7],
    [0.00002625869602082,4.450756137593575e-7],
],dtype=float)

def one_grid(native,probe,cfas,named_neutral,noise,rng,scale=1.6105431518598052):
    neutral_name,neutral=named_neutral
    n=np.asarray(neutral,float)
    yy,xx=np.indices((160,192)); rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        channel=np.where(red,0,np.where(blue,2,1))
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43; mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma: scene=gaussian_filter(scene,[sigma,sigma,0])
                        physical=scene*n
                        samples=np.where(red,physical[...,0],np.where(blue,physical[...,2],physical[...,1]))
                        if noise:
                            variance=RGB_PROFILE[channel,0]*np.maximum(samples,0)+RGB_PROFILE[channel,1]
                            samples=samples+rng.normal(size=samples.shape)*np.sqrt(variance)
                        samples=np.clip(samples,0,1)
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa)
                        current=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        cams={'D':probe.consume(current,base,cfa,n[0],n[2])}
                        support={}
                        for name,carrier,active in censored_carriers(probe,norm,sensor,cfa,n[0],n[2],1023):
                            if name in VARIANTS:
                                cams[name]=probe.consume(carrier,base,cfa,n[0],n[2])
                                support[name]=float(active.mean())
                        clipped=np.clip(scene,0,1); truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,neutral=neutral_name,noise=noise,shape=shape,sigma=sigma,
                                 background=bgname,subject=subject,support_fraction=support,metrics={})
                        for name,cam in cams.items():
                            z=restored(cam,scale,n)[16:-16,16:-16]
                            chroma=z[...,[0,2]]-z[...,[1]]
                            pink=(chroma[...,0]>.02)&(chroma[...,1]>.02)
                            row['metrics'][name]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                pink_fraction=float(pink.mean()))
                        rows.append(row)
        print('neutral',neutral_name,'noise',noise,'CFA',cfa,'cases',len(rows),flush=True)
    return rows

def summarize(rows):
    out={}
    for mode in VARIANTS:
        out[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            coloured=np.array([r['subject']!='neutral' for r in rows])
            out[mode][metric]=dict(
                cases_worse_than_D=int((delta>1e-12).sum()),
                coloured_cases_worse_than_D=int(((delta>1e-12)&coloured).sum()),
                max_rms_increase=float(delta.max()),
                p99_rms_increase=float(np.quantile(np.maximum(delta,0),.99)),
                mean_rms_change=float(delta.mean()),
                max_rms_improvement=float((-delta).max()))
        neutral=[r for r in rows if r['subject']=='neutral']
        d=np.array([r['metrics']['D']['pink_fraction'] for r in neutral])
        c=np.array([r['metrics'][mode]['pink_fraction'] for r in neutral])
        out[mode]['neutral_false_pink']=dict(
            cases_improved=int((c<d-1e-15).sum()),cases_worse=int((c>d+1e-15).sum()),
            mean_D=float(d.mean()),mean_candidate=float(c.mean()),
            max_D=float(d.max()),max_candidate=float(c.max()))
        out[mode]['mean_support_fraction']=float(np.mean([r['support_fraction'][mode] for r in rows]))
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    all_rows=[];by_condition={};seed=92322
    for idx,named in enumerate(NEUTRALS):
        for noise in (False,True):
            rng=np.random.default_rng(seed+idx*10+int(noise))
            rows=one_grid(native,probe,a.cfas,named,noise,rng)
            key=named[0]+('_noise' if noise else '_clean')
            by_condition[key]=summarize(rows);all_rows.extend(rows)
    result=dict(schema='m9.detail1m.censored_diagonal_stress.v1',case_count=len(all_rows),cfas=a.cfas,
        neutrals={k:v for k,v in NEUTRALS},rgb_noise_profile=RGB_PROFILE.tolist(),noise_seed_base=seed,
        representation_scale=1.6105431518598052,variants=list(VARIANTS),
        summary=summarize(all_rows),by_condition=by_condition,
        scope='Deterministic synthetic stress. Exactly one censored diagonal anchor; positive current carrier changed only when three surviving anchors have non-positive mean. Native green/Sharp and downstream rendering fixed. No scene/hue classifier.')
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=all_rows
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))
    print('BY_CONDITION')
    print(json.dumps(result['by_condition'],indent=2))

if __name__=='__main__':main()
