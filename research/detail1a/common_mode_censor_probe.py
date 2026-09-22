"""M9DETAIL1O: remove only unsupported common R/B excess near censoring.

This probe builds on the previously colour-safe certificate8 evidence.  It uses
the same sensor-censor geometry, same local uncensored measured R/B difference
bounds, and the same genuine-colour abstention rule.  The change is the
correction itself:

    eR = interpolated_RminusG - local_supported_RminusG_high
    eB = interpolated_BminusG - local_supported_BminusG_high

Only where both eR and eB are positive under the certificate do we act. Rather
than clamping R and B independently, subtract the SAME common amount

    common = min(eR,eB)

from both colour differences. This preserves R-B opponent colour exactly in
difference space and removes only unsupported common positive excess, the
signature that becomes false magenta when clipped luminance headroom is treated
as chroma.

No hue/magenta/foliage/subject classifier is used. Native green and fixed ISO160
Sharp remain byte-exact. Synthetic research only; no Android production/APK.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter,minimum_filter

from rb_domain import DomainProbe
from rb_probe import q14,q16
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored

MODES=('certificate8','common50','common75','common100')

def certificate_constraints(probe,norm,sensor,cfa,nr,nb,black,white):
    red,blue,green=cfa_masks(norm.shape,cfa)
    g,difference,_,_=probe.stages(norm,cfa,nr,nb,shrink=False)
    carrier=probe.stages(norm,cfa,nr,nb,shrink=True)[2]
    yy,xx=np.ogrid[:norm.shape[0],:norm.shape[1]]
    clipped=sensor>=white
    low=sensor<=np.asarray(black)[(yy%2)*2+xx%2]
    bad_green=green&(clipped|low)
    invalid=sum(np.roll(bad_green,shift,axis) for axis in (0,1) for shift in (-1,1))>0
    bounds=[];colour_evidence=[]
    radius=2
    for mask in (red,blue):
        possible=mask&~invalid&~low
        valid=possible&~clipped
        high=maximum_filter(np.where(valid,difference,0),size=2*radius+1)
        low_bound=minimum_filter(np.where(valid,difference,0),size=2*radius+1)
        available=maximum_filter(valid,size=2*radius+1)
        bounds.append((low_bound,high,available))
        colour_evidence.append(maximum_filter(np.where(possible,difference,0),size=3))
    support=maximum_filter(clipped&green,size=9)
    paired_positive=(colour_evidence[0]>0)&(colour_evidence[1]>0)
    support&=~maximum_filter(paired_positive,size=17)
    return carrier,bounds,support

def floor_half(a,b):
    # NumPy integer // is floor division, matching rb_domain.cpp floor_div.
    return (a.astype(np.int64)+b.astype(np.int64))//2

def interpolated_fields(carrier,cfa):
    h,w=carrier.shape
    yy,xx=np.ogrid[:h,:w]
    rx,ry=cfa in (1,3),cfa in (2,3)
    fields=[]
    # Same phase mapping as censored_chroma_probe.consume and rb_domain_consume.
    for ax,ay in ((1-rx,1-ry),(rx,ry)):
        horizontal=np.where(xx%2==ax,carrier,
            floor_half(np.roll(carrier,1,1),np.roll(carrier,-1,1)))
        full=np.where(yy%2==ay,horizontal,
            floor_half(np.roll(horizontal,1,0),np.roll(horizontal,-1,0)))
        fields.append(full.astype(np.int64))
    return fields

def llround(x):
    x=np.asarray(x,dtype=np.float64)
    return np.where(x>=0,np.floor(x+.5),np.ceil(x-.5)).astype(np.int64)

def reconstruct(base,diffs,nr,nb):
    out=base.copy()
    sg=q14(base[...,1]).astype(np.int64)
    for ch,nc,d in ((0,nr,diffs[0]),(2,nb,diffs[1])):
        out[...,ch]=q16(llround(nc*(sg+d)))
    out[...,1]=base[...,1]
    # Exact current consumer leaves outer ten pixels at base.
    out[:10]=base[:10];out[-10:]=base[-10:];out[:,:10]=base[:,:10];out[:,-10:]=base[:,-10:]
    return out

def candidate_variants(probe,norm,sensor,base,cfa,nr,nb,black,white):
    carrier,bounds,support=certificate_constraints(probe,norm,sensor,cfa,nr,nb,black,white)
    d=interpolated_fields(carrier,cfa)
    lo0,hi0,av0=bounds[0]; lo1,hi1,av1=bounds[1]
    joint=(support&av0&av1&(d[0]>hi0)&(d[1]>hi1))
    excess0=np.maximum(d[0]-hi0,0)
    excess1=np.maximum(d[1]-hi1,0)
    common=np.minimum(excess0,excess1)
    common=np.where(joint,common,0).astype(np.int64)

    # Pixel-exact baseline check against the compiled consumer.
    compiled=probe.consume(carrier,base,cfa,nr,nb)
    direct=reconstruct(base,d,nr,nb)
    assert np.array_equal(compiled,direct),'Python full-field consumer mismatch'

    result={}
    # Historical certificate8 clamps each positive excess independently.
    cert=[np.where(joint,hi0,d[0]).astype(np.int64),
          np.where(joint,hi1,d[1]).astype(np.int64)]
    result['certificate8']=(reconstruct(base,cert,nr,nb),dict(
        corrected_pixels=int(joint.sum()),common_removed_sum=0,
        opponent_difference_exact=False))
    for name,alpha in [('common50',.5),('common75',.75),('common100',1.)]:
        corr=llround(common*alpha)
        dd=[d[0]-corr,d[1]-corr]
        cam=reconstruct(base,dd,nr,nb)
        # In difference coordinates R-B is unchanged before camera scaling/clamp.
        before=d[0]-d[1]; after=dd[0]-dd[1]
        assert np.array_equal(before,after)
        result[name]=(cam,dict(corrected_pixels=int((corr!=0).sum()),
            common_removed_sum=int(corr.sum()),opponent_difference_exact=True,
            max_common_removed=int(corr.max())))
    return compiled,result,joint,common

def metrics(cam,truth,fixed,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16]
    t=truth[16:-16,16:-16];f=fixed[16:-16,16:-16]
    rd=np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)
    td=np.stack([t[...,0]-t[...,1],t[...,2]-t[...,1]],axis=-1)
    false_mag=(np.minimum(rd[...,0],rd[...,1])-np.minimum(td[...,0],td[...,1])>.02)
    green_excess=np.minimum(z[...,1]-z[...,0],z[...,1]-z[...,2])
    true_green=np.minimum(t[...,1]-t[...,0],t[...,1]-t[...,2])
    false_green=(green_excess-true_green>.02)
    return dict(scene_rgb_rms=float(np.sqrt(np.mean((z-t)**2))),
        fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-f[...,[0,2]])**2))),
        false_magenta_excess_fraction=float(false_mag.mean()),
        false_green_excess_fraction=float(false_green.mean()))

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
                        dcam,cands,joint,common=candidate_variants(
                            probe,norm,sensor,base,cfa,n[0],n[2],[64]*4,1023)
                        truth=np.clip(scene,0,1)
                        sg=base[...,1].astype(np.float64)/65535*scale
                        fixed=np.clip(truth-truth[...,[1]]+sg[...,None],0,1)
                        mm={'D':metrics(dcam,truth,fixed,scale,n)}
                        stats={}
                        for name,(cam,st) in cands.items():
                            mm[name]=metrics(cam,truth,fixed,scale,n);stats[name]=st
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            hard_clip_fraction=float((sensor>=1023).mean()),
                            certificate_joint_fraction=float(joint.mean()),
                            common_excess_mean=float(common[joint].mean()) if np.any(joint) else 0.,
                            common_excess_max=int(common.max()),candidate_stats=stats,metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode in MODES:
        summary[mode]={}
        for key in ('scene_rgb_rms','fixed_green_rb_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows]);c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        for subj in SUBJECTS:
            mask=np.array([r['subject']==subj for r in rows])
            d=np.array([r['metrics']['D']['false_magenta_excess_fraction'] for r in rows])[mask]
            c=np.array([r['metrics'][mode]['false_magenta_excess_fraction'] for r in rows])[mask]
            summary[mode]['false_magenta_'+subj]=dict(cases_improved=int((c<d-1e-12).sum()),
                cases_worse=int((c>d+1e-12).sum()),mean_D=float(d.mean()),mean_candidate=float(c.mean()))
        summary[mode]['mean_corrected_pixels']=float(np.mean([r['candidate_stats'][mode]['corrected_pixels'] for r in rows]))
    return dict(schema='m9.detail1o.common_mode_censor.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        summary=summary,cases=rows,
        scope='Same certificate8 censor geometry/bounds/abstention. Common variants subtract identical unsupported positive excess from R-G and B-G, preserving opponent R-B exactly before scaling/clipping. Native green/Sharp exact. No hue/subject mask or Android/APK mutation.')

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
