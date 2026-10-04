"""Falsify pre-interpolation white limiting combined with independent DCB.

The existing coherent-control fixture harness is reused with an explicit
one-variant override. This is an offline experiment, not an application hook.
"""
from pathlib import Path
import argparse,hashlib,json
import rawpy
import coherent_green_probe as screen
from native import Native
from rb_domain import DomainProbe
from demosaic_control import Control,local_control
from fringe_replay import white_probe


def prelimited_variant(native,probe,control,norm,base,sensor,cfa,neutral,white=1023):
    scale=1.6105431518598052  # The fixed capture/fixture representation scale.
    capped=white_probe(norm,neutral,scale,cfa)
    cam=control.render(capped,base,cfa,neutral,rawpy.DemosaicAlgorithm.DCB)
    yield 'prelimited_DCB',local_control(cam,base,sensor,white)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');control=Control(a.out/'temporary')
    screen.variants=prelimited_variant;screen.MODES=('prelimited_DCB',)
    result=screen.synthetic(native,probe,control,a.cfas)
    result['schema']='m9.prelimited_dcb_probe.v1'
    result['scope']='The fixed-green DCB control is rerun with a common physical-white limit before interpolation; the original green plane, border10 and clipping-distance4..8 support remain. Both previous oracles and scene-chroma metric retained. No noise calibration or Android implementation.'
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['fixture_harness_sha256']=hashlib.sha256(Path(screen.__file__).read_bytes()).hexdigest()
    result['spatial_source_hashes']=native.source_hashes
    result['rawpy_version']=rawpy.__version__;result['libraw_version']=rawpy.libraw_version
    cases=result.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
