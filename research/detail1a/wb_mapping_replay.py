"""Test a coherent phone WB/green/RB signal mapping; research, not an APK patch.

Recovered: Q14 gain normalization, pre-green clamp, native green/Sharp and R/B.
Adapted: map the phone's black-subtracted NORM030 data to physical white=16383,
use pedestal zero, and undo WB before the unchanged downstream colour code.
Original M9 sensor calibration/black-level processing is not claimed recovered.
The stored-domain control deliberately retains NORM030's arbitrary white scale.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
from native import Native
from rb_domain import DomainProbe
from rb_probe import q16
from detail1h import dng_inputs, TiledDetail
from downstream import Downstream
from fringe_replay import cfa_masks, pink_mask
from censored_chroma_probe import BACKGROUNDS, SUBJECTS


def phone_gains(neutral):
    """Phone adaptation: green-relative reciprocal, then min-normalize in Q14.

    This models the recovered tail within its non-overflowing range. It does
    not substitute the DNG neutral for M9's unrecovered upstream estimator.
    Reject unsupported ratios instead of copying firmware overflow/narrowing.
    """
    n=np.asarray(neutral,dtype=float)
    assert n.shape==(3,) and np.all(np.isfinite(n)) and np.all(n>0) and n[1]==1.
    assert np.all((n>=.25)&(n<=2.)), 'outside the tested gain-tail input domain'
    preliminary=np.floor(16384/n).astype(np.int64)
    factor=16384 if preliminary.min()>=16384 else 268435456//preliminary.min()
    products=preliminary*factor
    assert np.all(products<2**31)
    gains=np.maximum(products//16384,16384)
    gains[np.isin(gains,[16383,16385])]=16384
    assert np.all(gains<=65535) and np.any(gains==16384)
    return gains


def mapped(native,probe,norm,cfa,neutral,scale,domain):
    gains=phone_gains(neutral)
    red,blue,_=cfa_masks(norm.shape,cfa)
    gm=np.where(red,gains[0],np.where(blue,gains[2],gains[1]))
    restore=scale if domain=='physical' else 1.
    raw14=np.clip(np.floor(norm.astype(float)*restore*16383/65535+.5),0,16383).astype(np.int64)
    wb=q16(np.minimum(raw14*gm//16384,16383))
    base=native.render(wb,1.,1.,cfa,candidate=False)
    carrier=probe.stages(wb,cfa,1.,1.)[2]
    rgb=probe.consume(carrier,base,cfa,1.,1.)
    # Existing colour pipeline expects camera RGB before WB and before scale
    # restoration. No exposure gain or colour coefficients are changed.
    return np.clip(np.floor(rgb.astype(float)/(gains/16384)/restore+.5),0,65535).astype(np.uint16)


def synthetic(native,probe,neutral,scale):
    yy,xx=np.indices((160,192));n=np.asarray(neutral);rows=[]
    for cfa in range(4):
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43
            mask=coord>120 if shape=='edge' else coord%15<4
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
                        truth=np.clip(scene,0,1)[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        clipped=np.clip(scene,0,1)
                        old_truth=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,metrics={})
                        for mode in ('D','stored','physical'):
                            cam=dcam if mode=='D' else mapped(native,probe,norm,cfa,n,scale,mode)
                            z=np.clip(cam.astype(float)/65535*scale/n,0,1)[16:-16,16:-16]
                            row['metrics'][mode]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                scene_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-truth[...,[0,2]])**2))),
                                original_fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-old_truth[...,[0,2]])**2))))
                        rows.append(row)
    summary={}
    for mode in ('stored','physical'):
        summary[mode]={}
        for metric in rows[0]['metrics']['D']:
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),
                                       max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()))
    return dict(schema='m9.wb_mapping.synthetic.v1',case_count=len(rows),neutral=n.tolist(),representation_scale=scale,
                backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
                oracle='Keep original fixed-green R/B oracle for continuity; add full known scene after blur and physical per-channel white clipping, because this experiment changes the green signal domain. Neither reference is Leica hardware or a perceptual camera oracle. No sensor noise; unity shading; float64 synthetic normalization; inner16.',
                acceptance='No regression is hidden by changing the oracle or tolerance (1e-12). Finite fixtures alone do not establish photographic acceptance.')


def comparison(out,rendered):
    sheet=Image.new('RGB',(1224,1452),'#16191c');d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    d.text((12,12),'WB and reconstruction together — research replay, no accepted fix',font=font,fill='white')
    d.text((12,43),'Same RAW, colour and exposure. Physical-white probe still leaves fringes; see colour-test results.',font=small,fill='#ffc986')
    for col,(key,title) in enumerate([('H','Current DETAIL1H'),('stored','WB in scaled buffer (control)'),('physical','WB at physical RAW white')]):
        d.text((col*408+12,89),title,font=font,fill='white');im=np.rot90(rendered[key],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+row*432;d.text((col*408+12,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(im[y:y+384,x:x+384]),(col*408+12,top))
    sheet.save(out/'WB-reconstruction-comparison.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(a.raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(a.raw);nr,_,nb=meta['neutral'];scale=meta['representation_scale'];cfa=meta['cfa']
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native')
    colour=Downstream(repo,a.assembled,a.out/'colour');colour.configure(a.raw)
    base=native.render(norm,nr,nb,cfa,candidate=False)
    hcam,hstats=TiledDetail(a.out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],
                                               fixture['detail1H']['rgbProfile'],gains,scale,guard=True)
    variants={};rendered={}
    for mode in ('H','stored','physical'):
        cam=hcam if mode=='H' else mapped(native,probe,norm,cfa,meta['neutral'],scale,mode)
        rgb=colour.render(colour.restore(cam,scale),fixture['actual_render_gain']);rendered[mode]=rgb
        variants[mode]=dict(pink_pixels=int(pink_mask(rgb).sum()),
                            changed_green_samples=int(np.count_nonzero(cam[...,1]!=base[...,1])),guard=mode=='H')
        Image.fromarray(np.rot90(rgb,3)).save(a.out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,variants[mode],flush=True)
    comparison(a.out,rendered)
    syn=synthetic(native,probe,meta['neutral'],scale);cases=syn.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(syn,indent=2)[:-2]+',\n  "cases": [\n'+
                                      ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    report=dict(schema='m9.wb_mapping.replay.v1',raw_sha256=fixture['dng_sha256'],
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                gains_q14=phone_gains(meta['neutral']).tolist(),metadata=meta,
                actual_render_gain=fixture['actual_render_gain'],variants=variants,H_stats=hstats,
                synthetic_summary=syn['summary'],synthetic_case_count=syn['case_count'],
                spatial_source_hashes=native.source_hashes,colour_source_hashes=colour.hashes,
                photographic_acceptance_passed=False,android_implementation_changed=False,auto_exposure_changed=False,
                scope='Physical-white mapping is an explicit phone adaptation, not recovered M9 sensor calibration. Green/Sharp algorithm and ISO slot unchanged but input domain changes. Probes have guard off; existing H variance model is not transplanted.')
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(syn['summary'],indent=2))


if __name__=='__main__':main()
