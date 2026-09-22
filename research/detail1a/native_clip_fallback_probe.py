"""M9DETAIL1K research: clipped-edge fallback from corrected R/B to native MHC R/B.

Phone evidence shows DETAIL1H raises the failing woodland pink diagnostic versus
its native pre-detail baseline, while the accepted Noise2 guard is already
disabled around clipping.  This probe therefore keeps corrected DETAIL1D/H R/B
across the frame and substitutes only native MHC R/B inside deterministic
sensor-white neighbourhoods.  Native green/ISO160 Sharp is identical in both.

Synthetic falsification only. No Android source/APK change.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

from rb_domain import DomainProbe
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored

VARIANTS=('native_global','native_clip1','native_clip2','native_clip4',
          'native_clip1_half','native_clip2_half','native_clip4_half')

def combine(dcam,base,mask,alpha=1.0):
    out=dcam.copy()
    if alpha>=1:
        out[...,0]=np.where(mask,base[...,0],dcam[...,0])
        out[...,2]=np.where(mask,base[...,2],dcam[...,2])
    else:
        for ch in (0,2):
            mixed=np.floor(dcam[...,ch].astype(float)+alpha*(base[...,ch].astype(float)-dcam[...,ch].astype(float))+.5)
            out[...,ch]=np.where(mask,np.clip(mixed,0,65535).astype(np.uint16),dcam[...,ch])
    out[...,1]=dcam[...,1]
    return out

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
                        clipped=sensor>=1023
                        supports={
                            'native_global':np.ones(norm.shape,bool),
                            'native_clip1':maximum_filter(clipped,size=3,mode='constant'),
                            'native_clip2':maximum_filter(clipped,size=5,mode='constant'),
                            'native_clip4':maximum_filter(clipped,size=9,mode='constant'),
                        }
                        cams={'D':dcam}
                        sf={}
                        for name in ('native_global','native_clip1','native_clip2','native_clip4'):
                            cams[name]=combine(dcam,base,supports[name],1.0); sf[name]=float(supports[name].mean())
                            half=name+'_half'
                            if name!='native_global':
                                cams[half]=combine(dcam,base,supports[name],0.5); sf[half]=float(supports[name].mean())
                        clipped_scene=np.clip(scene,0,1); truth=clipped_scene[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped_scene-clipped_scene[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                 support_fraction=sf,metrics={})
                        for name,cam in cams.items():
                            z=restored(cam,scale,n)[16:-16,16:-16]
                            chroma=z[...,[0,2]]-z[...,[1]]
                            pink=(chroma[...,0]>.02)&(chroma[...,1]>.02)
                            true_chroma=truth[...,[0,2]]-truth[...,[1]]
                            false_magenta=(np.minimum(chroma[...,0],chroma[...,1])-
                                           np.minimum(true_chroma[...,0],true_chroma[...,1])>.02)
                            row['metrics'][name]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                pink_fraction=float(pink.mean()),
                                false_magenta_excess_fraction=float(false_magenta.mean()))
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
        fd=np.array([r['metrics']['D']['false_magenta_excess_fraction'] for r in rows])
        fc=np.array([r['metrics'][mode]['false_magenta_excess_fraction'] for r in rows])
        delta=fc-fd
        summary[mode]['false_magenta_excess']=dict(
            cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
            mean_D=float(fd.mean()),mean_candidate=float(fc.mean()),
            max_increase=float(delta.max()),max_reduction=float((-delta).max()),
            worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        summary[mode]['mean_support_fraction']=float(np.mean([r['support_fraction'].get(mode,1.) for r in rows]))
    return dict(schema='m9.detail1j.native_clip_fallback.v2',case_count=len(rows),cfas=cfas,
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        variants=list(VARIANTS),summary=summary,cases=rows,
        scope='Corrected D R/B remains baseline; native MHC R/B substituted only by raw-white proximity. Green/Sharp exact. Half variants blend R/B 50%. No exposure/colour/JPEG mutation or Leica-firmware claim.')

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
