"""Offline R/B support and post-interpolation-limit controls; no app change."""
from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
import rawpy
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, maximum_filter, uniform_filter, distance_transform_cdt
from native import Native
from rb_domain import DomainProbe
from rb_probe import q14
from demosaic_control import Control, local_control
from fringe_replay import cfa_masks, pink_mask
from censored_chroma_probe import BACKGROUNDS, SUBJECTS
from detail1h import dng_inputs, TiledDetail
from downstream import Downstream

MODES=('DCB','matched','post_limit','limit_then_match','match_then_limit','affine4','affine8')


def green_support(rgb,green):
    """Float equivalent of native green's phase-dependent spatial support.

    This applies the same support to every reconstructed channel. It does not
    reproduce native integer rounding; green is restored exactly at the end.
    Wrapped borders are discarded by the caller's ten-pixel perimeter.
    """
    cardinal=sum(np.roll(rgb,s,axis) for axis in (0,1) for s in (-1,1))/4
    diagonal=sum(np.roll(np.roll(rgb,dy,0),dx,1) for dy in (-1,1) for dx in (-1,1))
    return np.where(green[...,None],(4*rgb+diagonal)/8,cardinal)


def affine_control(rgb,norm,base,sensor,cfa,neutral,scale,white,radius):
    """Exploratory local C=a*G+b fit using uncensored CFA observations.

    Confidence thresholds are declared heuristics, not a statistical guarantee.
    Fit both colours before accepting either; the noise model is not reused.
    """
    red,blue,green=cfa_masks(norm.shape,cfa);n=np.asarray(neutral)
    guide=rgb[...,1]*scale/65535
    bad_green=maximum_filter(green & (sensor>=white),size=3)
    predictions=[];joint=np.ones(norm.shape,bool);size=2*radius+1
    def total(z):return uniform_filter(z.astype(float),size=size,mode='reflect')*size*size
    for channel,mask in [(0,red),(2,blue)]:
        data=norm.astype(float)*scale/65535/n[channel]
        valid=mask & (sensor<white) & (sensor>64) & ~bad_green
        count=total(valid);den=np.maximum(count,1)
        mean_g=total(guide*valid)/den;mean_c=total(data*valid)/den
        variance=np.maximum(total(guide*guide*valid)/den-mean_g**2,0)
        cov=total(guide*data*valid)/den-mean_g*mean_c
        a=cov/(variance+1e-6);b=mean_c-a*mean_g
        residual=np.maximum(total(data*data*valid)/den-mean_c**2-2*a*cov+a*a*variance,0)
        joint &= (count>=8) & (variance>=.02**2) & (residual<=.02**2) & (a>=-4) & (a<=8)
        predictions.append(np.maximum(a*guide+b,0))
    cam=base.copy()
    for channel,predicted in zip((0,2),predictions):
        value=(np.minimum(predicted,1)-np.minimum(guide,1))*65535/scale+base[...,1]
        value=np.clip(np.floor(value*n[channel]+.5),0,65535).astype(np.uint16)
        cam[...,channel]=np.where(joint,value,base[...,channel])
    return cam


def variants(control,norm,base,sensor,cfa,neutral,scale,white=1023,modes=MODES):
    n=np.asarray(neutral);red,blue,green=cfa_masks(norm.shape,cfa)
    nc=np.where(red,n[0],np.where(blue,n[2],1.));headroom=max(1.,1/n[0],1/n[2])
    encoded=np.floor(norm.astype(float)/nc/headroom+.5)
    assert encoded.min()>=0 and encoded.max()<=65535
    rgb=control.demosaic(encoded.astype(np.uint16),cfa,rawpy.DemosaicAlgorithm.DCB).astype(float)*headroom
    cap=65535/scale
    for mode in modes:
        if mode.startswith('affine'):
            cam=affine_control(rgb,norm,base,sensor,cfa,n,scale,white,int(mode[6:]))
        else:
            if mode=='DCB':z=rgb
            elif mode=='matched':z=green_support(rgb,green)
            elif mode=='post_limit':z=np.minimum(rgb,cap)
            elif mode=='limit_then_match':z=green_support(np.minimum(rgb,cap),green)
            else:z=np.minimum(green_support(rgb,green),cap)
            cam=np.clip(np.floor((z-z[...,[1]]+base[...,[1]])*n+.5),0,65535).astype(np.uint16)
        cam[...,1]=base[...,1]
        cam[:10]=base[:10];cam[-10:]=base[-10:];cam[:,:10]=base[:,:10];cam[:,-10:]=base[:,-10:]
        yield mode,local_control(cam,base,sensor,white)


def check_green_support(control,probe):
    # DCB's measured green sites supply every tap used by native green. Check
    # the dependency against the separately compiled C++ producer, all CFAs.
    rng=np.random.default_rng(92273);rows=[]
    for cfa in range(4):
        raw=rng.integers(0,50001,(80,96),dtype=np.uint16)
        _,_,green=cfa_masks(raw.shape,cfa)
        rgb=control.demosaic(raw,cfa,rawpy.DemosaicAlgorithm.DCB)
        inner=np.zeros(raw.shape,bool);inner[12:-12,12:-12]=True
        assert np.array_equal(rgb[...,1][inner&green],raw[inner&green])
        matched=np.floor(green_support(q14(rgb).astype(float),green)[...,1]).astype(np.uint16)
        reference=probe.stages(raw,cfa,1.,1.)[0]
        assert np.array_equal(matched[inner],reference[inner])
        rows.append(dict(cfa=cfa,measured_green_samples_exact=int((inner&green).sum()),
                         native_green_support_samples_exact=int(inner.sum())))
    return rows


def replay(raw,native,control,repo,assembled,out):
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(raw);nr,_,nb=meta['neutral'];cfa=meta['cfa'];scale=meta['representation_scale']
    base=native.render(norm,nr,nb,cfa,candidate=False)
    hcam,hstats=TiledDetail(out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],fixture['detail1H']['rgbProfile'],gains,scale,guard=True)
    fields=dict(tiles='tiles',supported_rb_samples='supportedRbSamples',changed_carrier_samples='changedCarrierSamples',
        max_abs_correction='maxAbsCorrection',censored_samples='rawCensoredSamples',mean_confidence='meanConfidence',
        mean_residual_variance14='meanResidualVariance14',scratch_budget_bytes='scratchBudgetBytes')
    assert all(hstats[k]==fixture['detail1H'][v] for k,v in fields.items())
    colour=Downstream(repo,assembled,out/'colour');colour.configure(raw)
    rendered={};reports={};far=distance_transform_cdt(sensor<meta['white'],metric='chessboard')>=8
    border=np.ones(norm.shape,bool);border[10:-10,10:-10]=False
    def render(mode,cam):
        assert np.array_equal(cam[...,1],hcam[...,1])
        assert np.array_equal(cam[border],hcam[border])
        assert np.array_equal(cam[far],hcam[far])
        rgb=colour.render(colour.restore(cam,scale),fixture['actual_render_gain']);rendered[mode]=rgb
        reports[mode]=dict(pink_pixels=int(pink_mask(rgb).sum()),native_green_exact=True,border10_exact=True,H_exact_beyond_support=True)
        Image.fromarray(np.rot90(rgb,3)).save(out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,reports[mode],flush=True)
    render('H',hcam)
    for mode,cam in variants(control,norm,hcam,sensor,cfa,meta['neutral'],scale,meta['white'],modes=('DCB','matched')):
        render(mode,cam)
    sheet=Image.new('RGB',(1224,1452),'#16191c');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((12,12),'Matching R/B support to native green — same RAW, exposure and downstream colour',font=font,fill='white')
    draw.text((12,43),'Both controls retain colour regressions. Research comparison; no accepted fix or new APK.',font=small,fill='#ffc986')
    for col,(mode,title) in enumerate([('H','Current DETAIL1H'),('DCB','Previous local DCB control'),('matched','Matched green support')]):
        draw.text((12+408*col,89),title,font=font,fill='white');rot=np.rot90(rendered[mode],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+432*row;draw.text((12+408*col,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(rot[y:y+384,x:x+384]),(12+408*col,top))
    sheet.save(out/'Green-support-comparison.png')
    return dict(variants=reports,raw_sha256=fixture['dng_sha256'],H_stats=hstats,H_phone_statistics_exact=len(fields),
                actual_render_gain=fixture['actual_render_gain'],colour_source_hashes=colour.hashes,
                accepted=False,android_implementation_changed=False,auto_exposure_changed=False)


def synthetic(native,probe,control,neutral,scale,cfas):
    yy,xx=np.indices((160,192));n=np.asarray(neutral);rows=[]
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
                        for mode,cam in [('D',dcam),*variants(control,norm,dcam,sensor,cfa,n,scale)]:
                            assert np.array_equal(cam[...,1],base[...,1])
                            z=np.clip(cam.astype(float)/65535*scale/n,0,1)[16:-16,16:-16]
                            row['metrics'][mode]=dict(scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in MODES:
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),
                max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()),worst_case_index=int(delta.argmax()))
    return dict(schema='m9.green_support_probe.v1',case_count=len(rows),summary=summary,cases=rows,
                neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
                support='Every control uses the existing clipping-distance4..8 local blend. D outside; exact native green, border10.',
                oracle='Both previous references retained; no noise, unity shading, float64 synthetic normalization, inner16. Strict tolerance1e-12. Not a Leica/perceptual oracle.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    ap.add_argument('--raw',type=Path,help='Optional exact failure RAW replay of H, local DCB and matched support.')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');control=Control(a.out/'temporary')
    checks=check_green_support(control,probe)
    photo=replay(a.raw,native,control,repo,a.assembled,a.out) if a.raw else None
    result=synthetic(native,probe,control,[.41796875,1.,.6435546875],1.6105431518598052,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['rawpy_version']=rawpy.__version__;result['libraw_version']=rawpy.libraw_version
    result['spatial_source_hashes']=native.source_hashes
    result['green_support_checks']=checks
    result['photograph']=photo
    result['accepted']=False
    cases=result.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
