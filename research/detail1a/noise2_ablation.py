"""Separate Noise2 filter width, threshold and attenuation on exact-context crops."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image
from native import Native
from downstream import Downstream
from inputs import read
from rb_domain import DomainProbe
from noise2 import Noise2,parameters
from rb_domain_run import crop_metrics
from full_run import orient
from run import slot_for

def main():
    ap=argparse.ArgumentParser();ap.add_argument('dng',type=Path);ap.add_argument('header',type=Path);ap.add_argument('reference',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];out=a.out;out.mkdir(parents=True,exist_ok=True)
    noise=Noise2(out/'native');domain=DomainProbe(out/'native');native=Native(repo,repo/'PhotonCamera',a.header,out/'native');colour=Downstream(repo,repo/'PhotonCamera',out/'colour')
    raw,meta=read(a.dng);ref=next(c for c in json.loads((a.reference/'report.json').read_text())['captures'] if c['name']==a.dng.name)
    assert hashlib.sha256(a.dng.read_bytes()).hexdigest()==ref['sha256']
    nr=meta['neutral'][0]/meta['neutral'][1];nb=meta['neutral'][2]/meta['neutral'][1];cfa=meta['cfa']
    base=native.render(raw,nr,nb,cfa,candidate=False);g,_,carrier,_=domain.stages(raw,cfa,nr,nb);colour.configure(a.dng)
    gain=ref['variants'][1]['meter']['render_gain'];rows=[]
    for tile in ref['tiles']:
        x,y=tile['xy'];pad=min(32,x,y)//16*16;size=384;s=np.s_[y-pad:y+size+pad,x-pad:x+size+pad]
        c=carrier[s].copy();gg=g[s].copy();bb=base[s].copy();p0=parameters(0,nr,nb);pi=parameters(slot_for(meta['iso']),nr,nb)
        versions={'corrected':c};fi,mi,_=noise.apply(c,gg,cfa,pi);versions['indexed']=fi
        versions['fixed160']=noise.apply(c,gg,cfa,p0)[0]
        p=dict(pi,shift=p0['shift'],threshold=p0['threshold']);versions['wide_fixed_threshold']=noise.apply(c,gg,cfa,p)[0]
        p=dict(pi,mode=1,carrier_border=5);versions['small_indexed_threshold']=noise.apply(c,gg,cfa,p)[0]
        v=np.abs(c.astype(np.int64)-mi)*noise.lut[gg>>6]//16
        versions['indexed_no_attenuation']=np.where(v>=pi['threshold'],c,fi).astype(np.int32)
        versions['indexed_smooth_only']=mi
        row=dict(kind=tile['kind'],xy=tile['xy'],variants={});core=np.s_[pad:pad+size,pad:pad+size]
        for name,ca in versions.items():
            cam=domain.consume(ca,bb,cfa,nr,nb);rgb=colour.render(colour.restore(cam,meta['representation_scale']),gain)
            jpg=out/f'{meta["iso"]}_{tile["kind"]}_{name}.jpg';orient(Image.fromarray(rgb),ref['orientation']).save(jpg,quality=95,subsampling=2,optimize=False)
            with Image.open(jpg) as im:decoded=np.array(orient(im.convert('RGB'),ref['orientation'],inverse=True))[core]
            row['variants'][name]=crop_metrics(decoded)
            if name in ('corrected','indexed','fixed160'):
                k={'corrected':1,'indexed':3,'fixed160':2}[name]
                with Image.open(a.reference/ref['variants'][k]['jpeg']) as im:
                    expected=np.array(orient(im.convert('RGB'),ref['orientation'],inverse=True))[y:y+size,x:x+size]
                assert np.array_equal(expected,decoded),(name,'context crop differs from full-frame reference')
        rows.append(row)
    report=dict(iso=meta['iso'],name=meta['name'],raw_sha256=ref['sha256'],full_jpeg_control_crop_parity=True,rows=rows)
    (out/'ablation.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in rows:
        b=row['variants']['corrected']['chroma_hf_rms'];print(row['kind'],{k:round(100*(v['chroma_hf_rms']/b-1),3) for k,v in row['variants'].items()},flush=True)

if __name__=='__main__':main()
