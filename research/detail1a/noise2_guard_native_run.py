"""Five-RAW native port verification against accepted DETAIL1F pixels/JPEGs."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image
from native import Native
from downstream import Downstream
from inputs import read
from rb_domain import DomainProbe
from rb_probe import q14
from noise2 import Noise2
from noise2_guard import guarded
from noise2_guard_native import NativeGuard
from full_run import orient

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True);ap.add_argument('--reference-report',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    native=Native(repo,a.assembled.resolve(),a.header.resolve(),out/'native')
    colour=Downstream(repo,a.assembled.resolve(),out/'native_colour');domain=DomainProbe(out/'native')
    noise=Noise2(out/'native');port=NativeGuard(out/'native')
    refs={c['name']:c for c in json.loads(a.reference_report.read_text())['captures']}
    source=Path(__file__).parent
    report=dict(schema='m9.detail1g.native.guard.parity.v1',captures=[],source_hashes=colour.hashes,
        implementation_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            source/'noise2_guard_native.cpp',source/'noise2_guard_native.py',source/'noise2_guard.py',source/'inputs.py']},
        scope='Native host port, nominal profile factor1; frozen DNG metadata, green, fixed ISO160 Sharp and downstream colour.',
        limitations=['No measured sensor calibration or historical profile repair',
                     'No Android/JNI integration, ARM build, phone timing or APK parity claim'])
    for path in a.dngs:
        ref=refs[path.name];assert hashlib.sha256(path.read_bytes()).hexdigest()==ref['sha256']
        raw,meta,nd=read(path,with_noise=True);cfa=meta['cfa'];nr=meta['neutral'][0]/meta['neutral'][1];nb=meta['neutral'][2]/meta['neutral'][1]
        colour.configure(path);tail=colour.tail(path)
        base=native.render(raw,nr,nb,cfa,candidate=False);g,_,carrier,_=domain.stages(raw,cfa,nr,nb)
        sharp=native.sharp(g,0,candidate=False);assert np.array_equal(sharp[10:-10,10:-10],q14(base[10:-10,10:-10,1]));del sharp
        expected,_=guarded(noise,carrier,g,cfa,nr,nb,**nd)
        actual,sm,vr,conf=port.apply(carrier,cfa,nr,nb,**nd)
        assert np.array_equal(actual,expected), (path.name,int(np.count_nonzero(actual!=expected)))
        correction=actual.astype(np.int64)-carrier
        assert np.all(np.abs(correction)<=np.sqrt(vr)*.5+.50001)
        assert np.all(actual>=np.minimum(carrier,sm)) and np.all(actual<=np.maximum(carrier,sm))
        cam=domain.consume(actual,base,cfa,nr,nb)
        del sm,vr,conf,correction,expected,actual,carrier,nd,raw,g
        assert np.array_equal(cam[...,1],base[...,1])
        assert all(np.array_equal(cam[s],base[s]) for s in [np.s_[:10],np.s_[-10:],np.s_[:,:10],np.s_[:,-10:]])
        del base
        restored=colour.restore(cam,meta['representation_scale']);meter=colour.meter(restored,tail)
        refvariant=next(x for x in ref['variants'] if x['name']=='noise_guard')
        assert meter==refvariant['meter']
        rgb=colour.render(restored,meter['render_gain']);jpg=out/(path.stem+'_noise_guard_native.jpg')
        orient(Image.fromarray(rgb),ref['orientation']).save(jpg,quality=95,subsampling=2,optimize=False)
        sha=hashlib.sha256(jpg.read_bytes()).hexdigest();assert sha==refvariant['jpeg_sha256']
        h,w=cam.shape[:2];row=dict(name=path.name,iso=meta['iso'],cfa=cfa,raw_sha256=ref['sha256'],
            exact_carrier_samples=h*w,native_green_unchanged_samples=h*w,
            fixed_iso160_sharp_equal_samples=(h-20)*(w-20),border10_rgb_unchanged=True,
            correction_bounds=True,meter_exact=True,jpeg_sha256=sha,jpeg_matches_detail1f=True)
        report['captures'].append(row);(out/'native_report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True);del cam,restored,rgb

if __name__=='__main__':main()
