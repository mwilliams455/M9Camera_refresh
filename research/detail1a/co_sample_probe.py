"""Isolate Co shrink and measured-CFA consistency in the corrected no-Sharp factorial.

The existing eight guide/interpolation/output-green cells are each run with
Co on and off. On cells must reproduce the prior 1,536-case report. Sharp and
Noise2 remain absent. The actual frozen internal MHC is a separate reference.
Measured-sample audits use camera Q14; truth metrics use WB linear camera RGB.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.ndimage import gaussian_filter
import true_mhc_factorial as f

BASE=f.BASE+'_coOn'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def measured_stats(cam,raw,cfa):
    z=f.q14(cam)[16:-16,16:-16];r=f.q14(raw)[16:-16,16:-16]
    red,blue,green=f.cfa_masks(raw.shape,cfa)
    result={}
    for ch,name,mask in [(0,'R',red),(1,'G',green),(2,'B',blue)]:
        m=mask[16:-16,16:-16];error=z[...,ch][m]-r[m];a=np.abs(error)
        result[name]=dict(samples=int(m.sum()),changed_exact=int(np.count_nonzero(error)),
            changed_gt1_q14=int((a>1).sum()),max_abs_q14=int(a.max()),
            mean_abs_q14=float(a.mean()),mean_signed_q14=float(error.mean()))
    return result

def phase_metrics(cam,truth,scale,n,cfa):
    z=f.restored(cam,scale,n)[16:-16,16:-16];t=truth[16:-16,16:-16]
    rd=z[...,[0,2]]-z[...,[1]];td=t[...,[0,2]]-t[...,[1]]
    mag=rd.min(-1)-td.min(-1)>.02
    gr=(-rd).min(-1)-(-td).min(-1)>.02
    error=z-t;red,blue,green=f.cfa_masks(cam.shape[:2],cfa)
    result={}
    for label,mask in [('R',red),('G',green),('B',blue)]:
        m=mask[16:-16,16:-16];e=error[m]
        result[label]=dict(false_magenta_fraction=float(mag[m].mean()),false_green_fraction=float(gr[m].mean()),
                           mean_signed_rgb_error=e.mean(0).tolist(),rgb_channel_rms=np.sqrt((e*e).mean(0)).tolist())
    return result

def variants(native,probe,raw,cfa,nr,nb):
    leica=native.render('nosharp',raw,nr,nb,cfa)
    mhc=native.render('true_mhc',raw,nr,nb,cfa)
    gd,d_on,c_on,unc=probe.stages(raw,cfa,nr,nb,shrink=True)
    _,d_off,c_off,_=probe.stages(raw,cfa,nr,nb,shrink=False)
    gm=f.q14(mhc[...,1]);zero=np.zeros_like(unc)
    m_on=f.guide_diff(raw,cfa,nr,nb,gm,unc);m_off=f.guide_diff(raw,cfa,nr,nb,gm,zero)
    assert np.array_equal(f.guide_diff(raw,cfa,nr,nb,gd,unc),d_on)
    assert np.array_equal(f.guide_diff(raw,cfa,nr,nb,gd,zero),d_off)
    assert np.array_equal(f.diagonal_carrier(d_off,cfa),c_off)
    out_m=leica.copy();out_m[10:-10,10:-10,1]=mhc[10:-10,10:-10,1]
    bases={'Leica':leica,'MHC':out_m};cams={};shrink_audit={}
    red,blue,_=f.cfa_masks(raw.shape,cfa);rb=(red|blue)[16:-16,16:-16]
    raw14=f.q14(raw)
    for guide,off,on in [('D',d_off,d_on),('M',m_off,m_on)]:
        delta=(on.astype(np.int64)-off)[16:-16,16:-16][rb]
        shrink_audit[guide]=dict(rb_sites=int(rb.sum()),changed_sites=int(np.count_nonzero(delta)),
            max_abs_difference14_change=int(np.abs(delta).max()),mean_abs_difference14_change=float(np.abs(delta).mean()))
        for state,diff in [('On',on),('Off',off)]:
            carrier=f.diagonal_carrier(diff,cfa)
            for output,base in bases.items():
                prefix=f'g{guide}_i';suffix=f'_o{output}_co{state}'
                cams[prefix+'Cross'+suffix]=probe.consume(carrier,base,cfa,nr,nb)
                direct=f.direct_consume(diff,base,cfa,nr,nb)
                cams[prefix+'Direct'+suffix]=direct
                # Independent anchor equation: interpolation must retain its own phase.
                sg=f.q14(base[...,1])
                for ch,mask,nc in [(0,red,nr),(2,blue,nb)]:
                    target=np.clip(f.llround(nc*(sg+diff)),0,16383)
                    m=mask[16:-16,16:-16]
                    got=f.q14(direct[...,ch])[16:-16,16:-16][m]
                    assert np.array_equal(got,target[16:-16,16:-16][m]),'direct anchor equation failed'
                    if state=='Off' and (guide,output) in [('D','Leica'),('M','MHC')]:
                        assert np.abs(got-raw14[16:-16,16:-16][m]).max()<=1,'coherent Co-off measured R/B changed'
    cams['MHC_rgb']=mhc
    return cams,shrink_audit

def controls(native,probe):
    rng=np.random.default_rng(9222027);count=0
    for cfa in range(4):
        raw=rng.integers(0,65536,(48,50),dtype=np.uint16)
        for nr,nb in [(.25,.5),(1.5,.8),(1.,1.)]:
            cams,audit=variants(native,probe,raw,cfa,nr,nb)
            for mode in ['gD_iDirect_oLeica_coOff','gM_iDirect_oMHC_coOff']:
                v=measured_stats(cams[mode],raw,cfa)
                assert v['R']['changed_gt1_q14']==v['B']['changed_gt1_q14']==0
                if mode.startswith('gM'):assert v['G']['changed_exact']==0
            # Every Co-on cell must be byte-identical to the previous experiment.
            old,_,_=f.variants(native,probe,raw,cfa,nr,nb,include_sharp=False)
            for mode,cam in old.items():
                if mode.startswith('g'):assert np.array_equal(cams[mode+'_coOn'],cam),(cfa,mode)
            count+=1
    return dict(random_all_CFA_neutral_cases=count,all_eight_Co_on_cells_byte_exact=True,
        coherent_direct_Co_off_RB_within_one_Q14=True,MHC_direct_Co_off_measured_G_exact=True,
        direct_anchor_equations_checked_for_every_variant=True)

def aggregate_anchors(rows):
    result={}
    for mode in rows[0]['measured_samples']:
        result[mode]={}
        for ch in ('R','G','B'):
            vals=[r['measured_samples'][mode][ch] for r in rows];samples=sum(v['samples'] for v in vals)
            result[mode][ch]=dict(samples=samples,
                changed_exact=sum(v['changed_exact'] for v in vals),
                changed_gt1_q14=sum(v['changed_gt1_q14'] for v in vals),
                max_abs_q14=max(v['max_abs_q14'] for v in vals),
                mean_abs_q14=sum(v['mean_abs_q14']*v['samples'] for v in vals)/samples)
    return result

def summarize(rows):
    modes=list(rows[0]['metrics']);summary={};contrasts={}
    subsets={'all':None,'clipped':lambda r:r['raw_clipped_fraction']>0,'unclipped':lambda r:r['raw_clipped_fraction']==0}
    for name in modes:
        summary[name]={k:f.comparison(rows,BASE,name,mask) for k,mask in subsets.items()}
        if name.endswith('_coOff'):
            on=name[:-3]+'On'
            contrasts[name]={k:f.comparison(rows,on,name,mask) for k,mask in subsets.items()}
    passers=[name for name in modes if name!=BASE and all(summary[name]['all'][k]['cases_worse']==0
        for k in ('false_magenta_excess_fraction','false_green_excess_fraction'))]
    return summary,contrasts,passers

def synthetic(native,probe,prior,out):
    yy,xx=np.indices((160,192));n=np.array(prior['neutral']);scale=prior['representation_scale'];rows=[]
    assert sha(Path(f.__file__))==prior['script_sha256']
    for cfa in range(4):
        red,blue,_=f.cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in f.BACKGROUNDS.items():
                    for subject,fg in f.SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(np.float64)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)
                        cams,audit=variants(native,probe,norm,cfa,n[0],n[2]);truth=np.clip(scene,0,1)
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),shrink_audit=audit,
                            metrics={k:f.metrics(v,truth,scale,n) for k,v in cams.items()},
                            measured_samples={k:measured_stats(v,norm,cfa) for k,v in cams.items()},
                            phase_errors={k:phase_metrics(v,truth,scale,n,cfa) for k,v in cams.items()})
                        old=prior['cases'][len(rows)]
                        for k in ('cfa','shape','sigma','background','subject'):assert old[k]==row[k]
                        for mode in cams:
                            oldmode=mode[:-5] if mode.endswith('_coOn') else mode
                            if oldmode not in old['metrics']:continue
                            for key in f.METRICS:assert abs(row['metrics'][mode][key]-old['metrics'][oldmode][key])<1e-14,(mode,key)
                        rows.append(row)
        (out/'checkpoint.json').write_text(json.dumps(dict(cases_completed=len(rows),cfa_completed=cfa)))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary,contrasts,passers=summarize(rows)
    return dict(schema='m9.co_sample_consistency.v1',case_count=len(rows),baseline=BASE,
        native_source_sha256=native.source_sha256,neutral=n.tolist(),representation_scale=scale,
        previous_Co_on_metrics_exact=True,summary=summary,co_off_minus_on=contrasts,
        measured_samples=aggregate_anchors(rows),strict_zero_false_chroma_regression=passers,
        scope='Sixteen cells: original corrected 2x2x2 factorial with Co on/off. Sharp and Noise2 absent. Co uncertainty is the original D signal. MHC_rgb is a separate frozen internal control. Measured-sample audit uses camera Q14, tolerating one unit for double rounding; truth metrics use clipped WB linear camera RGB. Crop16 excludes borders.',cases=rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--prior-report',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2];native=f.NativePair(repo,a.assembled,a.out/'native');probe=f.DomainProbe(a.out/'native')
    checks=controls(native,probe);print('Controls passed',checks,flush=True)
    prior=json.loads(a.prior_report.read_text());assert prior['case_count']==1536
    result=synthetic(native,probe,prior,a.out)
    result.update(controls=checks,script_sha256=sha(__file__),prior_report_sha256=sha(a.prior_report),
                  prior_probe_sha256=sha(Path(f.__file__)))
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASSERS',result['strict_zero_false_chroma_regression'],flush=True)

if __name__=='__main__':main()
