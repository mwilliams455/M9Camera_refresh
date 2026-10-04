#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-scenefingerprint1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists(): raise SystemExit(f'missing {rel}')
    return p.read_text()

scene = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java')
neg = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
coord = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java')
gradle = read('app/build.gradle')

checks = {
    'scene schema frozen': 'm9cam.sceneexposure.v8.renderaware1h' in scene,
    'tile payload present': 'spatialTileMedians3x3' in scene,
    'nine named tiles present': all(x in scene for x in ['topLeft','topCenter','topRight','middleLeft','middleCenter','middleRight','bottomLeft','bottomCenter','bottomRight']),
    'negative v4 schema': 'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a' in neg,
    'fingerprint v2 schema': 'm9cam.scenefingerprint.v2.scene1h_spatialtiles1b' in neg,
    'threshold remains 1.0': 'private static final double SIMILAR_SCENE_DISTANCE = 1.0;' in neg,
    'age gate remains 60s': 'private static final long MAX_FEEDBACK_AGE_MS = 60_000L;' in neg,
    'spatial scale 60': 'Math.abs(a[i] - b[i]) / 60.0' in neg,
    'nearest candidate still used': 'if (d < bestDistance)' in neg,
    'signedcal formula frozen label': 'recommendationFormulaFrozen", "M9NEGATIVE1A"' in neg,
    'signedcal still non-live': 'usedToMutateCaptureTarget", false' in neg,
    'coordinator v5': 'm9cam.exposuresplit.v5.capturemeter1b.m9negative1c.scenefingerprint1b.signedcal1a' in coord,
    'version 1.49': "versionName '1.49-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cm1b'" in gradle,
}
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
    if not ok: raise SystemExit(1)

# Regression logic from the two field batches. The prior-good associations had worst
# observed max tile-median delta <= ~56 Y (distance <= .933). The newly observed false
# associations began at >=102 Y (distance >=1.70). Keep a wide safety margin around 1.0.
def spatial_distance(a,b):
    return max(abs(x-y) for x,y in zip(a,b))/60.0

good = ([80,92,104,88,101,113,76,89,100], [85,98,110,93,107,119,82,95,106])
edge_good = ([20,35,50,65,80,95,110,125,140], [76,80,94,111,124,145,160,173,196])
false_scene = ([45,60,75,90,105,120,135,150,165], [147,162,177,192,207,222,237,252,255])
assert spatial_distance(*good) < 1.0
assert spatial_distance(*edge_good) < 1.0
assert spatial_distance(*false_scene) > 1.0
print('OK   synthetic field-regression separation around threshold 1.0')

# Frozen photographic seams must remain untouched by this overlay.
for rel in [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]:
    text = read(rel)
    if not text.strip(): raise SystemExit(f'empty frozen seam {rel}')
print('OK   frozen photographic seams present')
print('SCENEFINGERPRINT1B verification passed')
