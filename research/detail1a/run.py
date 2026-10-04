#!/usr/bin/env python3
"""M9DETAIL1A: isolated, reproducible GL2G Sharp ISO-table comparison.

No automatic sensor ISO mapping is promoted. 1x and historic 2x are probes.
Images show the green detail stage with a common display scale, not final JPEGs.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter, sobel
from PIL import Image,ImageDraw,ImageFont
from native import Native,ISOS,checks
from inputs import read

def slot_for(iso):
    value=min(2500,max(160,float(iso)))
    return int(np.argmin(np.abs(np.log2(ISOS/value))))

def tile_metrics(rgb):
    z=rgb.astype(np.float64)/65535;g=z[:,:,1]
    hi=g-gaussian_filter(g,1.0)
    grad=np.hypot(sobel(g,axis=0)/8,sobel(g,axis=1)/8)
    return dict(green_mean=float(g.mean()),green_hf_rms=float(np.sqrt(np.mean(hi**2))),
                green_gradient_p95=float(np.percentile(grad,95)),
                rgb_zero_pct=float(np.mean(rgb==0)*100),rgb_white_pct=float(np.mean(rgb==65535)*100))

def choose_tiles(raw,size):
    # Fixed grid, identical selection for every candidate. Exclude whole-frame border.
    h,w=raw.shape;rows=[]
    for y in range(16,h-size-16,size):
        for x in range(16,w-size-16,size):
            a=raw[y:y+size,x:x+size].astype(float)
            g=(a[0::2,1::2]+a[1::2,0::2])*.5
            score=float(np.percentile(np.abs(np.diff(g,axis=0)),90)+np.percentile(np.abs(np.diff(g,axis=1)),90))
            rows.append((score,float(np.median(g)),y,x))
    edge=max(rows)
    eligible=[r for r in rows if 256<r[1]<55000]
    flat=min(eligible or rows)
    return [('edge',edge[-2],edge[-1]),('quiet',flat[-2],flat[-1])]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--firmware',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--size',type=int,default=384);ap.add_argument('--full-parity',action='store_true')
    ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'tools'))
    import m9_sharpness_export_fulliso_header as firmware
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    header=out/'native/m9_sharp_fulliso_bank.h'
    subprocess.run([sys.executable,str(repo/'tools/m9_sharpness_export_fulliso_header.py'),str(a.firmware),'--out',str(header)],check=True,stdout=subprocess.DEVNULL)
    fw=a.firmware.read_bytes();assert hashlib.sha256(fw).hexdigest()==firmware.FW_SHA
    resource=[p for path,n,p in firmware.walk(fw) if len(p)==firmware.EXPECTED_SIZE];assert len(resource)==1
    bank=np.frombuffer(resource[0],'<i2',count=13*2050,offset=firmware.BANK_OFF).reshape(13,2050)
    modes=firmware.STANDARD_EXPECT
    native=Native(repo,a.assembled.resolve(),header,out/'native')
    report=dict(schema='m9.detail1a.offline.v1',source_hashes=native.source_hashes,
                firmware_sha256=firmware.FW_SHA,checks=checks(native,bank,modes),captures=[],
                scope='Native RGB16 detail stage; NORM030 reconstructed from Android DNG GainMaps; downstream colour, TC20, tone and JPEG are not executed',
                sensor_iso_mapping_validated=False,noise_reduction_implemented=False,
                metric_limit='High-frequency RMS includes scene texture and noise; it is not a noise-only quality score',
                schedule=[])
    for i in range(13):
        row=bank[i].astype(int);coeff=np.clip(row*2 if modes[i]==4 else row//2 if modes[i]==2 else row,-2048,2048)
        report['schedule'].append(dict(iso=int(ISOS[i]),slot=i,mode=modes[i],base_sha256=hashlib.sha256(bank[i].tobytes()).hexdigest(),
            correction_at_positive_residual={str(r):int(coeff[1024+r]) for r in [4,8,16,32,64,128,256,512,1024]}))
    pictures=[];seen=set()
    for path in a.dngs:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:continue
        seen.add(digest);raw,meta=read(path);meta['sha256']=digest
        nr=float(meta['neutral'][0]/meta['neutral'][1]);nb=float(meta['neutral'][2]/meta['neutral'][1]);cfa=meta['cfa']
        slots=[slot_for(meta['iso']),slot_for(meta['iso']*2)]
        meta['mapping_probes']={'physical_iso_1x':slots[0],'historical_main_iso_2x':slots[1]}
        meta['tiles']=[]
        if a.full_parity and len(report['captures'])<2:
            b=native.render(raw,nr,nb,cfa,candidate=False)
            q=native.render(raw,nr,nb,cfa,slot=0)
            assert np.array_equal(b,q),('full raster parity',path.name)
            meta['full_raster_slot0_parity_rgb_samples']=int(q.size);del b,q
        for kind,y,x in choose_tiles(raw,a.size):
            halo=16;block=np.ascontiguousarray(raw[y-halo:y+a.size+halo,x-halo:x+a.size+halo])
            crop=np.s_[halo:-halo,halo:-halo,:]
            baseline=native.render(block,nr,nb,cfa,candidate=False)[crop].copy()
            row=dict(kind=kind,xy=[x,y],size=a.size,baseline=tile_metrics(baseline),slots=[])
            selected={}
            for slot in range(13):
                candidate=native.render(block,nr,nb,cfa,slot=slot)[crop].copy()
                if slot<=2:assert np.array_equal(candidate,baseline)
                delta=candidate.astype(np.int32)-baseline.astype(np.int32)
                m=tile_metrics(candidate)
                m.update(slot=slot,leica_iso=int(ISOS[slot]),max_rgb16_delta=int(np.abs(delta).max()),
                    mean_abs_rgb16_delta=float(np.abs(delta).mean()),changed_channels_pct=float(np.mean(delta!=0)*100))
                row['slots'].append(m)
                if slot in slots:selected[slot]=candidate
            meta['tiles'].append(row)
            # Diagnostic grayscale avoids suggesting an unexecuted final colour render.
            gs=baseline[:,:,1].astype(float)/65535.0
            display_scale=.55/max(float(np.percentile(gs,95)),.02)
            ims=[]
            for pixels in [baseline,selected[slots[0]],selected[slots[1]]]:
                z=np.clip(pixels[:,:,1].astype(float)/65535.0*display_scale,0,1)
                z=np.where(z<=.0031308,12.92*z,1.055*z**(1/2.4)-.055)
                ims.append(Image.fromarray(np.uint8(np.clip(z*255+.5,0,255))).convert('RGB'))
            pictures.append((meta['name'],meta['iso'],kind,slots,ims))
        report['captures'].append(meta)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'capture':path.name,'iso':meta['iso'],'cfa':cfa,'probe_slots':slots,'tiles':len(meta['tiles'])}),flush=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    for i,(name,iso,kind,slots,ims) in enumerate(pictures):
        canvas=Image.new('RGB',(3*a.size,a.size+86),'#171b22');draw=ImageDraw.Draw(canvas)
        draw.text((10,7),f'{name}  |  ISO {iso}  |  {kind}',font=font,fill='white')
        labels=['Current fixed ISO160',f'1x probe: Leica ISO {ISOS[slots[0]]}',f'2x probe: Leica ISO {ISOS[slots[1]]}']
        for col,(im,label) in enumerate(zip(ims,labels)):
            draw.text((col*a.size+10,32),label,font=font,fill='#b8d8ee');canvas.paste(im,(col*a.size,60))
        draw.text((10,a.size+64),'Native green detail stage; common display scale; not final M9 JPEG colour or tone.',font=font,fill='#c8c8c8')
        canvas.save(out/f'comparison_{i:02d}.png')
    print('PASS',out/'report.json')

if __name__=='__main__':main()
