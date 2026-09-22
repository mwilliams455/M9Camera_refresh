"""Regression isolation against the actual pre-DETAIL GL2G native RGB output.

Keep native green, ISO160 Sharp, normalization and colour inputs fixed while
comparing GL2G with DETAIL1C/D. Include the earlier internal MHC and no-Sharp
references, explicitly distinguishing a Sharp toggle from a rollback.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter
import true_mhc_factorial as f
from rb_probe import RbProbe

BASE='GL2G_native'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def variants(native,probe,old_probe,raw,cfa,nr,nb):
    native_rgb=native.render('sharp',raw,nr,nb,cfa)
    true_mhc=native.render('true_mhc',raw,nr,nb,cfa)
    no_sharp=native.render('nosharp',raw,nr,nb,cfa)
    carrier=probe.stages(raw,cfa,nr,nb,shrink=True)[2]
    d=probe.consume(carrier,native_rgb,cfa,nr,nb)
    c=old_probe.consume(old_probe.stages(raw,cfa,shrink=True)[2],native_rgb,cfa)
    assert np.array_equal(c[...,1],native_rgb[...,1])
    assert np.array_equal(d[...,1],native_rgb[...,1])
    # Exact operator identity for the historical SHARPSOURCE1C/RBANCHOR1A.
    # It adds the same camera-domain offset to all channels, before later WB.
    mq=f.q14(true_mhc);sg=f.q14(native_rgb[...,1]);delta=sg-mq[...,1]
    expected=f.q16(mq+delta[...,None])
    assert np.array_equal(expected[9:-9,9:-9],native_rgb[9:-9,9:-9]),'native graft equation changed'
    return {BASE:native_rgb,'DETAIL1C_failed':c,'DETAIL1D':d,
        'MHC_before_Sharp_math':true_mhc,'native_Sharp_off_only':no_sharp,
        'DETAIL1D_Sharp_off':probe.consume(carrier,no_sharp,cfa,nr,nb)}

def domain_audit():
    n=np.array([.41796875,1.,.6435546875]);g=4096.;base=n*g;out=[]
    for delta in [-512.,512.]:
        old=base+delta;old_wb=old/n
        consistent=base+n*delta;consistent_wb=consistent/n
        assert np.allclose(consistent_wb,consistent_wb[1],atol=1e-12)
        observed=old_wb[[0,2]]-old_wb[1]
        expected=delta*(1/n[[0,2]]-1)
        assert np.allclose(observed,expected,atol=1e-12)
        out.append(dict(delta=delta,old_WB_R_minus_G=float(observed[0]),
            old_WB_B_minus_G=float(observed[1]),unit_consistent_WB_chroma_max=float(np.max(np.abs(consistent_wb-consistent_wb[1])))))
    return dict(neutral=n.tolist(),green=4096.,examples=out,
        scope='Unclipped real-valued arithmetic of the historical uniform camera-RGB graft. This identifies a unit mismatch, not a complete replacement renderer. Production rounding/clipping and the later colour transform are excluded from this illustrative equation.')

def synthetic(native,probe,old_probe,prior):
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
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)
                        cams=variants(native,probe,old_probe,norm,cfa,n[0],n[2])
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),
                            metrics={k:f.metrics(v,np.clip(scene,0,1),scale,n) for k,v in cams.items()})
                        old=prior['cases'][len(rows)]
                        for k in ('cfa','shape','sigma','background','subject'):assert row[k]==old[k]
                        for name,oldname in [('DETAIL1D','D_sharp_ref'),('MHC_before_Sharp_math','MHC_rgb'),
                            ('native_Sharp_off_only','MHC_reanchored_Leica'),('DETAIL1D_Sharp_off','gD_iCross_oLeica')]:
                            for k in f.METRICS:assert abs(row['metrics'][name][k]-old['metrics'][oldname][k])<1e-14
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={name:{label:f.comparison(rows,BASE,name,mask) for label,mask in
        [('all',None),('clipped',lambda r:r['raw_clipped_fraction']>0),('unclipped',lambda r:r['raw_clipped_fraction']==0)]}
        for name in rows[0]['metrics']}
    return dict(schema='m9.iso_sharp_regression.v1',case_count=len(rows),baseline=BASE,
        neutral=n.tolist(),representation_scale=scale,native_source_sha256=native.source_sha256,
        native_green_Sharp_exact_for_C_and_D=True,prior_four_control_metrics_exact=True,
        uniform_camera_RGB_graft_identity_exact_all_cases=True,domain_audit=domain_audit(),summary=summary,
        commits=dict(ISO_replay='49b0070',DETAIL1C='62861ef',DETAIL1D='78075a36b01d722f8a42566f201752bddef75505',
            DETAIL1H_phone_integration='0726b579055b0ffade7f18f8a8667efdf1333df5',
            first_Sharp_closure='f06c7a6260030f4720ac291cd1d6de85114ea4a6',RBANCHOR1A='f6aa2b4fbfa94d47122744a1082f26df787b5f08'),
        scope='Actual frozen GL2G native RGB is the pre-DETAIL control. C and D change only R/B while native green and Sharp remain bit-identical. Internal MHC is an earlier mathematical-stage control, not a complete historical APK replay. No new demosaic or sharpening candidate and no app mutation.',cases=rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['assembled','prior-report','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=f.NativePair(repo,a.assembled,a.out/'native');probe=f.DomainProbe(a.out/'native');old=RbProbe(a.out/'native')
    r=synthetic(native,probe,old,json.loads(a.prior_report.read_text()))
    r.update(script_sha256=sha(__file__),prior_report_sha256=sha(a.prior_report),base_probe_sha256=sha(f.__file__))
    (a.out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print('Completed historical-control regression isolation',flush=True)

if __name__=='__main__':main()
