"""Read-only capture inventory and noise-profile provenance audit, not a fit."""
from pathlib import Path
import argparse, datetime, hashlib, itertools, json, re
import numpy as np
import tifffile
from inputs import rational, PATTERNS

REFERENCE='https://developer.android.com/reference/android/hardware/camera2/CaptureResult#SENSOR_NOISE_PROFILE'

def audit(root, assembled):
    captures=[]
    for path in sorted(root.rglob('*.dng')):
        with tifffile.TiffFile(path) as tf:
            tags=tf.pages[0].tags
            desc=str(tags['ImageDescription'].value) if 'ImageDescription' in tags else ''
            fields=dict(re.findall(r'(FrameCount|CameraID)\s*=\s*([^\n]+)',desc))
            pattern=tuple(tags['CFAPattern'].value);p=np.asarray(tags['NoiseProfile'].value).reshape(3,2)
            assert np.isfinite(p).all() and (p>=0).all()
            stamp=re.search(r'IMG_(\d{8}_\d{6})',path.name)
            row=dict(name=path.name,raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                model=tags['Model'].value,iso=int(rational(tags['ISOSpeedRatings'])[0]),
                exposure_seconds=float(rational(tags['ExposureTime'])[0]),
                focal_length_mm=float(rational(tags['FocalLength'])[0]),cfa=PATTERNS[pattern],
                noise_profile=p.ravel().tolist(),reported_frame_count=int(fields['FrameCount']) if 'FrameCount' in fields else None,
                camera_id=fields.get('CameraID'),filename_time=stamp.group(1) if stamp else None)
            if row['cfa']==3:
                # A bound on sigma uncertainty for a hypothetical R/B pair swap,
                # not a claim that the stored profile actually needs swapping.
                # Ratio of two positive affine functions is monotonic on [0,1].
                ratios=[(p[0,0]*x+p[0,1])/(p[2,0]*x+p[2,1]) for x in (0.,1.)]
                row['hypothetical_rb_swap_max_sigma_ratio']=float(np.sqrt(max(ratios+[1/r for r in ratios])))
            captures.append(row)
    nearby=[]
    for a,b in itertools.combinations(captures,2):
        if not a['filename_time'] or not b['filename_time']:continue
        dt=abs((datetime.datetime.strptime(a['filename_time'],'%Y%m%d_%H%M%S')-datetime.datetime.strptime(b['filename_time'],'%Y%m%d_%H%M%S')).total_seconds())
        if dt<=120 and all(a[k]==b[k] for k in ['model','camera_id','iso','exposure_seconds','focal_length_mm']):
            nearby.append(dict(a=a['name'],b=b['name'],seconds_apart=dt))
    source_paths=['app/src/main/java/com/particlesdevs/photoncamera/processing/'+p for p in [
        'DngCreator.java','render/Parameters.java','render/NoiseModeler.java']]
    return dict(schema='m9.detail1g.calibration.audit.v1',captures=captures,raw_count=len(captures),
        same_settings_pairs_within_120_seconds=nearby,
        pair_screen='Exact model/camera/ISO/exposure/focal length plus filename time within120s. Metadata screen only; a match would still need scene/illumination review.',
        inspected_source_sha256={p:hashlib.sha256((assembled/p).read_bytes()).hexdigest() for p in source_paths},
        source_findings=[
            'Parameters passes CaptureResult.SENSOR_NOISE_PROFILE and cfaPattern directly to NoiseModeler.',
            'NoiseModeler four-pair branch assumes [R,G,G,B] without using its bayer argument.',
            'DngCreator packs the resulting computeModel as RGB NoiseProfile.',
            'Fresh standards-compliant CFA-order input is mispacked for GRBG/GBRG/BGGR in that branch; custom and three-pair paths differ.',
            'noise2_profile_rgb in the native research port explicitly maps all four layouts; it does not rescale or rewrite DNG tags.',
            'Inspected current source does not identify which historical/custom path produced each DNG.',
            'FrameCount=1 does not independently identify adaptiveMpy, actual noise covariance or sensor processing.'],
        source_reference=REFERENCE, measured_sensor_calibration=False,
        disposition='Keep factor1 and original DNG tags for accepted F/native parity; collect matched repeat captures before a calibrated production noise model.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('inputs',type=Path);ap.add_argument('assembled',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();r=audit(a.inputs,a.assembled);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['raw_count','same_settings_pairs_within_120_seconds','measured_sensor_calibration']},indent=2))
