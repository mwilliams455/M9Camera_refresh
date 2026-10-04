"""Pointwise colour-difference bound at measured, censored green CFA sites.

With downstream camera white fixed at one, a lower bound L on true normalized
green implies C-G <= max(0, 1-L) for either white-clipped R or B. Apply only at
the actual measured green sites. Do not infer this bound at R/B CFA locations.
The six-sigma noise allowance is a model margin, not a calibration guarantee.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter
from native import Native
from rb_domain import DomainProbe
from fringe_replay import cfa_masks
from censored_chroma_probe import BACKGROUNDS,SUBJECTS


def project(norm,sensor,cam,cfa,neutral,scale,black,white,green_profile=(0.,0.),sigmas=6.):
    n=np.asarray(neutral,dtype=float);black=np.asarray(black,dtype=float)
    assert n.shape==(3,) and n[1]==1 and np.all(n>0) and black.shape==(4,)
    assert scale>0 and np.isfinite(scale) and np.all(white>black)
    s,o=map(float,green_profile)
    assert s>=0 and o>=0 and np.isfinite(s+o) and sigmas>=0
    _,_,green=cfa_masks(norm.shape,cfa)
    yy,xx=np.ogrid[:norm.shape[0],:norm.shape[1]]
    selected=green & (sensor>=white)
    selected[:10]=False;selected[-10:]=False;selected[:,:10]=False;selected[:,-10:]=False
    # At sensor white, pre-shading normalized green is one. The post-shading
    # norm therefore measures the effective shading gain / representation scale.
    # Subtract one whole uint16 code for conservative normalization rounding.
    gain_lower=np.maximum(norm.astype(float)-1.,0.)*scale/65535
    adc_half_bin=.5/(white-black[(yy%2)*2+xx%2])
    uncertainty=adc_half_bin+sigmas*np.sqrt(s+o)
    green_lower=gain_lower*np.maximum(1.-uncertainty,0.)
    upper=np.maximum(1.-green_lower,0.)
    out=cam.copy()
    ceiling=cam[...,1].astype(float)+upper*65535/scale
    for channel in (0,2):
        cap=np.clip(np.floor(n[channel]*ceiling+.5),0,65535).astype(np.uint16)
        out[...,channel]=np.where(selected,np.minimum(cam[...,channel],cap),cam[...,channel])
    assert np.array_equal(out[...,1],cam[...,1]) and np.array_equal(out[~selected],cam[~selected])
    return out,dict(selected_green_sites=int(selected.sum()),changed_pixels=int(np.any(out!=cam,axis=-1).sum()),
        changed_rb_samples=int(np.count_nonzero(out!=cam)),maximum_correction=int((cam.astype(np.int32)-out).max()),
        green_exact=True,unselected_pixels_exact=True,noise_sigmas=sigmas,green_profile=[s,o]),upper,selected


def synthetic(native,probe,cfas,noise=False):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052;rows=[]
    rng=np.random.default_rng(92311)
    profile=np.array([[2.661066294125e-05,4.351414460641375e-07],
        [3.1248508540855e-05,3.669826853873275e-07],[2.625869602082e-05,4.450756137593575e-07]]) if noise else np.zeros((3,2))
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa);channel=np.where(red,0,np.where(blue,2,1))
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        physical=np.where(red,scene[...,0]*n[0],np.where(blue,scene[...,2]*n[2],scene[...,1]))
                        observed=physical.copy()
                        if noise:
                            variance=profile[channel,0]*physical+profile[channel,1]
                            observed+=rng.normal(size=observed.shape)*np.sqrt(variance)
                        samples=np.clip(observed,0,1)
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa,candidate=False)
                        dcam=probe.consume(probe.stages(norm,cfa,n[0],n[2])[2],base,cfa,n[0],n[2])
                        candidate,stats,upper,selected=project(norm,sensor,dcam,cfa,n,scale,[64]*4,1023,profile[1])
                        clipped=np.clip(scene,0,1);truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,metrics={},projection=stats)
                        errors=[]
                        for mode,cam in [('D',dcam),('bounded',candidate)]:
                            z=np.clip(cam.astype(float)/65535*scale/n,0,1)[16:-16,16:-16]
                            errors.append((z[...,[0,2]]-fixed[...,[0,2]])**2)
                            row['metrics'][mode]=dict(scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean(errors[-1]))))
                        increase=errors[1]-errors[0]
                        row['fixed_reference_samples_worse']=int((increase>1e-15).sum())
                        row['maximum_fixed_reference_squared_error_increase']=float(increase.max())
                        true_diff=clipped[...,[0,2]]-clipped[...,[1]]
                        row['true_difference_bound_violations']=int(np.count_nonzero(selected[...,None] & (true_diff>upper[...,None]+1e-12)))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
        delta=np.array([r['metrics']['bounded'][metric]-r['metrics']['D'][metric] for r in rows])
        summary[metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),max_rms_increase=float(delta.max()),
            mean_rms_change=float(delta.mean()),worst_case_index=int(delta.argmax()))
    summary['fixed_reference_samples_worse']=sum(r['fixed_reference_samples_worse'] for r in rows)
    summary['true_difference_bound_violations']=sum(r['true_difference_bound_violations'] for r in rows)
    summary['changed_rb_samples']=sum(r['projection']['changed_rb_samples'] for r in rows)
    return dict(schema='m9.censored_green_bound.v1',case_count=len(rows),cases=rows,summary=summary,
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        sensor_noise=noise,noise_profile=profile.tolist(),noise_seed=92311 if noise else None,
        scope='Measured green clipping sites only. Same declared references; no new white cap, guide interpolation or colour-fit assumption. Full scene RGB reference retained despite its different luma target. No photographic acceptance implied.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    ap.add_argument('--noise',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas,a.noise)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['spatial_source_hashes']=native.source_hashes
    cases=result.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
