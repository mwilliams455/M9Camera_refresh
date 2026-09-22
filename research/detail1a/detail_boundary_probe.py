"""Causal decomposition of GL2G -> DETAIL1D, not a new renderer candidate.

Cross two changes: MHC/carrier colour differences and old/scaled green offset.
Both endpoints must reproduce the native controls exactly inside support.
Co is also removed as a diagnostic. All outputs retain native GL2G green/Sharp.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter
import true_mhc_factorial as f

BASE='GL2G_native'
NAMES=(BASE,'MHC_scaled_offset','carrier_old_offset','DETAIL1D','DETAIL1D_Co_off')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def make_fields(native,probe,raw,cfa,nr,nb):
    base=native.render('sharp',raw,nr,nb,cfa)
    mhc=native.render('true_mhc',raw,nr,nb,cfa)
    fields={}
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    for shrink in (False,True):
        carrier=probe.stages(raw,cfa,nr,nb,shrink=shrink)[2]
        fields[shrink]=[f.direct_field(carrier,1-ry,1-rx),f.direct_field(carrier,ry,rx)]
        if shrink:
            expected=probe.consume(carrier,base,cfa,nr,nb)
    return base,mhc,fields,expected

def variants(base,mhc,fields,nr,nb,expected):
    mq=f.q14(mhc);sg=f.q14(base[...,1]);mg=mq[...,1];delta=sg-mg
    old=f.q16(mq+delta[...,None])
    assert np.array_equal(old[10:-10,10:-10],base[10:-10,10:-10]),'GL2G endpoint identity'
    cams={name:base.copy() for name in NAMES}
    for i,(ch,nc) in enumerate(((0,nr),(2,nb))):
        estimates={
            'MHC_scaled_offset':mq[...,ch]+nc*delta,
            'carrier_old_offset':nc*(mg+fields[True][i])+delta,
            'DETAIL1D':nc*(sg+fields[True][i]),
            'DETAIL1D_Co_off':nc*(sg+fields[False][i])}
        for name,value in estimates.items():
            cams[name][10:-10,10:-10,ch]=f.q16(f.llround(value))[10:-10,10:-10]
    assert np.array_equal(cams['DETAIL1D'],expected),'D endpoint identity'
    for cam in cams.values():assert np.array_equal(cam[...,1],base[...,1])
    return cams

def attribution(base,mhc,fields,nr,nb,dcam,masks):
    """Exact additive budget for camera Q14 change; summaries in WB Q14 units.

    Carrier term uses Co off. Co, offset scaling, and rounding/clipping remain
    separate. Mean contributions are signed, not explained-variance percentages.
    Native border is excluded from every mask.
    """
    mq=f.q14(mhc);bq=f.q14(base);dq=f.q14(dcam);sg=bq[...,1];mg=mq[...,1];delta=sg-mg
    accum={};maxerr=0.
    for i,(ch,nc) in enumerate(((0,nr),(2,nb))):
        d0=fields[False][i];d1=fields[True][i]
        parts={
            'carrier_replaces_MHC':nc*d0-mq[...,ch]+nc*mg,
            'Co_shrink':nc*(d1-d0),
            'offset_scaling':(nc-1.)*delta}
        actual=(dq[...,ch]-bq[...,ch]).astype(np.float64)
        pre=sum(parts.values());parts['rounding_and_clipping']=actual-pre
        err=np.abs(sum(parts.values())-actual)[10:-10,10:-10]
        maxerr=max(maxerr,float(err.max()))
        assert maxerr<1e-9
        parts['actual']=actual
        for name,value in parts.items():
            if name not in accum:accum[name]=value/nc/2
            else:accum[name]+=value/nc/2
    # Common chroma change = 0.5 * (delta R/nR + delta B/nB), since G is fixed.
    out={}
    for maskname,mask in masks.items():
        mask=np.array(mask,dtype=bool,copy=True);mask[:10]=False;mask[-10:]=False;mask[:,:10]=False;mask[:,-10:]=False
        row={'pixels':int(mask.sum()),'common_chroma_change_WB_Q14':{}}
        for name,value in accum.items():
            a=value[mask]
            row['common_chroma_change_WB_Q14'][name]=dict(mean=float(a.mean()) if a.size else None,
                mean_abs=float(np.abs(a).mean()) if a.size else None,
                positive_fraction=float((a>1e-9).mean()) if a.size else None,
                negative_fraction=float((a<-1e-9).mean()) if a.size else None)
        out[maskname]=row
    return dict(max_additive_identity_error_Q14=maxerr,masks=out)

def impulse_support(probe):
    """Show actual carrier footprint at a measured R/B anchor, without Co.

    A Q14 impulse of 256 maps through two diagonal means to a 3x3 binomial
    kernel on its original CFA lattice. This is an operator measurement, not a
    full image-quality test and not a proposed filter.
    """
    result=[]
    for cfa in range(4):
        ry=int(cfa in (2,3));rx=int(cfa in (1,3));shape=(48,48)
        for ch,py,px in [('R',ry,rx),('B',1-ry,1-rx)]:
            y=24+py;x=24+px
            diff=np.zeros(shape,np.int32);diff[y,x]=256
            ca=f.diagonal_carrier(diff,cfa)
            field=f.direct_field(ca,1-py,1-px)
            patch=field[y-2:y+3:2,x-2:x+3:2]
            expected=np.array([[16,32,16],[32,64,32],[16,32,16]])
            assert np.array_equal(patch,expected)
            result.append(dict(cfa=cfa,channel=ch,measured_anchor_own_sample_weight=float(field[y,x]/256),
                original_phase_3x3_weights=(patch/256).tolist()))
    return result

def synthetic(native,probe,prior):
    yy,xx=np.indices((160,192));n=np.array(prior['neutral']);scale=prior['representation_scale'];rows=[]
    assert native.source_sha256==prior['native_source_sha256']
    for cfa in range(4):
        red,blue,_=f.cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in f.BACKGROUNDS.items():
                    for subject,fg in f.SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(np.float64)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        obs=np.minimum(scene*n,1.)
                        samples=np.where(red,obs[...,0],np.where(blue,obs[...,2],obs[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        raw=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)
                        base,mhc,fields,expected=make_fields(native,probe,raw,cfa,n[0],n[2])
                        cams=variants(base,mhc,fields,n[0],n[2],expected)
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),
                            metrics={name:f.metrics(cam,np.clip(scene,0,1),scale,n) for name,cam in cams.items()})
                        old=prior['cases'][len(rows)]
                        for k in ('cfa','shape','sigma','background','subject'):assert row[k]==old[k]
                        for name in (BASE,'DETAIL1D'):
                            for metric in f.METRICS:assert abs(row['metrics'][name][metric]-old['metrics'][name][metric])<1e-14
                        if subject=='neutral' and bgname=='neutral' and sigma==0:
                            row['attribution']=attribution(base,mhc,fields,n[0],n[2],cams['DETAIL1D'],{'all':np.ones(raw.shape,bool)})
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={name:{label:f.comparison(rows,BASE,name,mask) for label,mask in
        [('all',None),('clipped',lambda r:r['raw_clipped_fraction']>0),('unclipped',lambda r:r['raw_clipped_fraction']==0)]}
        for name in NAMES}
    # Effects of each axis conditional on the other; clipping/rounding may interact.
    edges={label:f.comparison(rows,a,b) for label,a,b in [
        ('scale_offset_with_MHC',BASE,'MHC_scaled_offset'),
        ('scale_offset_with_carrier','carrier_old_offset','DETAIL1D'),
        ('replace_chroma_with_old_offset',BASE,'carrier_old_offset'),
        ('replace_chroma_with_scaled_offset','MHC_scaled_offset','DETAIL1D'),
        ('Co_shrink_with_D','DETAIL1D_Co_off','DETAIL1D')]}
    return dict(schema='m9.detail_boundary.v1',case_count=len(rows),baseline=BASE,neutral=n.tolist(),
        representation_scale=scale,native_source_sha256=native.source_sha256,
        endpoint_RGB_exact_all_cases=True,all_native_green_samples_exact=True,prior_endpoint_metrics_exact=True,
        carrier_impulse_support=impulse_support(probe),summary=summary,conditional_effects=edges,cases=rows,
        scope='Historical two-axis counterfactual diagnostics, not accepted candidates. Native green and Sharp fixed; no app mutation. Known-scene RGB truth and inherited metrics; one neutral and one Sharp row. Co-off carrier term includes guide/interpolation differences versus MHC; it is not uniquely attributable to just one kernel.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['assembled','prior-report','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=f.NativePair(repo,a.assembled,a.out/'native');probe=f.DomainProbe(a.out/'native')
    r=synthetic(native,probe,json.loads(a.prior_report.read_text()))
    r.update(script_sha256=sha(__file__),prior_report_sha256=sha(a.prior_report),factorial_sha256=sha(f.__file__))
    (a.out/'report.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
