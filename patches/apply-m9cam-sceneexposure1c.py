#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1c.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')
here = Path(__file__).resolve().parent


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1C missing expected file: {rel}')
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha256(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1C quality-freeze guard missing expected file: {rel}')
    return hashlib.sha256(p.read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene_before = read(scene_rel)
if 'm9cam.sceneexposure.v2.signedpressure1b' not in scene_before:
    raise SystemExit('SCENEEXPOSURE1C requires SCENEEXPOSURE1B first')
for frozen_positive_marker in [
    'BODY_MEDIAN_ZERO_NEED_Y = 138.0',
    'HEALTHY_CENTER_MAX_ATTENUATION = 0.88',
    'SEVERE_BACKLIGHT_PRESERVE_START = 0.72',
    'SEVERE_BACKLIGHT_PRESERVE_FULL = 0.90',
]:
    if frozen_positive_marker not in scene_before:
        raise SystemExit(f'SCENEEXPOSURE1C positive-freeze anchor missing: {frozen_positive_marker}')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

src = here / 'sceneexposure1c' / 'M9SceneExposureDiagnostic.java'
if not src.exists():
    raise SystemExit('SCENEEXPOSURE1C source diagnostic class missing')
shutil.copy2(src, root / scene_rel)

gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.35-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1b'"
new_v = "versionName '1.36-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1c'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1C: expected SCENEEXPOSURE1B versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.35-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1b'
new_b = '1.36-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1c'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1C: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1C QUALITY FREEZE FAILED: {rel} changed')
    print(f'OK   quality-freeze unchanged: {rel}')

print('M9Cam SCENEEXPOSURE1C applied: diagnostic negative/high-key gate only; 1B positive path and live M9 exposure/rendering unchanged')
