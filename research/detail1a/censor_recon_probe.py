"""M9DETAIL1Q / CENSORRECON1A: reconstruct only censored colour-difference anchors.

DETAIL1D forms a camera-neutral colour difference at native R/B CFA sites:
    d = C/nC - Ginterp
A measured d becomes unreliable when the colour sample itself is sensor-white
censored, or when one of the cardinal green samples used by Ginterp is censored.

This probe leaves every reliable measured d exact.  Only unreliable d samples
are reconstructed from surrounding reliable same-colour differences on the
native CFA phase grid.  The bounded variants also preserve the one-sided facts
that clipping still tells us:
  * colour clipped, green support valid  -> true d >= measured d
  * green support clipped, colour valid  -> true d <= measured d
  * both clipped                         -> no ordering constraint

No hue/subject/foliage classifier is used. Final native green/ISO160 Sharp,
exposure, colour, SAT2/curve02 and JPEG remain unchanged. Research only.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,convolve

from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

MODES=('nearest_bounds','harmonic8_bounds','harmonic24_bounds','harmonic24_unbounded')
CROSS=np.array([[0.,.25,0.],[.25,0.,.25],[0.,.25,0.]],np.float64)

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

def invalid_masks(sensor,cfa,white=1023):
    red,blue,green=cfa_masks(sensor.shape,cfa)
    clipped=sensor>=white
    # At every native R/B site its four cardinal neighbours are green CFA sites.
    gc=(np.roll(clipped,1,0)|np.roll(clipped,-1,0)|
        np.roll(clipped,1,1)|np.roll(clipped,-1,1))
    rb=red|blue
    own=rb&clipped
    gsup=rb&gc
    invalid=rb&(own|gsup)
    # Roll wrap must never create support at the physical perimeter.
    for m in (own,gsup,invalid):
        m[:2]=False;m[-2:]=False;m[:,:2]=False;m[:,-2:]=False
    return own,gsup,invalid

def fill_phase(vals,invalid,iters,bounds,own,gsup):
    vals=np.asarray(vals,np.int64);invalid=np.asarray(invalid,bool)
    if not np.any(invalid):return vals.copy()
    known=~invalid
    if not np.any(known):return vals.copy()
    # Nearest reliable same-colour anchor is a deterministic initialization.
    _,idx=distance_transform_edt(invalid,return_indices=True)
    work=vals[tuple(idx)].astype(np.float64)
    work[known]=vals[known]
    if iters:
        for _ in range(iters):
            avg=convolve(work,CROSS,mode='nearest')
            work=np.where(invalid,avg,vals)
    out=llround(work)
    if bounds:
        colour_only=own&~gsup
        green_only=gsup&~own
        out=np.where(colour_only,np.maximum(out,vals),out)
        out=np.where(green_only,np.minimum(out,vals),out)
    out[known]=vals[known]
    return out.astype(np.int64)

def reconstructed_diff(diff,sensor,cfa,mode,white=1023):
    red,blue,_=cfa_masks(diff.shape,cfa)
    own,gsup,invalid=invalid_masks(sensor,cfa,white)
    out=diff.astype(np.int64).copy()
    if mode=='nearest_bounds':iters=0;bounds=True
    elif mode=='harmonic8_bounds':iters=8;bounds=True
    elif mode=='harmonic24_bounds':iters=24;bounds=True
    elif mode=='harmonic24_unbounded':iters=24;bounds=False
    else:raise ValueError(mode)
    for phase in ((int(cfa in (2,3)),int(cfa in (1,3))),
                  (1-int(cfa in (2,3)),1-int(cfa in (1,3)))):
        py,px=phase
        sl=np.s_[py::2,px::2]
        out[sl]=fill_phase(diff[sl],invalid[sl],iters,bounds,own[sl],gsup[sl])
    # Non-R/B samples and reliable measured anchors must remain exact.
    rb=red|blue
    assert np.array_equal(out[~rb],diff[~rb])
    assert np.array_equal(out[rb&~invalid],diff[rb&~invalid])
    return out.astype(np.int32),dict(own_clip=own,green_support_clip=gsup,invalid=invalid)

def carrier_from_diff(filled,current,cfa):
    red,blue,green=cfa_masks(filled.shape,cfa)
    d=filled.astype(np.int64)
    total=(np.roll(np.roll(d,1,0),1,1)+np.roll(np.roll(d,1,0),-1,1)+
           np.roll(np.roll(d,-1,0),1,1)+np.roll(np.roll(d,-1,0),-1,1))
    candidate=total//4
    out=current.astype(np.int64).copy()
    inner=np.zeros_like(green);inner[3:-3,3:-3]=True
    mask=(red|blue)&inner
    out[mask]=candidate[mask]
    return out.astype(np.int32)

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
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[];valid_exact={m:True for m in MODES}
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
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        for mode in MODES:
                            filled,masks=reconstructed_diff(diff,sensor,cfa,mode)
                            invalid=masks['invalid'];rb=red|blue
                            valid_exact[mode] &= np.array_equal(filled[rb&~invalid],diff[rb&~invalid])
                            carrier=carrier_from_diff(filled,current,cfa)
                            cam=probe.consume(carrier,base,cfa,n[0],n[2])
                            assert np.array_equal(cam[...,1],base[...,1])
                            mm[mode]=metrics(cam,truth,scale,n)
                            stats[mode]=dict(
                                invalid_anchor_fraction=float(invalid.mean()),
                                own_clip_anchor_fraction=float(masks['own_clip'].mean()),
                                green_support_clip_anchor_fraction=float(masks['green_support_clip'].mean()),
                                changed_diff_samples=int(np.count_nonzero(filled!=diff)),
                                changed_carrier_samples=int(np.count_nonzero(carrier!=current)))
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm,reconstruction=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in MODES:
        summary[mode]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            d=np.array([r['metrics']['D'][key] for r in rows]);c=np.array([r['metrics'][mode][key] for r in rows]);delta=c-d
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_D=float(d.mean()),mean_candidate=float(c.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                d=np.array([r['metrics']['D'][key] for r in rows])[sel];c=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_mean_D']=float(d.mean());vals[key+'_mean_candidate']=float(c.mean())
                vals[key+'_cases_worse']=int((c>d+1e-12).sum())
            summary[mode][subset]=vals
        summary[mode]['reconstruction']=dict(
            valid_measured_diff_exact=bool(valid_exact[mode]),
            mean_invalid_anchor_fraction=float(np.mean([r['reconstruction'][mode]['invalid_anchor_fraction'] for r in rows])),
            changed_diff_total=int(sum(r['reconstruction'][mode]['changed_diff_samples'] for r in rows)),
            changed_carrier_total=int(sum(r['reconstruction'][mode]['changed_carrier_samples'] for r in rows)))
    return dict(schema='m9.detail1q.censor_recon.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        summary=summary,cases=rows,
        scope='Only censored native R/B difference anchors are reconstructed. Reliable measured difference anchors exact. One-sided clipping bounds retained in bounded variants. Native green/Sharp and downstream rendering unchanged; no hue/subject classifier or APK mutation.')

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
