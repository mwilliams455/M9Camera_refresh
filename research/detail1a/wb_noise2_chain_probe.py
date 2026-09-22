"""M9DETAIL1P: combine stored-domain WB with recovered Noise2 mode1.

This tests the recovered Leica stage order more faithfully:
WB/clamp -> green/Sharp -> R/B carrier -> Noise2 -> R/B interpolation.

Four paths are compared:
D current
D + recovered Noise2 mode1
stored-domain WB -> D
stored-domain WB -> D -> recovered Noise2 mode1

No hue/subject classifier and no Android/APK mutation.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter

from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe
from rb_probe import q16
from noise2 import Noise2,parameters

MODES=('D','D_noise2','stored','stored_noise2')

def phone_gains(neutral):
    n=np.asarray(neutral,dtype=float)
    preliminary=np.floor(16384/n).astype(np.int64)
    factor=16384 if preliminary.min()>=16384 else 268435456//preliminary.min()
    gains=np.maximum(preliminary*factor//16384,16384)
    gains[np.isin(gains,[16383,16385])]=16384
    assert np.all(gains<=65535) and np.any(gains==16384)
    return gains

def stored_chain(native,probe,noise,norm,cfa,neutral,use_noise):
    gains=phone_gains(neutral)
    red,blue,_=cfa_masks(norm.shape,cfa)
    gm=np.where(red,gains[0],np.where(blue,gains[2],gains[1]))
    raw14=np.clip(np.floor(norm.astype(float)*16383/65535+.5),0,16383).astype(np.int64)
    wb=q16(np.minimum(raw14*gm//16384,16383))
    base=native.render(wb,1.,1.,cfa)
    green,_,carrier,_=probe.stages(wb,cfa,1.,1.,shrink=True)
    if use_noise:
        carrier=noise.apply(carrier,green,cfa,parameters(0,neutral[0],neutral[2]))[0]
    rgb=probe.consume(carrier,base,cfa,1.,1.)
    return np.clip(np.floor(rgb.astype(float)/(gains/16384)+.5),0,65535).astype(np.uint16)

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

def synthetic(native,probe,noise,cfas):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
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
                        green,_,carrier,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(carrier,base,cfa,n[0],n[2])
                        n2=noise.apply(carrier,green,cfa,parameters(0,n[0],n[2]))[0]
                        dnoise=probe.consume(n2,base,cfa,n[0],n[2])

                        stored=stored_chain(native,probe,noise,norm,cfa,n,False)
                        stored_n=stored_chain(native,probe,noise,norm,cfa,n,True)
                        truth=np.clip(scene,0,1)
                        mm={k:metrics(v,truth,scale,n) for k,v in {
                            'D':dcam,'D_noise2':dnoise,'stored':stored,'stored_noise2':stored_n}.items()}
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                         raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in ('D_noise2','stored','stored_noise2'):
        summary[mode]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows]);c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        for subset,mask in [('clipped',clipped),('clipped_neutral',clipped&neutral),('unclipped',~clipped)]:
            vals={'case_count':int(mask.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                d=np.array([r['metrics']['D'][key] for r in rows])[mask];c=np.array([r['metrics'][mode][key] for r in rows])[mask]
                vals[key+'_mean_D']=float(d.mean());vals[key+'_mean_candidate']=float(c.mean())
                vals[key+'_cases_worse']=int((c>d+1e-12).sum())
            summary[mode][subset]=vals
    return dict(schema='m9.detail1p.wb_noise2_chain.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,phone_gains_q14=phone_gains(n).tolist(),
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Recovered stage ordering probe. Stored-domain WB uses phone neutral adaptation; Noise2 mode1 uses recovered slot0 threshold with original WB coefficients. No hue/subject classifier, no Android/APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native')
    probe=DomainProbe(a.out/'native');noise=Noise2(a.out/'native')
    result=synthetic(native,probe,noise,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__':main()
