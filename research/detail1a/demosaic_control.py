"""Independent interpolation controls for the DETAIL1H clipped-edge failure.

LibRaw AHD/DCB are offline controls, not recovered Leica routines or Android
implementations. Native green/ISO160 Sharp and downstream colour/exposure stay
fixed. WB headroom is encoded reversibly before interpolation; no white cap.
"""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import numpy as np
import rawpy
import tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, distance_transform_cdt
from native import Native
from rb_domain import DomainProbe
from detail1h import dng_inputs, TiledDetail
from downstream import Downstream
from fringe_replay import cfa_masks, pink_mask
from censored_chroma_probe import BACKGROUNDS, SUBJECTS

PARAMS=dict(output_color=rawpy.ColorSpace.raw,output_bps=16,gamma=(1,1),
            no_auto_bright=True,no_auto_scale=True,user_black=0,user_sat=65535,
            adjust_maximum_thr=0.,user_wb=[1,1,1,1],user_flip=0,median_filter_passes=0)


class Control:
    def __init__(self,work):
        self.work=Path(work);self.work.mkdir(parents=True,exist_ok=True)

    def demosaic(self,raw,cfa,algorithm):
        pattern=[(0,1,1,2),(1,0,2,1),(1,2,0,1),(2,1,1,0)][cfa]
        # A minimal temporary DNG avoids inheriting camera matrices, gain-map
        # opcodes or black levels from the real capture. No output colour LUT.
        tags=[(50706,'B',4,(1,4,0,0),False),(50707,'B',4,(1,1,0,0),False),
              (50708,'s',0,'RESEARCH CFA',False),(33421,'H',2,(2,2),False),
              (33422,'B',4,pattern,False),(50710,'B',3,(0,1,2),False),
              (50711,'H',1,1,False),(50714,'H',1,0,False),(50717,'I',1,65535,False),
              (50721,'2i',9,(1,1,0,1,0,1,0,1,1,1,0,1,0,1,0,1,1,1),False),
              (50778,'H',1,21,False)]
        with tempfile.TemporaryDirectory(dir=self.work) as temp:
            path=Path(temp)/'input.dng'
            tifffile.imwrite(path,raw,photometric=32803,metadata=None,extratags=tags)
            with rawpy.imread(str(path)) as decoded:
                return decoded.postprocess(demosaic_algorithm=algorithm,**PARAMS)

    def render(self,norm,base,cfa,neutral,algorithm):
        n=np.asarray(neutral);assert n.shape==(3,) and n[1]==1 and np.all(n>0)
        red,blue,_=cfa_masks(norm.shape,cfa)
        nc=np.where(red,n[0],np.where(blue,n[2],1.));headroom=max(1.,1/n[0],1/n[2])
        encoded=np.floor(norm.astype(float)/nc/headroom+.5)
        assert encoded.min()>=0 and encoded.max()<=65535
        rgb=self.demosaic(encoded.astype(np.uint16),cfa,algorithm).astype(float)*headroom
        # Transfer only colour differences, restoring camera-channel units.
        cam=np.clip(np.floor((rgb-rgb[...,[1]]+base[...,[1]])*n+.5),0,65535).astype(np.uint16)
        cam[...,1]=base[...,1]
        cam[:10]=base[:10];cam[-10:]=base[-10:];cam[:,:10]=base[:,:10];cam[:,-10:]=base[:,-10:]
        return cam


def local_control(candidate,base,sensor,white):
    if not np.any(sensor>=white):return base.copy()
    distance=distance_transform_cdt(sensor<white,metric='chessboard')
    weight=np.clip((8-distance)/4,0,1)
    return np.floor(base.astype(float)+weight[...,None]*(candidate.astype(float)-base)+.5).astype(np.uint16)


def checks(control):
    rows=[]
    for cfa in range(4):
        red,blue,_=cfa_masks((64,80),cfa)
        for values in ([10000,20000,30000],[50000,2000,45000],[0,65535,0]):
            raw=np.where(red,values[0],np.where(blue,values[2],values[1])).astype(np.uint16)
            for alg in (rawpy.DemosaicAlgorithm.AHD,rawpy.DemosaicAlgorithm.DCB):
                rgb=control.demosaic(raw,cfa,alg)[10:-10,10:-10]
                error=int(np.abs(rgb.astype(int)-values).max());assert error<=1
                rows.append(dict(cfa=cfa,values=values,algorithm=alg.name,max_channel_error=error))
    return dict(flat_linear_camera_rgb_cases=rows,case_count=len(rows))


def synthetic(native,probe,control,neutral,scale):
    yy,xx=np.indices((160,192));n=np.asarray(neutral);rows=[]
    for cfa in range(4):
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
                        candidate=control.render(norm,dcam,cfa,n,rawpy.DemosaicAlgorithm.DCB)
                        local=local_control(candidate,dcam,sensor,1023)
                        clipped=np.clip(scene,0,1);truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed_truth=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,metrics={})
                        for mode,cam in [('D',dcam),('DCB',candidate),('local_DCB',local)]:
                            assert np.array_equal(cam[...,1],base[...,1])
                            z=np.clip(cam.astype(float)/65535*scale/n,0,1)[16:-16,16:-16]
                            row['metrics'][mode]=dict(scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed_truth[...,[0,2]])**2))))
                        rows.append(row)
        print('synthetic CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in ('DCB','local_DCB'):
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),
                max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()),worst_case_index=int(delta.argmax()))
    return dict(schema='m9.demosaic_control.synthetic.v1',case_count=len(rows),summary=summary,cases=rows,
                neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
                oracle='Both previous references retained: known blurred scene after physical clipping, and its colour differences added to fixed native green. No noise, unity shading, float64 synthetic normalization, inner16. Strict comparison tolerance 1e-12. Neither is a Leica hardware/perceptual oracle.')


def comparison(out,rendered):
    sheet=Image.new('RGB',(1224,1452),'#16191c');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((12,12),'Interpolation controls — native green, sharpening, colour and exposure held fixed',font=font,fill='white')
    draw.text((12,43),'No early white cap. Less photographic pink, but fixture regressions remain; research only.',font=small,fill='#ffc986')
    for col,(mode,title) in enumerate([('H','Current DETAIL1H'),('local_DCB','DCB near clipping (control)'),('DCB','DCB across frame (control)')]):
        draw.text((12+408*col,89),title,font=font,fill='white');rot=np.rot90(rendered[mode],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+432*row;draw.text((12+408*col,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(rot[y:y+384,x:x+384]),(12+408*col,top))
    sheet.save(out/'Interpolation-controls.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(a.raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(a.raw);nr,_,nb=meta['neutral'];scale=meta['representation_scale'];cfa=meta['cfa']
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');control=Control(a.out/'temporary')
    flat_checks=checks(control)
    base=native.render(norm,nr,nb,cfa,candidate=False)
    hcam,hstats=TiledDetail(a.out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],fixture['detail1H']['rgbProfile'],gains,scale,guard=True)
    colour=Downstream(repo,a.assembled,a.out/'colour');colour.configure(a.raw)
    rendered={};variants={}
    for mode in ('H','AHD','DCB','local_DCB'):
        if mode=='H':cam=hcam
        elif mode=='local_DCB':cam=local_control(dcb,hcam,sensor,meta['white'])
        else:
            cam=control.render(norm,hcam,cfa,meta['neutral'],getattr(rawpy.DemosaicAlgorithm,mode))
            if mode=='DCB':dcb=cam
        assert np.array_equal(cam[...,1],hcam[...,1])
        border=np.ones(norm.shape,bool);border[10:-10,10:-10]=False
        assert np.array_equal(cam[border],hcam[border])
        rgb=colour.render(colour.restore(cam,scale),fixture['actual_render_gain']);rendered[mode]=rgb
        variants[mode]=dict(pink_pixels=int(pink_mask(rgb).sum()),native_green_exact=True,border10_exact=True)
        if mode=='local_DCB':
            far=distance_transform_cdt(sensor<meta['white'],metric='chessboard')>=8
            assert np.array_equal(cam[far],hcam[far]);variants[mode]['H_exact_at_distance_8_or_more']=True
        Image.fromarray(np.rot90(rgb,3)).save(a.out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,variants[mode],flush=True)
    comparison(a.out,rendered)
    syn=synthetic(native,probe,control,meta['neutral'],scale);cases=syn.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(syn,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    report=dict(schema='m9.demosaic_control.replay.v1',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                raw_sha256=fixture['dng_sha256'],rawpy_version=rawpy.__version__,libraw_version=rawpy.libraw_version,
                libraw_flags=rawpy.flags,linear_flat_checks=flat_checks,variants=variants,H_stats=hstats,
                actual_render_gain=fixture['actual_render_gain'],synthetic_summary=syn['summary'],synthetic_cases=len(cases),
                spatial_source_hashes=native.source_hashes,colour_source_hashes=colour.hashes,
                local_support='All sensor channels: full DCB within Chebyshev distance4 of raw>=white; linear taper to zero at8. H retained outside. This is a heuristic control, not a recovered M9 rule.',
                scope='Independent offline interpolation control. No pre-WB white clipping, exposure change, hue mask or Android implementation. Existing H guard is retained only through the H base; no new DCB variance model.',
                photographic_acceptance_passed=False,android_implementation_changed=False,auto_exposure_changed=False)
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(syn['summary'],indent=2))


if __name__=='__main__':main()
