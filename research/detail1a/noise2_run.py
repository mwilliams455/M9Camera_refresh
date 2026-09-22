#!/usr/bin/env python3
"""DETAIL1E: Noise2 against the corrected domain, with native green/Sharp fixed."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
import numpy as np
import tifffile
from PIL import Image,ImageDraw,ImageFont
from native import Native,ISOS
from downstream import Downstream
from inputs import read
from run import choose_tiles,slot_for
from full_run import metrics,orient
from rb_probe import q14
from rb_domain import DomainProbe
from rb_domain_run import crop_metrics
from noise2 import Noise2,parameters

NAMES=['baseline','corrected_co2','noise160','noise_iso']

def comparison(meta,decoded):
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';title=ImageFont.truetype(font,18);small=ImageFont.truetype(font,15)
    panel=Image.new('RGB',(1200,944),'#14191d');d=ImageDraw.Draw(panel)
    model='17 Ultra' if '25128' in meta['model'] else '15 Ultra';iso=meta['variants'][3]['leica_noise_iso']
    d.text((12,12),f'M9 DETAIL1E | {model} | sensor ISO {meta["iso"]} | fixed green + ISO160 Sharp | JPEG 100%',font=title,fill='white')
    labels=['Corrected R/B, Noise2 off','Fixed ISO160 (research probe)',f'Indexed ISO{iso} (not approved)']
    for k,label in enumerate(labels):
        left=k*400+8;d.text((left,46),label,font=small,fill='#dedfe0')
        for ti,tile in enumerate(meta['tiles']):
            x,y=tile['xy'];top=102+ti*420
            d.text((left,top-26),f'{tile["kind"]}: x={x}, y={y}',font=small,fill='#bdc8cd')
            panel.paste(Image.fromarray(decoded[k+1][y:y+384,x:x+384]),(left,top))
    d.text((12,920),'Indexed setting not approved: colour-detail loss and ISO573 edge regression. Green/Sharp stay fixed.',font=small,fill='#bdc8cd')
    return panel

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--reference-report',type=Path,required=True);ap.add_argument('--checks',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    native=Native(repo,a.assembled.resolve(),a.header.resolve(),out/'native');colour=Downstream(repo,a.assembled.resolve(),out/'native_colour')
    domain=DomainProbe(out/'native');noise=Noise2(out/'native')
    refs={c['name']:c for c in json.loads(a.reference_report.read_text())['captures']}
    report=dict(schema='m9.detail1e.noise2.v1',source_hashes=colour.hashes,checks=json.loads(a.checks.read_text()),captures=[],
        scope='Luma-disabled Noise2 modes1..3 in corrected wider difference domain. Native green and fixed ISO160 Sharp unchanged.',
        boundaries=['Offline probe only; no application or APK change; no Android/Blackfin hardware parity',
            'Nearest sensor ISO to Leica ISO is a comparison probe, not sensor noise calibration',
            'WB-normalized int32 carrier and 1/AsShotNeutral WB gains retain mobile headroom; no firmware signed16 wrap',
            'Mode2 uses nearest-even MAC extraction; biased-rounding sensitivity is measured because ASTAT state is unresolved',
            'Only modes1..3 and luma-disabled slots0..10 are implemented; slots11/12 reject explicitly',
            'Green and outer ten pixels remain the frozen baseline; HF metrics include real detail as well as noise',
            'Same host colour, neutral exposure intent and JPEG limitations as DETAIL1D'],jpeg_quality=95,jpeg_subsampling='4:2:0',sharp_slot=0)
    for path in a.dngs:
        raw,meta=read(path);h,w=raw.shape;meta['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        meta['context']=colour.configure(path);tail=colour.tail(path);meta['raw_tail']=tail
        with tifffile.TiffFile(path) as tf:orientation=int(tf.pages[0].tags['Orientation'].value)
        meta['orientation']=orientation;cfa=meta['cfa'];nr=meta['neutral'][0]/meta['neutral'][1];nb=meta['neutral'][2]/meta['neutral'][1]
        base=native.render(raw,nr,nb,cfa,candidate=False);g,_,carrier,_=domain.stages(raw,cfa,nr,nb)
        sharp=native.sharp(g,0,candidate=False);assert np.array_equal(sharp[10:-10,10:-10],q14(base[10:-10,10:-10,1]));del sharp
        meta['green_source_sharp_equal_samples']=(h-20)*(w-20);meta['variants']=[];decoded=[];crops=[];tiles=choose_tiles(raw,384);gain0=None
        border=np.ones((h,w),bool);border[10:-10,10:-10]=False
        for k,name in enumerate(NAMES):
            detail={};extra={}
            if k==0:cam=base
            elif k==1:cam=domain.consume(carrier,base,cfa,nr,nb)
            else:
                slot=0 if k==2 else slot_for(meta['iso']);p=parameters(slot,nr,nb)
                filtered,sm,counts=noise.apply(carrier,g,cfa,p);cam=domain.consume(filtered,base,cfa,nr,nb)
                detail.update(adaptive_branch_counts=counts);extra.update(noise_parameters=p,leica_noise_iso=int(ISOS[slot]))
                if p['mode']==2:
                    biased,_,_=noise.apply(carrier,g,cfa,p,rounding=2)
                    bcam=domain.consume(biased,base,cfa,nr,nb)
                    detail['rounding_sensitivity']=dict(carrier_max_abs_delta=int(np.max(np.abs(biased.astype(np.int64)-filtered))),
                        camera_q14_max_abs_delta=int(np.max(np.abs(q14(bcam)-q14(cam)))),camera_rgb16_changed_pct=float(np.mean(bcam!=cam)*100))
                    del biased,bcam
                del filtered,sm
            assert np.array_equal(cam[:,:,1],base[:,:,1]);assert np.array_equal(cam[border],base[border])
            detail.update(green_equal_samples=h*w,border_equal_rgb_samples=int(border.sum()*3))
            restored=colour.restore(cam,meta['representation_scale']);meter=colour.meter(restored,tail);gain=meter['render_gain']
            if gain0 is None:gain0=gain
            rgb=colour.render(restored,gain);fixed=rgb if gain==gain0 else colour.render(restored,gain0)
            crops.append([rgb[y:y+384,x:x+384].copy() for _,y,x in tiles])
            variant=dict(name=name,meter=meter,gain_delta_ev=float(np.log2(gain/gain0)),native=detail,**extra,
                baseline_gain_crop_metrics=[crop_metrics(fixed[y:y+384,x:x+384]) for _,y,x in tiles],pre_encode=metrics(rgb))
            jpg=out/(path.stem+'_'+name+'.jpg');orient(Image.fromarray(rgb),orientation).save(jpg,quality=95,subsampling=2,optimize=False)
            with Image.open(jpg) as im:decoded.append(np.array(orient(im.convert('RGB'),orientation,inverse=True)))
            variant.update(jpeg=jpg.name,jpeg_bytes=jpg.stat().st_size,jpeg_sha256=hashlib.sha256(jpg.read_bytes()).hexdigest())
            if k<2:
                ref=refs[meta['name']];assert ref['sha256']==meta['sha256']
                assert variant['jpeg_sha256']==ref['variants'][0 if k==0 else 3]['jpeg_sha256'],'DETAIL1D JPEG parity'
            meta['variants'].append(variant);del restored,rgb,fixed,cam
            print(json.dumps(dict(iso=meta['iso'],variant=name,gain_delta_ev=variant['gain_delta_ev'])),flush=True)
        meta['tiles']=[]
        for ti,(kind,y,x) in enumerate(tiles):
            row=dict(kind=kind,xy=[x,y],size=384,variants=[])
            for k,name in enumerate(NAMES):row['variants'].append(dict(name=name,pre_encode=crop_metrics(crops[k][ti]),
                decoded_jpeg=crop_metrics(decoded[k][y:y+384,x:x+384]),mean_abs_rgb8_delta=float(np.abs(crops[k][ti].astype(int)-crops[1][ti].astype(int)).mean())))
            meta['tiles'].append(row)
        png=out/(path.stem+'_comparison.png');comparison(meta,decoded).save(png);meta['comparison']=png.name
        thumb=orient(Image.fromarray(decoded[0]),orientation);thumb.thumbnail((960,960));thumb.save(out/(path.stem+'_overview.jpg'),quality=90)
        report['captures'].append(meta);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        del raw,base,g,carrier,decoded,crops
    print('Complete: '+str(out/'report.json'),flush=True)

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode() if isinstance(e.stderr,bytes) else e.stderr,file=sys.stderr);raise
