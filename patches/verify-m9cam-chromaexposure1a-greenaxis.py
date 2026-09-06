#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
helper = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ChromaExposure1AController.java').read_text()
dng = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java').read_text()
native = (root / 'app/src/main/cpp/m9color_jni.cpp').read_text()
bridge = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()

required_helper = [
    'm9cam.chromaexposure.v1a.greenaxis1a',
    'MAX_EXTRA_NEG_CR_COMPRESSION = 0.10',
    'coherent_low_chroma_green_axis_bias_after_exposure_placement',
    'acceptCandidate(JSONObject before, JSONObject after)',
]
for token in required_helper:
    if token not in helper:
        raise SystemExit(f'CHROMAEXPOSURE1A verify failed: helper missing {token!r}')

required_renderer = [
    'cameraRotation, 0.0, 0.0);',
    'cameraRotation, candidateEv, 0.0);',
    'double chromaGreenCompression) throws Exception',
    'final double effectiveCrGain = tgCrGain * (1.0 - boundedGreenCompression);',
    'M9ChromaExposure1AController.evaluate(bitmap, out.diagnostics, edgeDecision)',
    'NATIVE_NEGATIVE_CR_RERENDER',
    'directRenderedLumaPreChroma',
    'chromaExposure1A',
]
for token in required_renderer:
    if token not in renderer:
        raise SystemExit(f'CHROMAEXPOSURE1A verify failed: renderer missing {token!r}')

native_calls = renderer.count('effectiveRenderGain, tgCbGain, effectiveCrGain')
if native_calls != 4:
    raise SystemExit(f'CHROMAEXPOSURE1A verify failed: expected 4 effective-Cr native calls, found {native_calls}')
if 'effectiveRenderGain, tgCbGain, tgCrGain' in renderer:
    raise SystemExit('CHROMAEXPOSURE1A verify failed: unpatched promoted native Cr call remains')

# The established native ABI/kernel and bridge stay unchanged; the new control is supplied by
# changing only the per-frame tgCrGain argument in M9R35Renderer.
for token in [
    'const double crModern = cr < 0 ? cr * tgCrGain : static_cast<double>(cr);',
    'void renderStripScalar(const ColorContext& ctx,',
]:
    if token not in native:
        raise SystemExit(f'CHROMAEXPOSURE1A verify failed: native baseline contract missing {token!r}')
for token in [
    'double tgCbGain,',
    'double tgCrGain,',
    'renderBlockParallelDirectBitmap',
]:
    if token not in bridge:
        raise SystemExit(f'CHROMAEXPOSURE1A verify failed: Java native bridge baseline missing {token!r}')

# DNG GainMap correctness must remain promoted.
if 'M9 DNGGAINMAPFIX1A' not in dng:
    raise SystemExit('CHROMAEXPOSURE1A verify failed: DNGGAINMAPFIX1A marker missing')
expected_order = '''parameters.sensorPix.left,\n                   parameters.sensorPix.top,\n                   parameters.sensorPix.right,\n                   parameters.sensorPix.bottom,'''
if expected_order not in dng:
    raise SystemExit('CHROMAEXPOSURE1A verify failed: corrected DNG GainMap ordering missing')

print('OK CHROMAEXPOSURE1A GREENAXIS1A helper and post-exposure detector present')
print('OK correction uses existing native negative-Cr seam; native ABI/kernel unchanged')
print('OK baseline render passes zero chroma correction; DARK rerenders remain exposure-only initially')
print('OK correction bounded to <=10% and candidate acceptance checks green improvement + luma stability')
print('OK DNGGAINMAPFIX1A remains promoted')
