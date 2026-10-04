#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')
here = Path(__file__).resolve().parent


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1B missing expected file: {rel}')
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha256(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1B quality-freeze guard missing expected file: {rel}')
    return hashlib.sha256(p.read_bytes()).hexdigest()

# 1B MUST layer on top of 1A and remain diagnostic-only. Preserve hashes of the live
# exposure decision path, metadata wiring, and frozen photographic renderer so this
# calibration overlay cannot silently alter image formation.
scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
if 'm9cam.sceneexposure.v1.signedpressure1a' not in read(scene_rel):
    raise SystemExit('SCENEEXPOSURE1B requires SCENEEXPOSURE1A first')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

# Replace only the diagnostic recommendation class. No live exposure or renderer file
# is patched by SCENEEXPOSURE1B.
src = here / 'sceneexposure1b' / 'M9SceneExposureDiagnostic.java'
if not src.exists():
    raise SystemExit('SCENEEXPOSURE1B source diagnostic class missing')
shutil.copy2(src, root / scene_rel)

# Build identity only.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.34-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1a'"
new_v = "versionName '1.35-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1b'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1B: expected SCENEEXPOSURE1A versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.34-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1a'
new_b = '1.35-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1b'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1B: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

# Hard quality/M9 freeze check: these files must be byte-identical before vs after 1B.
for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1B QUALITY FREEZE FAILED: {rel} changed')
    print(f'OK   quality-freeze unchanged: {rel}')

print('M9Cam SCENEEXPOSURE1B applied: diagnostic calibration only; live exposure and frozen M9 renderer unchanged')
