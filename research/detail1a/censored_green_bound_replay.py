"""Same-RAW replay of the measured-green bound; partial correction only."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np,rawpy
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import distance_transform_cdt
from native import Native
from detail1h import dng_inputs,TiledDetail
from downstream import Downstream
from demosaic_control import Control,local_control
from censored_green_bound import project
from fringe_replay import pink_mask,cfa_masks


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(a.raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(a.raw);nr,_,nb=meta['neutral'];cfa=meta['cfa'];scale=meta['representation_scale']
    native=Native(repo,a.assembled,a.header,a.out/'native');control=Control(a.out/'temporary')
    base=native.render(norm,nr,nb,cfa,candidate=False)
    profile=fixture['detail1H']['rgbProfile']
    hcam,hstats=TiledDetail(a.out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],profile,gains,scale,guard=True)
    fields=dict(tiles='tiles',supported_rb_samples='supportedRbSamples',changed_carrier_samples='changedCarrierSamples',
        max_abs_correction='maxAbsCorrection',censored_samples='rawCensoredSamples',mean_confidence='meanConfidence',
        mean_residual_variance14='meanResidualVariance14',scratch_budget_bytes='scratchBudgetBytes')
    assert all(hstats[k]==fixture['detail1H'][v] for k,v in fields.items())
    colour=Downstream(repo,a.assembled,a.out/'colour');colour.configure(a.raw)
    red,blue,green=cfa_masks(norm.shape,cfa);reports={};photos={}
    clip_distance=distance_transform_cdt(sensor<meta['white'],metric='chessboard')
    for mode in ('H','H_bound','DCB','DCB_bound'):
        if mode=='H':cam=hcam
        elif mode=='H_bound':
            cam,stats,_,selected=project(norm,sensor,hcam,cfa,meta['neutral'],scale,meta['black'],meta['white'],profile[2:4])
        elif mode=='DCB':
            cam=local_control(control.render(norm,hcam,cfa,meta['neutral'],rawpy.DemosaicAlgorithm.DCB),hcam,sensor,meta['white']);dcam=cam
        else:cam,stats,_,selected=project(norm,sensor,dcam,cfa,meta['neutral'],scale,meta['black'],meta['white'],profile[2:4])
        assert np.array_equal(cam[...,1],hcam[...,1])
        rgb=colour.render(colour.restore(cam,scale),fixture['actual_render_gain']);photos[mode]=rgb
        pm=pink_mask(rgb)
        reports[mode]=dict(pink_pixels=int(pm.sum()),pink_at_green_cfa=int((pm&green).sum()),
                           pink_at_censored_green=int((pm&green&(sensor>=meta['white'])).sum()),native_green_exact=True)
        reports[mode]['pink_by_cfa_and_raw_clip_distance']={name:[int((pm&phase&(np.minimum(clip_distance,9)==d)).sum()) for d in range(10)] for name,phase in [('R',red),('G',green),('B',blue)]}
        if mode.endswith('_bound'):
            reference=mode.removesuffix('_bound');delta=rgb.astype(np.int16)-photos[reference].astype(np.int16)
            reports[mode].update(projection=stats,final_rgb_changed_pixels=int(np.any(delta!=0,axis=-1).sum()),
                final_rgb_maximum_channel_change=int(np.abs(delta).max()),final_rgb_exact=bool(np.all(delta==0)))
        Image.fromarray(np.rot90(rgb,3)).save(a.out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,reports[mode],flush=True)
    sheet=Image.new('RGB',(1632,1452),'#16191c');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((12,12),'Measured-green colour bound — exact native green and sharpening, same exposure and colour',font=font,fill='white')
    draw.text((12,43),'Measured clipped-green sites only; six-sigma model margin. No reduction in pink edging; not an accepted fix.',font=small,fill='#ffc986')
    for col,(mode,title) in enumerate([('H','Current DETAIL1H'),('H_bound','H + measured-green bound'),('DCB','Previous local DCB control'),('DCB_bound','DCB + measured-green bound')]):
        draw.text((12+408*col,89),title,font=font,fill='white');rot=np.rot90(photos[mode],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+432*row;draw.text((12+408*col,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(rot[y:y+384,x:x+384]),(12+408*col,top))
    sheet.save(a.out/'Measured-green-bound-comparison.png')
    result=dict(schema='m9.censored_green_bound.replay.v1',raw_sha256=fixture['dng_sha256'],H_stats=hstats,
        H_phone_statistics_exact=len(fields),actual_render_gain=fixture['actual_render_gain'],variants=reports,
        spatial_source_hashes=native.source_hashes,colour_source_hashes=colour.hashes,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        bound_script_sha256=hashlib.sha256(Path(__file__).with_name('censored_green_bound.py').read_bytes()).hexdigest(),
        scope='Partial offline colour-difference constraint at directly measured censored green CFA sites. Noise allowance is model-dependent, calibration remains open. DCB still has its previous interpolation regressions.',
        android_implementation_changed=False,auto_exposure_changed=False,complete_fringe_fix=False)
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
