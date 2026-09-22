"""M9DETAIL1R / RATIOCENSOR1A: reconstruct censored anchors in chromaticity space.

Absolute R-G/B-G differences scale with scene luminance. DETAIL1Q showed that
propagating those differences across a clipped highlight can trade magenta for
large false-green errors. This probe instead propagates a same-colour
chromaticity ratio from reliable native CFA anchors.

For a native R/B anchor:
  C = WB-normalized measured colour sample
  G = cardinal-green interpolation
  rho = C/G on anchors where both C and green support are uncensored

When green support is censored but C is valid:
  G_est = C/rho, d_est = C-G_est, constrained d_est <= measured d.

When C is censored but green support is valid:
  C_est = rho*G, d_est = C_est-G, constrained d_est >= measured d.

When both sides are censored, abstain and retain current DETAIL1D. Reliable
measured anchors remain exact. Reconstructed unshrunk d is passed through the
same recovered Co=2 shrink before the normal diagonal carrier/consumer.

No hue, subject, foliage or wildlife classifier. Native green/ISO160 Sharp and
all downstream rendering remain unchanged. Research only; no APK mutation.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,convolve

from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe
from rb_probe import q14

MODES=('green_nearest','green_h8','green_h24','single_h8','single_h24')
CROSS=np.array([[0.,.25,0.],[.25,0.,.25],[0.,.25,0.]],np.float64)
RATIO_MIN=1/64
RATIO_MAX=64.

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

def censor_masks(sensor,cfa,white=1023):
    red,blue,green=cfa_masks(sensor.shape,cfa)
    clipped=sensor>=white
    gc=(np.roll(clipped,1,0)|np.roll(clipped,-1,0)|
        np.roll(clipped,1,1)|np.roll(clipped,-1,1))
    rb=red|blue
    own=rb&clipped
    gsup=rb&gc
    for m in (own,gsup):
        m[:2]=False;m[-2:]=False;m[:,:2]=False;m[:,-2:]=False
    reliable=rb&~own&~gsup
    green_only=rb&gsup&~own
    colour_only=rb&own&~gsup
    both=rb&own&gsup
    return dict(own=own,gsup=gsup,reliable=reliable,green_only=green_only,
                colour_only=colour_only,both=both)

def fill_log_ratio(logrho,known,iters):
    known=np.asarray(known,bool)
    if not np.any(known):return np.array(logrho,copy=True),False
    missing=~known
    _,idx=distance_transform_edt(missing,return_indices=True)
    work=np.asarray(logrho,np.float64)[tuple(idx)]
    work[known]=logrho[known]
    for _ in range(iters):
        avg=convolve(work,CROSS,mode='nearest')
        work=np.where(missing,avg,logrho)
    return work,True

def shrink_co(d,a):
    d=np.asarray(d,np.int64);a=np.asarray(a,np.int64)
    v=np.maximum(np.abs(d)-(a>>2),0)
    return np.where(np.abs(d)<a,np.where(d<0,-v,v),d)

def reconstruct(norm,sensor,cfa,nr,nb,probe,mode,white=1023):
    green,d0,_,uncertainty=probe.stages(norm,cfa,nr,nb,shrink=False)
    _,dcurrent,current,_=probe.stages(norm,cfa,nr,nb,shrink=True)
    z=q14(np.asarray(norm,np.uint16)).astype(np.int64)
    red,blue,_=cfa_masks(norm.shape,cfa)
    masks=censor_masks(sensor,cfa,white)
    out=dcurrent.astype(np.int64).copy()

    if mode.endswith('nearest'):iters=0
    elif mode.endswith('h8'):iters=8
    elif mode.endswith('h24'):iters=24
    else:raise ValueError(mode)
    use_colour_only=mode.startswith('single_')

    changed=np.zeros(norm.shape,bool)
    ratio_available=np.zeros(norm.shape,bool)
    for channel_mask,nc,phase in [
        (red,nr,(int(cfa in (2,3)),int(cfa in (1,3)))),
        (blue,nb,(1-int(cfa in (2,3)),1-int(cfa in (1,3))))]:
        py,px=phase;sl=np.s_[py::2,px::2]
        g=green[sl].astype(np.int64)
        c=llround(z[sl].astype(np.float64)/nc)
        reliable=masks['reliable'][sl]&(g>0)&(c>0)
        ratio=np.clip(c.astype(np.float64)/np.maximum(g,1),RATIO_MIN,RATIO_MAX)
        logrho=np.log(ratio)
        filled,ok=fill_log_ratio(logrho,reliable,iters)
        if not ok:continue
        rho=np.exp(np.clip(filled,np.log(RATIO_MIN),np.log(RATIO_MAX)))
        target_g=masks['green_only'][sl]
        target_c=masks['colour_only'][sl] if use_colour_only else np.zeros_like(target_g)
        ratio_available[sl]|=target_g|target_c

        # Green censored, colour valid: derive the missing luminance from C/rho.
        gest=llround(c/np.maximum(rho,1e-12))
        dg=c-gest
        dg=np.minimum(dg,d0[sl].astype(np.int64))  # true d <= observed lower-G d
        dg=shrink_co(dg,uncertainty[sl])
        phase_out=out[sl]
        phase_out=np.where(target_g,dg,phase_out)

        # Colour censored, green valid: derive missing colour from rho*G.
        cest=llround(rho*g)
        dc=cest-g
        dc=np.maximum(dc,d0[sl].astype(np.int64))  # true d >= observed lower-C d
        dc=shrink_co(dc,uncertainty[sl])
        phase_out=np.where(target_c,dc,phase_out)
        changed_phase=(target_g|target_c)&(phase_out!=dcurrent[sl])
        out[sl]=phase_out
        changed[sl]|=changed_phase

    rb=red|blue
    targeted=masks['green_only']|(masks['colour_only'] if use_colour_only else False)
    # Reliable anchors, both-censored anchors and non-target censor cases stay exact.
    assert np.array_equal(out[rb&~targeted],dcurrent[rb&~targeted])
    return out.astype(np.int32),current.astype(np.int32),masks,changed,ratio_available

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
    rows=[];preserve={m:True for m in MODES}
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
                        _,_,current,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        for mode in MODES:
                            filled,current2,masks,changed,available=reconstruct(norm,sensor,cfa,n[0],n[2],probe,mode)
                            assert np.array_equal(current2,current)
                            target=masks['green_only']|(masks['colour_only'] if mode.startswith('single_') else False)
                            preserve[mode] &= np.array_equal(filled[~target],probe.stages(norm,cfa,n[0],n[2],shrink=True)[1][~target])
                            carrier=carrier_from_diff(filled,current,cfa)
                            cam=probe.consume(carrier,base,cfa,n[0],n[2])
                            assert np.array_equal(cam[...,1],base[...,1])
                            mm[mode]=metrics(cam,truth,scale,n)
                            stats[mode]=dict(
                                green_only_fraction=float(masks['green_only'].mean()),
                                colour_only_fraction=float(masks['colour_only'].mean()),
                                both_fraction=float(masks['both'].mean()),
                                changed_diff_samples=int(changed.sum()),
                                changed_carrier_samples=int(np.count_nonzero(carrier!=current)),
                                ratio_target_available_fraction=float((available&target).sum()/max(int(target.sum()),1)))
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
            non_target_diff_exact=bool(preserve[mode]),
            mean_green_only_fraction=float(np.mean([r['reconstruction'][mode]['green_only_fraction'] for r in rows])),
            mean_colour_only_fraction=float(np.mean([r['reconstruction'][mode]['colour_only_fraction'] for r in rows])),
            mean_both_fraction=float(np.mean([r['reconstruction'][mode]['both_fraction'] for r in rows])),
            changed_diff_total=int(sum(r['reconstruction'][mode]['changed_diff_samples'] for r in rows)),
            changed_carrier_total=int(sum(r['reconstruction'][mode]['changed_carrier_samples'] for r in rows)))
    return dict(schema='m9.detail1r.ratio_censor_recon.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,ratio_limits=[RATIO_MIN,RATIO_MAX],
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Chromaticity ratio propagated only from fully uncensored same-colour anchors. Green-only and optionally colour-only single-sided censor cases reconstructed with one-sided bounds; both-censored cases abstain. Native green/Sharp and downstream rendering unchanged; no hue/subject classifier or APK mutation.')

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
