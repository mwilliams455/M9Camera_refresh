"""Same-RAW tiled phone-kernel replay with F's unchanged DNG-profile authority."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image
from detail1h import TiledDetail,dng_inputs
from native import Native
from downstream import Downstream
from full_run import orient

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--header',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('dngs',type=Path,nargs='+');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2];native=Native(repo,repo/'PhotonCamera',a.header,a.out/'native')
    colour=Downstream(repo,repo/'PhotonCamera',a.out/'colour');tile=TiledDetail(a.out/'native')
    refs={r['name']:r for r in json.loads((Path(__file__).parent/'results/noise2_guard_report.json').read_text())['captures']}
    report=dict(schema='m9.detail1h.tiled.replay.v1',captures=[],source_hashes=colour.hashes,
        kernel_sha256=hashlib.sha256((repo/'patches/m9detail1h/m9detail1h.cpp').read_bytes()).hexdigest(),
        noise_authority='Original F DNG RGB profiles for equivalence. Phone uses fresh unscaled Camera2 CFA profiles; those can differ.')
    for path in a.dngs:
        norm,m,nd,sensor,gains=dng_inputs(path);ref=refs[path.name]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==ref['sha256'];nr=m['neutral'][0]/m['neutral'][1];nb=m['neutral'][2]/m['neutral'][1]
        colour.configure(path);tail=colour.tail(path);base=native.render(norm,nr,nb,m['cfa'],candidate=False)
        cam,stats=tile.apply(norm,sensor,base,m['cfa'],nr,nb,m['black'],m['white'],m['noise_profile'],gains,m['representation_scale'])
        assert np.array_equal(cam[...,1],base[...,1]);del norm,nd,sensor,gains,base
        restored=colour.restore(cam,m['representation_scale']);meter=colour.meter(restored,tail)
        expected=next(x for x in ref['variants'] if x['name']=='noise_guard');assert meter==expected['meter']
        rgb=colour.render(restored,meter['render_gain']);jpg=a.out/(path.stem+'_detail1h.jpg')
        orient(Image.fromarray(rgb),ref['orientation']).save(jpg,quality=95,subsampling=2,optimize=False)
        sha=hashlib.sha256(jpg.read_bytes()).hexdigest();assert sha==expected['jpeg_sha256'],(path.name,sha,expected['jpeg_sha256'])
        row=dict(name=path.name,raw_sha256=ref['sha256'],iso=m['iso'],cfa=m['cfa'],stats=stats,meter_exact=True,
                 green_equal_samples=cam.shape[0]*cam.shape[1],jpeg_sha256=sha,detail1f_jpeg_exact=True)
        report['captures'].append(row);(a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
        del cam,restored,rgb

if __name__=='__main__':main()
