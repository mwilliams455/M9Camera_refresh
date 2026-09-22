"""Unclipped achromatic counterexamples for the recent DETAIL carrier change.

Unity-neutral cases eliminate WB-offset scaling as an explanation. No Noise2
guard is present. Endpoints retain identical native green and Sharp.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import gaussian_filter
import detail_boundary_probe as p

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['assembled','out']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=p.f.NativePair(repo,a.assembled,a.out/'native');probe=p.f.DomainProbe(a.out/'native')
    yy,xx=np.indices((160,192));rows=[];examples=[];scale=1.6105431518598052
    for cfa in range(4):
        red,blue,_=p.f.cfa_masks(xx.shape,cfa)
        for neutral in [(1.,1.,1.),(.41796875,1.,.6435546875)]:
            n=np.array(neutral)
            for shape in ['edge','fine_branches']:
                coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
                for sigma in (0.,.5,1.,2.):
                    lum=np.where(mask,.03,.5)
                    if sigma:lum=gaussian_filter(lum,sigma)
                    truth=np.repeat(lum[...,None],3,axis=-1)
                    signal=lum*np.where(red,n[0],np.where(blue,n[2],1.))
                    sensor=np.floor(64+signal*959+.5).astype(np.uint16)
                    assert sensor.max()<1023 and sensor.min()>64
                    raw=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                    base,mhc,fields,expected=p.make_fields(native,probe,raw,cfa,n[0],n[2])
                    cams=p.variants(base,mhc,fields,n[0],n[2],expected)
                    if neutral==(1.,1.,1.):
                        assert np.array_equal(cams['MHC_scaled_offset'],base)
                        assert np.array_equal(cams['carrier_old_offset'],cams['DETAIL1D'])
                    metrics={name:p.f.metrics(cam,truth,scale,n) for name,cam in cams.items()}
                    row=dict(cfa=cfa,neutral=list(neutral),shape=shape,sigma=sigma,metrics=metrics)
                    rows.append(row)
                    if neutral==(1.,1.,1.) and shape=='edge' and sigma==2. and cfa==0:
                        # Worst increase of common R/B-vs-G at this smooth neutral edge.
                        rgb={name:p.f.restored(cam,scale,n) for name,cam in cams.items()}
                        common={name:(z[...,0]+z[...,2])*.5-z[...,1] for name,z in rgb.items()}
                        d=common['DETAIL1D']-common[p.BASE];d[:16]=-np.inf;d[-16:]=-np.inf;d[:,:16]=-np.inf;d[:,-16:]=-np.inf
                        y,x=np.unravel_index(np.argmax(d),d.shape)
                        point=np.zeros(raw.shape,bool);point[y,x]=True
                        examples.append(dict(cfa=cfa,neutral=list(neutral),shape=shape,sigma=sigma,pixel_yx=[int(y),int(x)],
                            truth_RGB=truth[y,x].tolist(),camera_scene_RGB={name:z[y,x].tolist() for name,z in rgb.items()},
                            common_chroma={name:float(z[y,x]) for name,z in common.items()},
                            signed_budget=p.attribution(base,mhc,fields,n[0],n[2],cams['DETAIL1D'],{'point':point})))
    summary={label:{name:p.f.comparison(selected,p.BASE,name) for name in p.NAMES} for label,selected in
        [('unity',[r for r in rows if r['neutral']==[1.,1.,1.]]),('unequal',[r for r in rows if r['neutral']!=[1.,1.,1.]])]}
    r=dict(schema='m9.detail_boundary.neutral.v1',case_count=len(rows),all_sensor_samples_unclipped=True,
        unity_offset_variants_byte_exact=True,native_source_sha256=native.source_sha256,script_sha256=p.sha(__file__),
        probe_sha256=p.sha(p.__file__),summary=summary,examples=examples,cases=rows,
        scope='Achromatic scene counterexamples; all native green/Sharp held fixed. Unity neutrals remove WB scaling as a cause. No Noise2. Existing Co shrink remains explicitly separable. These are not candidate fixes.')
    (a.out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print('Completed',len(rows),'unclipped neutral cases',flush=True)

if __name__=='__main__':main()
