#!/usr/bin/env python3
"""DETAIL1D: repair the camera-neutral difference domain with fixed green/Sharp."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
from native import Native
from downstream import Downstream
from inputs import read
from run import choose_tiles
from full_run import metrics,orient
from rb_probe import RbProbe,q14
from rb_domain import DomainProbe,checks

NAMES=['baseline','failed_camera_domain','neutral_no_shrink','neutral_co2']
LABELS=['Current MHC differences','Failed R/B probe','Corrected domain + Co=2']

def crop_metrics(rgb):
    m=metrics(rgb);z=rgb.astype(float)/255.;c=z[:,:,[0,2]]-z[:,:,[1]]
    hf=c-gaussian_filter(c,(1,1,0))
    m.update(chroma_hf_rms=float(np.sqrt(np.mean(hf**2))),chroma_rms=float(np.sqrt(np.mean(c**2))))
    return m

def comparison(meta,decoded):
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';title=ImageFont.truetype(font,18);small=ImageFont.truetype(font,15)
    panel=Image.new('RGB',(1200,944),'#14191d');d=ImageDraw.Draw(panel)
    model='17 Ultra' if '25128' in meta['model'] else '15 Ultra'
    d.text((12,12),f'M9 DETAIL1D | {model} | ISO {meta["iso"]} | fixed ISO160 Sharp | decoded JPEG, 100%',font=title,fill='white')
    for k,label in enumerate(LABELS):
        left=k*400+8;d.text((left,46),label,font=small,fill='#dedfe0')
        for ti,tile in enumerate(meta['tiles']):
            x,y=tile['xy'];top=102+ti*420
            d.text((left,top-26),f'{tile["kind"]}: x={x}, y={y}',font=small,fill='#bdc8cd')
            panel.paste(Image.fromarray(decoded[[0,1,3][k]][y:y+384,x:x+384]),(left,top))
    d.text((12,920),'Domain correction only; Noise2 remains bypassed. Same green, colour transform and JPEG95 encoder.',font=small,fill='#bdc8cd')
    return panel

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--reference-report',type=Path,required=True);ap.add_argument('--synthetic-report',type=Path,required=True);
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    native=Native(repo,a.assembled.resolve(),a.header.resolve(),out/'native')
    colour=Downstream(repo,a.assembled.resolve(),out/'native_colour');old=RbProbe(out/'native');probe=DomainProbe(out/'native')
    reference=json.loads(a.reference_report.read_text());refs={c['name']:c for c in reference['captures']}
    synthetic=json.loads(a.synthetic_report.read_text())
    report=dict(schema='m9.detail1d.rb.domain.v1',source_hashes=colour.hashes,checks=checks(probe,old),synthetic_neutral_edges=synthetic,captures=[],
        scope='Camera-neutral differences and restoration to camera RGB around recovered carrier/consumer; fixed GL2G green and Sharp',
        boundaries=['Noise2 is bypassed, not implemented; not full Leica reconstruction parity',
            'Firmware arithmetic interpreted from disassembly; no Blackfin hardware comparison',
            'Mobile adaptation uses wider signed differences for WB headroom; exact Leica WB scaling/rounding not claimed',
            'Outer ten pixels retained from baseline, corresponding to Sharp support9 plus consumer increment1',
            'Same host colour replay and neutral exposure intent limitations as DETAIL1B',
            'HF metrics contain both detail and noise and cannot establish false-colour accuracy without a reference'],
        jpeg_quality=95,jpeg_subsampling='4:2:0',sharp_slot=0,sharp_mode=4,sharp_multiplier=2)
    for path in a.dngs:
        raw,meta=read(path);h,w=raw.shape;meta['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        meta['context']=colour.configure(path);tail=colour.tail(path);meta['raw_tail']=tail
        with tifffile.TiffFile(path) as tf:orientation=int(tf.pages[0].tags['Orientation'].value)
        meta['orientation']=orientation;cfa=meta['cfa'];nr=meta['neutral'][0]/meta['neutral'][1];nb=meta['neutral'][2]/meta['neutral'][1]
        base=native.render(raw,nr,nb,cfa,candidate=False)
        stages=old.stages(raw,cfa,False)
        sharp=native.sharp(stages[0],0,candidate=False)
        assert np.array_equal(sharp[10:-10,10:-10],q14(base[10:-10,10:-10,1])),'green source/Sharp equivalence'
        meta['green_source_sharp_equal_samples']=int(sharp[10:-10,10:-10].size);del sharp
        meta['variants']=[];decoded=[];rgb_crops=[];tiles=choose_tiles(raw,384);baseline_gain=None
        native_mask=np.zeros((h,w),bool);native_mask[2:-2,2:-2]=True
        yy,xx=np.ogrid[:h,:w];native_mask &= (yy%2==xx%2) if cfa in [0,3] else (yy%2!=xx%2)
        unshrunk_diff=None;border=np.ones((h,w),bool);border[10:-10,10:-10]=False
        for k,name in enumerate(NAMES):
            if k==0:cam=base
            elif k==1:
                stages=old.stages(raw,cfa,True);cam=old.consume(stages[2],base,cfa)
            else:
                stages=probe.stages(raw,cfa,nr,nb,k==3);cam=probe.consume(stages[2],base,cfa,nr,nb)
                if k==2:unshrunk_diff=stages[1][native_mask].copy()
            assert np.array_equal(cam[:,:,1],base[:,:,1]),'green unchanged'
            assert np.array_equal(cam[border],base[border]),'border10 unchanged'
            detail=dict(green_equal_samples=h*w,border_equal_rgb_samples=int(border.sum()*3))
            if k==3:
                ds=stages[1][native_mask];detail.update(native_difference_shrunk_pct=float(np.mean(ds!=unshrunk_diff)*100),
                    mean_abs_native_difference_before=float(np.abs(unshrunk_diff.astype(int)).mean()),
                    mean_abs_native_difference_after=float(np.abs(ds.astype(int)).mean()))
            # 14-bit clipping before colour; green remains identical even if final RGB8 green changes via the matrix.
            detail['red_blue_zero_pct']=float(np.mean(cam[10:-10,10:-10][:,:,[0,2]]==0)*100)
            restored=colour.restore(cam,meta['representation_scale']);meter=colour.meter(restored,tail);gain=meter['render_gain']
            if baseline_gain is None:baseline_gain=gain
            rgb=colour.render(restored,gain)
            fixed=rgb if gain==baseline_gain else colour.render(restored,baseline_gain)
            crops=[rgb[y:y+384,x:x+384].copy() for _,y,x in tiles];rgb_crops.append(crops)
            variant=dict(name=name,meter=meter,gain_delta_ev=float(np.log2(gain/baseline_gain)),native=detail,
                baseline_gain_crop_metrics=[crop_metrics(fixed[y:y+384,x:x+384]) for _,y,x in tiles],
                pre_encode=metrics(rgb))
            jpg=out/(path.stem+'_'+name+'.jpg');orient(Image.fromarray(rgb),orientation).save(jpg,quality=95,subsampling=2,optimize=False)
            with Image.open(jpg) as im:decoded.append(np.array(orient(im.convert('RGB'),orientation,inverse=True)))
            variant.update(jpeg=jpg.name,jpeg_bytes=jpg.stat().st_size,jpeg_sha256=hashlib.sha256(jpg.read_bytes()).hexdigest())
            if k in [0,1]:
                ref=refs[meta['name']];assert ref['sha256']==meta['sha256']
                assert variant['jpeg_sha256']==ref['variants'][0 if k==0 else 2]['jpeg_sha256'],'reference JPEG parity'
            meta['variants'].append(variant);del restored,rgb,fixed,cam
        meta['tiles']=[]
        for ti,(kind,y,x) in enumerate(tiles):
            row=dict(kind=kind,xy=[x,y],size=384,variants=[])
            for k,name in enumerate(NAMES):
                row['variants'].append(dict(name=name,pre_encode=crop_metrics(rgb_crops[k][ti]),
                    decoded_jpeg=crop_metrics(decoded[k][y:y+384,x:x+384]),
                    mean_abs_rgb8_delta=float(np.abs(rgb_crops[k][ti].astype(int)-rgb_crops[0][ti].astype(int)).mean())))
            meta['tiles'].append(row)
        png=out/(path.stem+'_comparison.png');comparison(meta,decoded).save(png);meta['comparison']=png.name
        thumb=orient(Image.fromarray(decoded[0]),orientation);thumb.thumbnail((960,960));thumb.save(out/(path.stem+'_overview.jpg'),quality=90)
        report['captures'].append(meta);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(iso=meta['iso'],name=path.name,gain_delta_ev=[v['gain_delta_ev'] for v in meta['variants']],
            shrink_pct=meta['variants'][3]['native']['native_difference_shrunk_pct'])),flush=True)
        del raw,base,stages,decoded,rgb_crops
    print('Complete: '+str(out/'report.json'),flush=True)

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode() if isinstance(e.stderr,bytes) else e.stderr,file=sys.stderr);raise
