"""Independent coherent-RGB control, explicitly allowing green to change.

Research only: DCB is not recovered M9 processing. The sharpened variant uses
the existing native ISO160 Sharp routine on DCB green, then applies its common
correction to all WB-neutralized channels. Exposure and colour stay fixed.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter
from native import Native
from rb_domain import DomainProbe
from rb_probe import q14,q16
from fringe_replay import cfa_masks
from demosaic_control import Control,local_control
from censored_chroma_probe import BACKGROUNDS,SUBJECTS

MODES=('fixed_green','coherent','coherent_sharp','coherent_native_detail')


def variants(native,probe,control,norm,base,sensor,cfa,neutral,white=1023):
    n=np.asarray(neutral);red,blue,_=cfa_masks(norm.shape,cfa)
    nc=np.where(red,n[0],np.where(blue,n[2],1.));headroom=max(1.,1/n[0],1/n[2])
    encoded=np.floor(norm.astype(float)/nc/headroom+.5)
    assert encoded.min()>=0 and encoded.max()<=65535
    rgb=control.demosaic(encoded.astype(np.uint16),cfa,rawpy.DemosaicAlgorithm.DCB).astype(float)*headroom
    g14=np.clip(np.floor(rgb[...,1]*16383/65535+.5),0,16383).astype(np.uint16)
    sg=q16(native.sharp(g14,0,candidate=False)).astype(float)
    original_green=q16(probe.stages(norm,cfa,n[0],n[2])[0]).astype(float)
    original_detail=base[...,1].astype(float)-original_green
    for mode in MODES:
        if mode=='fixed_green':z=rgb-rgb[...,[1]]+base[...,[1]]
        elif mode=='coherent_sharp':z=rgb-rgb[...,[1]]+sg[...,None]
        elif mode=='coherent_native_detail':z=rgb+original_detail[...,None]
        else:z=rgb
        cam=np.clip(np.floor(z*n+.5),0,65535).astype(np.uint16)
        cam[:10]=base[:10];cam[-10:]=base[-10:];cam[:,:10]=base[:,:10];cam[:,-10:]=base[:,-10:]
        yield mode,local_control(cam,base,sensor,white)


def synthetic(native,probe,control,cfas):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052;rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa,candidate=False)
                        dcam=probe.consume(probe.stages(norm,cfa,n[0],n[2])[2],base,cfa,n[0],n[2])
                        clipped=np.clip(scene,0,1);truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,metrics={})
                        for mode,cam in [('D',dcam),*variants(native,probe,control,norm,dcam,sensor,cfa,n)]:
                            z=np.clip(cam.astype(float)/65535*scale/n,0,1)[16:-16,16:-16]
                            row['metrics'][mode]=dict(scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                scene_chroma_rms=float(np.sqrt(np.mean(((z[...,[0,2]]-z[...,[1]])-(truth[...,[0,2]]-truth[...,[1]]))**2))))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in MODES:
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms','scene_chroma_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),max_rms_increase=float(delta.max()),
                mean_rms_change=float(delta.mean()),worst_case_index=int(delta.argmax()))
    return dict(schema='m9.coherent_green_probe.v1',case_count=len(rows),cases=rows,summary=summary,
                neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
                scope='Independent local DCB controls; coherent modes change green. Old fixed-green reference retained as a historical comparison, not redefined. Additional scene-chroma error has no sharpening reference. No noise, unity shading, inner16.',
                accepted=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');control=Control(a.out/'temporary')
    result=synthetic(native,probe,control,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['spatial_source_hashes']=native.source_hashes
    result['rawpy_version']=rawpy.__version__;result['libraw_version']=rawpy.libraw_version
    cases=result.pop('cases');(a.out/'synthetic.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
