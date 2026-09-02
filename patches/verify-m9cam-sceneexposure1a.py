#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

checks = {
    'scene diagnostic class': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'm9cam.sceneexposure.v1.signedpressure1a'),
    'diagnostic-only marker': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'diagnostic_only_no_exposure_mutation'),
    'positive pressure': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'positiveEvCandidate'),
    'negative pressure': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'negativeEvCandidate'),
    'signed recommendation': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'recommendedSignedEv'),
    'step0 evaluation': (
        'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
        'M9SceneExposureDiagnostic.evaluateStep0'),
    'metadata output': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
        'm9SceneExposureDiagnostic'),
    'build identity': (
        'app/build.gradle',
        '1.34-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1a'),
    'existing exposure audit retained': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
        'm9ExposureAudit'),
}

for label, (rel, needle) in checks.items():
    p = root / rel
    if not p.exists():
        raise SystemExit(f'FAIL {label}: missing {rel}')
    text = p.read_text()
    if needle not in text:
        raise SystemExit(f'FAIL {label}: {needle!r} missing from {rel}')
    print(f'OK   {label}')

# Guard the central contract: the new call returns no exposure pair and its class has
# no public method that applies/mutates exposure. This overlay must remain observational.
scene = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java').read_text()
for forbidden in ['applyExposure', 'applySceneExposure', 'setExpo(', 'CaptureRequest.Builder']:
    if forbidden in scene:
        raise SystemExit(f'FAIL diagnostic-only contract: forbidden mutation marker {forbidden!r}')
print('OK   diagnostic-only no exposure mutation markers')

print('SCENEEXPOSURE1A verification passed')
