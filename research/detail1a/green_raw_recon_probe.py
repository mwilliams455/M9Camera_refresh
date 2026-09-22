"""M9DETAIL1S / GREENRAWRECON1A: reconstruct clipped green CFA samples before demosaic.

DETAIL1Q/R showed that correcting R/B colour differences while leaving the
original clipped green plane can simply trade false magenta for false green.
This probe moves the intervention to the missing measurement itself.

Only sensor-white-censored GREEN CFA samples may change.  R/B samples and every
uncensored green sample remain exact.  Local R/G and B/G chromaticity is learned
only from anchors whose colour sample and cardinal green support are both
uncensored.  For a clipped green CFA site, each surviving cardinal R/B sample
provides:
    G_est = (C/nC) / rho_C
where rho_C is the propagated local C/G ratio for that colour phase.

Candidates either take the median of available estimates or require red-derived
and blue-derived luminance estimates to agree before reconstructing.  The
reconstructed green is bounded below by the recorded clipped value and above by
the wider 14-bit representation headroom.  The resulting RAW is then passed
through the unchanged native demosaic, exact ISO160 Leica Sharp, DETAIL1D
carrier and consumer.

No hue, subject, foliage or wildlife classifier. Research only; no APK change.
"""
from pathlib import Path
import argparse,hashlib,json,warnings
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,convolve

from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe
from rb_probe import q14,q16

MODES=('median_h8','rb25_nearest','rb25_h8','rb50_h8','rb25_h24')
CROSS=np.array([[0.,.25,0.],[.25,0.,.25],[0.,.25,0.]],np.float64)
RATIO_MIN=1/64
RATIO_MAX=64.

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

def support_masks(sensor,cfa,white=1023):
    red,blue,green=cfa_masks(sensor.shape,cfa)
    clipped=sensor>=white
    gc=(np.roll(clipped,1,0)|np.roll(clipped,-1,0)|
        np.roll(clipped,1,1)|np.roll(clipped,-1,1))
    rb=red|blue
    reliable=rb&~clipped&~gc
    for m in (reliable,):
        m[:2]=False;m[-2:]=False;m[:,:2]=False;m[:,-2:]=False
    return red,blue,green,clipped,reliable

def fill_log_ratio(logrho,known,iters):
    if not np.any(known):return np.array(logrho,copy=True),False
    missing=~known
    _,idx=distance_transform_edt(missing,return_indices=True)
    work=np.asarray(logrho,np.float64)[tuple(idx)]
    work[known]=logrho[known]
    for _ in range(iters):
        avg=convolve(work,CROSS,mode='nearest')
        work=np.where(missing,avg,logrho)
    return work,True

def ratio_fields(norm,sensor,cfa,nr,nb,probe,iters):
    green,_,_,_=probe.stages(norm,cfa,nr,nb,shrink=False)
    z=q14(np.asarray(norm,np.uint16)).astype(np.int64)
    red,blue,_,_,reliable=support_masks(sensor,cfa)
    rho=np.ones(norm.shape,np.float64)
    available=np.zeros(norm.shape,bool)
    colour_id=np.full(norm.shape,-1,np.int8)
    for channel_mask,nc,phase,cid in [
        (red,nr,(int(cfa in (2,3)),int(cfa in (1,3))),0),
        (blue,nb,(1-int(cfa in (2,3)),1-int(cfa in (1,3))),2)]:
        py,px=phase;sl=np.s_[py::2,px::2]
        g=green[sl].astype(np.int64)
        c=llround(z[sl].astype(np.float64)/nc)
        known=reliable[sl]&(g>0)&(c>0)
        r=np.clip(c.astype(np.float64)/np.maximum(g,1),RATIO_MIN,RATIO_MAX)
        filled,ok=fill_log_ratio(np.log(r),known,iters)
        if not ok:continue
        rho[sl]=np.exp(np.clip(filled,np.log(RATIO_MIN),np.log(RATIO_MAX)))
        available[sl]=True
        colour_id[sl]=cid
    return rho,available,colour_id,z

def shifted(a,dy,dx,fill):
    out=np.full(a.shape,fill,dtype=a.dtype)
    ys=slice(max(0,-dy),min(a.shape[0],a.shape[0]-dy))
    xs=slice(max(0,-dx),min(a.shape[1],a.shape[1]-dx))
    yd=slice(max(0,dy),min(a.shape[0],a.shape[0]+dy))
    xd=slice(max(0,dx),min(a.shape[1],a.shape[1]+dx))
    out[yd,xd]=a[ys,xs]
    return out

def reconstruct_green(norm,sensor,cfa,nr,nb,probe,mode,white=1023):
    if mode.endswith('nearest'):iters=0
    elif mode.endswith('h8'):iters=8
    elif mode.endswith('h24'):iters=24
    else:raise ValueError(mode)
    rho,available,cid,z=ratio_fields(norm,sensor,cfa,nr,nb,probe,iters)
    red,blue,green,clipped,_=support_masks(sensor,cfa,white)
    target=green&clipped

    ests=[];isred=[];valids=[]
    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
        nz=shifted(z,dy,dx,0)
        nrho=shifted(rho,dy,dx,1.)
        nav=shifted(available,dy,dx,False)
        nclip=shifted(clipped,dy,dx,True)
        ncid=shifted(cid,dy,dx,-1)
        nc=np.where(ncid==0,nr,np.where(ncid==2,nb,1.))
        cn=llround(nz.astype(np.float64)/nc)
        est=cn/np.maximum(nrho,1e-12)
        valid=target&nav&~nclip&((ncid==0)|(ncid==2))
        ests.append(est);valids.append(valid);isred.append(ncid==0)
    E=np.stack(ests,axis=0);V=np.stack(valids,axis=0);R=np.stack(isred,axis=0)
    masked=np.where(V,E,np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',category=RuntimeWarning)
        median=np.nanmedian(masked,axis=0)
        red_est=np.nanmedian(np.where(V&R,E,np.nan),axis=0)
        blue_est=np.nanmedian(np.where(V&~R,E,np.nan),axis=0)
    count=V.sum(axis=0)
    have_r=np.any(V&R,axis=0);have_b=np.any(V&~R,axis=0)
    both=have_r&have_b
    rbmean=.5*(red_est+blue_est)
    disagreement=np.abs(red_est-blue_est)/np.maximum(np.abs(rbmean),1.)

    if mode=='median_h8':
        use=target&(count>=1)&np.isfinite(median);gest=median
    else:
        tol=.25 if mode.startswith('rb25') else .50
        use=target&both&np.isfinite(rbmean)&(disagreement<=tol);gest=rbmean

    gest=np.maximum(llround(np.nan_to_num(gest,nan=0.)),z)
    gest=np.clip(gest,0,16383)
    out=np.array(norm,dtype=np.uint16,copy=True)
    out[use]=q16(gest[use])
    # Hard contract: only clipped green CFA samples can change.
    changed=out!=norm
    assert not np.any(changed&~target)
    return out,dict(target=target,use=use,count=count,disagreement=disagreement,changed=changed,
                    estimated_q14=gest)

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
    rows=[];raw_exact={m:True for m in MODES}
    for cfa in cfas:
        red,blue,green=cfa_masks(xx.shape,cfa)
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
                        current=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        true_g=np.clip(scene[...,1]/scale*16383,0,16383)
                        for mode in MODES:
                            rnorm,st=reconstruct_green(norm,sensor,cfa,n[0],n[2],probe,mode)
                            raw_exact[mode] &= np.array_equal(rnorm[~st['target']],norm[~st['target']])
                            rbase=native.render(rnorm,n[0],n[2],cfa)
                            rcarrier=probe.stages(rnorm,cfa,n[0],n[2],shrink=True)[2]
                            cam=probe.consume(rcarrier,rbase,cfa,n[0],n[2])
                            mm[mode]=metrics(cam,truth,scale,n)
                            used=st['use']
                            err=(st['estimated_q14'].astype(float)-true_g)
                            stats[mode]=dict(
                                clipped_green_fraction=float(st['target'].mean()),
                                reconstructed_green_fraction=float(used.mean()),
                                clipped_green_coverage=float(used.sum()/max(int(st['target'].sum()),1)),
                                changed_raw_samples=int(st['changed'].sum()),
                                green_estimate_rms_q14=float(np.sqrt(np.mean(err[used]**2))) if np.any(used) else 0.,
                                green_estimate_max_abs_q14=float(np.max(np.abs(err[used]))) if np.any(used) else 0.,
                                rb_disagreement_mean=float(np.nanmean(st['disagreement'][used])) if np.any(used) else 0.)
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
            non_clipped_green_and_all_rb_raw_exact=bool(raw_exact[mode]),
            mean_clipped_green_coverage=float(np.mean([r['reconstruction'][mode]['clipped_green_coverage'] for r in rows])),
            changed_raw_total=int(sum(r['reconstruction'][mode]['changed_raw_samples'] for r in rows)),
            mean_green_estimate_rms_q14=float(np.mean([r['reconstruction'][mode]['green_estimate_rms_q14'] for r in rows])))
    return dict(schema='m9.detail1s.green_raw_recon.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,ratio_limits=[RATIO_MIN,RATIO_MAX],
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Only sensor-white-censored green CFA samples may change before native demosaic/Sharp. Estimates derive from surviving cardinal R/B and chromaticity propagated from fully uncensored anchors. Native renderer/D then run unchanged. No hue/subject classifier or APK mutation.')

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
