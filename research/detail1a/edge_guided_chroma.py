"""Falsification probe for green-guided, measured-phase R/B interpolation.

Two fixed controls share radius6, spatial sigma3 and green-range sigma0.08 in
physical WB-normalized units. One includes every R/B anchor; the other excludes
sensor-clipped R/B anchors and anchors touching a clipped measured green sample.
Co2 differences, native green and ISO160 Sharp are retained. No colour mask is
used. No parameter fitting, early white cap or complete Leica parity claim.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter,distance_transform_cdt
from PIL import Image,ImageDraw,ImageFont
from native import Native
from rb_domain import DomainProbe
from rb_probe import q14,q16
from fringe_replay import cfa_masks,pink_mask
from censored_chroma_probe import BACKGROUNDS,SUBJECTS
from demosaic_control import local_control
from detail1h import dng_inputs,TiledDetail
from downstream import Downstream

MODES=('guided_all','guided_uncensored')

class Guided:
    def __init__(self,build):
        build.mkdir(parents=True,exist_ok=True);so=build/'edge_guided_chroma.so'
        subprocess.run(['g++','-O3','-std=c++17','-fPIC','-fopenmp','-shared',str(Path(__file__).with_suffix('.cpp')),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()));self.fn=self.lib.edge_guided_chroma
        self.fn.argtypes=[C.c_void_p]*5+[C.c_int]*3+[C.c_double]*3+[C.c_void_p];self.fn.restype=None

    def render(self,green,diff,valid,support,base,cfa,neutral,scale):
        arrays=[np.ascontiguousarray(x,dtype=t) for x,t in zip((green,diff,valid,support,base),(np.uint16,np.int32,np.uint8,np.uint8,np.uint16))]
        h,w=green.shape;out=arrays[-1].copy()
        self.fn(*[z.ctypes.data for z in arrays],w,h,cfa,neutral[0],neutral[2],scale,out.ctypes.data)
        return out

    def variants(self,probe,norm,sensor,base,cfa,neutral,scale,white=1023):
        green,diff,_,_=probe.stages(norm,cfa,neutral[0],neutral[2],shrink=True)
        red,blue,g=cfa_masks(norm.shape,cfa)
        distance=distance_transform_cdt(sensor<white,metric='chessboard')
        support=(distance>=0)&(distance<8)
        # The native green estimate at an R/B anchor uses four cardinal green
        # measurements. The cross excludes diagonally located R/B samples.
        cross=np.array([[0,1,0],[1,1,1],[0,1,0]],bool)
        touched=maximum_filter(g&(sensor>=white),footprint=cross)
        for mode in MODES:
            valid=red|blue
            if mode=='guided_uncensored':valid &= (sensor<white)&~touched
            candidate=self.render(green,diff,valid,support,base,cfa,neutral,scale)
            cam=local_control(candidate,base,sensor,white)
            assert np.array_equal(cam[...,1],base[...,1])
            assert np.array_equal(cam[~support],base[~support])
            yield mode,cam


def scalar_checks(guided):
    rng=np.random.default_rng(92319);rows=[]
    for cfa in range(4):
        shape=(40,44);red,blue,_=cfa_masks(shape,cfa)
        green=rng.integers(0,16384,shape,dtype=np.uint16)
        diff=rng.integers(-16000,40000,shape,dtype=np.int32)
        base=rng.integers(0,65536,(*shape,3),dtype=np.uint16)
        support=rng.random(shape)>.2;valid=(red|blue)&(rng.random(shape)>.35)
        n=[.41796875,1.,.6435546875];scale=1.6105431518598052
        actual=guided.render(green,diff,valid,support,base,cfa,n,scale)
        expected=base.copy();count=0
        for y in range(10,shape[0]-10):
            for x in range(10,shape[1]-10):
                if not support[y,x]:continue
                sg=int(q14(base[y,x,1]));gs=int(green[y,x])
                for channel,phase in [(0,red),(2,blue)]:
                    total=0.;value=0.
                    for yy in range(y-6,y+7):
                        for xx in range(x-6,x+7):
                            if not phase[yy,xx] or not valid[yy,xx]:continue
                            delta=(gs-int(green[yy,xx]))*scale/16383/.08
                            weight=np.exp(-((yy-y)**2+(xx-x)**2)/18)*np.exp(-.5*delta**2)
                            total+=weight;value+=weight*int(diff[yy,xx])
                    if total>1e-12:
                        v=n[channel]*(sg+value/total)
                        expected[y,x,channel]=q16(np.clip(np.floor(v+.5),0,16383).astype(np.int64))
                        count+=1
        assert np.array_equal(actual,expected)
        rows.append(dict(cfa=cfa,scalar_channel_samples=count,complete_array_exact=True))
    return rows


def synthetic(native,probe,guided,cfas):
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
                        for mode,cam in [('D',dcam),*guided.variants(probe,norm,sensor,dcam,cfa,n,scale)]:
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
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),max_rms_increase=float(delta.max()),
                mean_rms_change=float(delta.mean()),worst_case_index=int(delta.argmax()))
    return dict(case_count=len(rows),cases=rows,summary=summary,neutral=n.tolist(),representation_scale=scale,
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,oracle='Both existing scene RGB and fixed-green R/B references retained, inner16, tolerance1e-12. Noiseless, unity shading. Not a Leica/perceptual oracle.')


def replay(raw,native,probe,guided,repo,assembled,out):
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(raw);nr,_,nb=meta['neutral'];cfa=meta['cfa'];scale=meta['representation_scale']
    base=native.render(norm,nr,nb,cfa,candidate=False)
    hcam,hstats=TiledDetail(out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],fixture['detail1H']['rgbProfile'],gains,scale,guard=True)
    fields=dict(tiles='tiles',supported_rb_samples='supportedRbSamples',changed_carrier_samples='changedCarrierSamples',
        max_abs_correction='maxAbsCorrection',censored_samples='rawCensoredSamples',mean_confidence='meanConfidence',
        mean_residual_variance14='meanResidualVariance14',scratch_budget_bytes='scratchBudgetBytes')
    assert all(hstats[k]==fixture['detail1H'][v] for k,v in fields.items())
    colour=Downstream(repo,assembled,out/'colour');colour.configure(raw);photos={};reports={}
    def variants():
        yield 'H',hcam
        yield from guided.variants(probe,norm,sensor,hcam,cfa,meta['neutral'],scale,meta['white'])
    for mode,cam in variants():
        rgb=colour.render(colour.restore(cam,scale),fixture['actual_render_gain']);photos[mode]=rgb
        reports[mode]=dict(pink_pixels=int(pink_mask(rgb).sum()),native_green_exact=bool(np.array_equal(cam[...,1],hcam[...,1])),
            camera_changed_pixels=int(np.any(cam!=hcam,axis=-1).sum()))
        Image.fromarray(np.rot90(rgb,3)).save(out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,reports[mode],flush=True)
    sheet=Image.new('RGB',(1224,1452),'#16191c');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((12,12),'Green-guided red/blue interpolation — exact native green, same exposure and colour',font=font,fill='white')
    draw.text((12,43),'Much less pink here, but genuine-colour fixture regressions remain. Research only; not an accepted fix.',font=small,fill='#ffc986')
    for col,(mode,title) in enumerate([('H','Current DETAIL1H'),('guided_all','Guided: all colour anchors'),('guided_uncensored','Guided: uncensored anchors')]):
        draw.text((12+408*col,89),title,font=font,fill='white');rot=np.rot90(photos[mode],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+432*row;draw.text((12+408*col,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(rot[y:y+384,x:x+384]),(12+408*col,top))
    sheet.save(out/'Edge-guided-interpolation-comparison.png')
    return dict(variants=reports,raw_sha256=fixture['dng_sha256'],H_stats=hstats,H_phone_statistics_exact=len(fields),
        actual_render_gain=fixture['actual_render_gain'],colour_source_hashes=colour.hashes)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    ap.add_argument('--raw',type=Path);ap.add_argument('--photo-only',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    if a.photo_only and not a.raw:ap.error('--photo-only requires --raw')
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');guided=Guided(a.out/'native')
    result=dict(schema='m9.edge_guided_chroma.v1',checks=scalar_checks(guided),radius=6,spatial_sigma=3,range_sigma=.08,
        support='Same clipping distance4..8 local blend, border10, green exact, Co2 differences retained; no pink mask in processing.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        cpp_sha256=hashlib.sha256(Path(__file__).with_suffix('.cpp').read_bytes()).hexdigest(),
        spatial_source_hashes=native.source_hashes,android_implementation_changed=False,auto_exposure_changed=False,accepted=False)
    if not a.photo_only:result['synthetic']=synthetic(native,probe,guided,a.cfas)
    if a.raw:result['photograph']=replay(a.raw,native,probe,guided,repo,a.assembled,a.out)
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    if 'synthetic' in result:print(json.dumps(result['synthetic']['summary'],indent=2))


if __name__=='__main__':main()
