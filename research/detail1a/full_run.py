#!/usr/bin/env python3
"""Run DETAIL1B full-colour same-RAW probes after the DETAIL1A Sharp study."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import subprocess
import numpy as np
import cv2
import tifffile
from scipy.ndimage import gaussian_filter,sobel
from PIL import Image,ImageDraw,ImageFont,features
from native import Native,ISOS
from inputs import read
from run import slot_for,choose_tiles
from downstream import Downstream


def metrics(rgb):
    z=rgb.astype(float)/255.;y=z@np.array([.2126,.7152,.0722])
    hf=y-gaussian_filter(y,1.)
    grad=np.hypot(sobel(y,axis=0)/8,sobel(y,axis=1)/8)
    return dict(luma_mean=float(y.mean()),luma_hf_rms=float(np.sqrt(np.mean(hf**2))),
                luma_gradient_p95=float(np.percentile(grad,95)),rgb_mean=z.mean(axis=(0,1)).tolist(),
                rgb_zero_pct=float(np.mean(rgb==0)*100),rgb_white_pct=float(np.mean(rgb==255)*100))


def orient(im,orientation,inverse=False):
    if orientation==1:return im
    if orientation==6:return im.transpose(Image.Transpose.ROTATE_90 if inverse else Image.Transpose.ROTATE_270)
    if orientation==8:return im.transpose(Image.Transpose.ROTATE_270 if inverse else Image.Transpose.ROTATE_90)
    if orientation==3:return im.transpose(Image.Transpose.ROTATE_180)
    raise ValueError(('unsupported DNG orientation',orientation))


def comparison(meta,decoded):
    """Decoded JPEG crops at 100%, without resizing or exposure lifting."""
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(font_path,18);small=ImageFont.truetype(font_path,15)
    panel=Image.new('RGB',(1200,944),'#14191d');draw=ImageDraw.Draw(panel)
    model='17 Ultra' if '25128' in meta['model'] else '15 Ultra'
    draw.text((16,12),f'M9 DETAIL1B | {model} | sensor ISO {meta["iso"]} | same RAW, final JPEG crops',font=font,fill='white')
    for col,(variant,label) in enumerate(zip(meta['variants'],['Current fixed ISO160','1x ISO probe','2x ISO probe'])):
        left=col*400+8;draw.text((left,46),label+f' / Leica {variant["leica_iso"]}',font=small,fill='#dedfe0')
        for ti,tile in enumerate(meta['tiles']):
            x,y=tile['xy'];top=102+ti*420
            draw.text((left,top-26),f'{tile["kind"]}: x={x}, y={y}',font=small,fill='#bdc8cd')
            panel.paste(Image.fromarray(decoded[col][y:y+384,x:x+384]),(left,top))
    draw.text((12,922),'Offline neutral intent; 100% crops; identical JPEG95 encoder. Probes, not approved settings.',font=small,fill='#bdc8cd')
    return panel


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--firmware',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    header=out/'native/m9_sharp_fulliso_bank.h'
    subprocess.run([sys.executable,str(repo/'tools/m9_sharpness_export_fulliso_header.py'),str(a.firmware),'--out',str(header)],check=True,capture_output=True)
    native=Native(repo,a.assembled.resolve(),header,out/'native')
    colour=Downstream(repo,a.assembled.resolve(),out/'native_colour')
    report=dict(schema='m9.detail1b.fullcolour.offline.v1',source_hashes=colour.hashes,
        scope='NORM030 reconstruction, native detail, representation restore, native source colour, TC20, tone bound, SAT2/curve02, TG1 and horizontal BT.601 4:2:2; host JPEG95',
        boundaries=['DNG metadata replay does not establish Camera2/HAL parity',
                    'Neutral exposure intent (no capture-time GL2G exposure plan), edge-placement EV=0',
                    'Host OpenCV and floating-point implementation are not bit-verified against Android',
                    'Pillow/libjpeg95 with 4:2:0 sampling is a controlled shared encoder, not Android Bitmap.compress parity',
                    'High-frequency RMS includes texture and noise; no Noise2 implementation or validated sensor ISO mapping'],
        opencv_version=cv2.__version__,jpeg_version=features.version_codec('jpg'),
        jpeg_quality=95,jpeg_subsampling='4:2:0',checks={},captures=[])
    checked_cfas=set()
    for path in a.dngs:
        raw,meta=read(path);h,w=raw.shape
        meta['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        meta['context']=colour.configure(path);tail=colour.tail(path);meta['raw_tail']=tail
        with tifffile.TiffFile(path) as tf:orientation=int(tf.pages[0].tags['Orientation'].value)
        meta['orientation']=orientation
        nr=meta['neutral'][0]/meta['neutral'][1];nb=meta['neutral'][2]/meta['neutral'][1]
        slots=[0,slot_for(meta['iso']),slot_for(meta['iso']*2)]
        names=['baseline','iso_1x_probe','iso_2x_probe'];results=[];tiles=choose_tiles(raw,384)
        meta['variants']=[];decoded=[];fixed_crop_metrics=[]
        baseline_gain=None
        for name,slot in zip(names,slots):
            cam=native.render(raw,nr,nb,meta['cfa'],slot=slot,candidate=name!='baseline')
            cam=colour.restore(cam,meta['representation_scale'])
            meter=colour.meter(cam,tail);gain=meter['render_gain']
            rgb=colour.render(cam,gain)
            if name=='baseline':
                baseline_gain=gain
                if meta['cfa'] not in checked_cfas:
                    q=native.render(raw,nr,nb,meta['cfa'],slot=0)
                    q=colour.restore(q,meta['representation_scale'])
                    assert np.array_equal(cam,q),'full RGB16 baseline/slot0 parity'
                    qm=colour.meter(q,tail);assert meter==qm,'meter parity'
                    qr=colour.render(q,qm['render_gain']);assert np.array_equal(rgb,qr),'full RGB8 parity'
                    key='full_'+str(meta['cfa'])+'_cfa_slot0'
                    report['checks'][key]=dict(rgb16_samples=int(q.size),rgb8_samples=int(qr.size),meter_equal=True)
                    rng=np.random.default_rng(91222)
                    for shape in [(31,33,3),(32,38,3)]:
                        z=rng.integers(0,65536,shape,dtype=np.uint16)
                        assert np.array_equal(colour.render(z,gain,workers=1),colour.render(z,gain,workers=8))
                    report['checks']['serial_parallel_colour_including_odd_width']=True
                    checked_cfas.add(meta['cfa']);del q,qr
            fixed=rgb if gain==baseline_gain else colour.render(cam,baseline_gain)
            fixed_crop_metrics.append([metrics(fixed[y:y+384,x:x+384]) for _,y,x in tiles])
            variant=dict(name=name,slot=slot,leica_iso=int(ISOS[slot]),meter=meter,
                         gain_delta_ev=float(np.log2(gain/baseline_gain)),pre_encode=metrics(rgb))
            jpg=out/(path.stem+'_'+name+'.jpg')
            orient(Image.fromarray(rgb),orientation).save(jpg,quality=95,subsampling=2,optimize=False)
            with Image.open(jpg) as im:decoded.append(np.array(orient(im.convert('RGB'),orientation,inverse=True)))
            variant['jpeg']=jpg.name;variant['jpeg_sha256']=hashlib.sha256(jpg.read_bytes()).hexdigest()
            variant['jpeg_bytes']=jpg.stat().st_size;variant['decoded_jpeg']=metrics(decoded[-1])
            if name!='baseline' and slot<=2:
                assert np.array_equal(rgb,results[0]),'low-ISO RGB8 identity'
                assert variant['jpeg_sha256']==meta['variants'][0]['jpeg_sha256'],'low-ISO JPEG identity'
            meta['variants'].append(variant);results.append(rgb)
            del cam,fixed
        meta['tiles']=[]
        for ti,(kind,y,x) in enumerate(tiles):
            row=dict(kind=kind,xy=[x,y],size=384,variants=[])
            for k,rgb in enumerate(results):
                crop=rgb[y:y+384,x:x+384];base=results[0][y:y+384,x:x+384]
                row['variants'].append(dict(name=names[k],pre_encode=metrics(crop),
                    baseline_gain_pre_encode=fixed_crop_metrics[k][ti],
                    decoded_jpeg=metrics(decoded[k][y:y+384,x:x+384]),
                    mean_abs_rgb8_delta=float(np.abs(crop.astype(int)-base.astype(int)).mean())))
            meta['tiles'].append(row)
        png=out/(path.stem+'_comparison.png');comparison(meta,decoded).save(png)
        with Image.open(png) as im:im.verify()
        meta['comparison']=png.name
        thumb=Image.fromarray(decoded[0]);thumb=orient(thumb,orientation);thumb.thumbnail((960,960))
        thumb.save(out/(path.stem+'_overview.jpg'),quality=90)
        report['captures'].append(meta)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(name=path.name,iso=meta['iso'],slots=slots,
              bounded_ev=[v['meter']['bounded_ev'] for v in meta['variants']],
              jpeg_bytes=[v['jpeg_bytes'] for v in meta['variants']])),flush=True)
        del raw,results,decoded
    print('Complete: '+str(out/'report.json'),flush=True)


if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode() if isinstance(e.stderr,bytes) else e.stderr,file=sys.stderr);raise
