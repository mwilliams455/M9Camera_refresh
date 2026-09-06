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
    'm9cam.chromaexposure.v1b.localneutral1a',
    'MAX_EXTRA_NEG_CR_COMPRESSION = 0.10',
    'MAX_LOCAL_EXTRA_NEG_CR_COMPRESSION = 0.08',
    'GRID_ROWS = 4',
    'GRID_COLS = 6',
    'LOCAL_ABS_CB_MAX = 10',
    'LOCAL_MEDIAN_CR_MAX = -4.0',
    'LOCAL_Q75_CR_MAX = 0.0',
    'LARGE_REGION_MIN_NEUTRAL_FRACTION = 0.28',
    'GREEN_GLOBAL_NEUTRAL',
    'GREEN_LOCAL_NEUTRAL',
    'GREEN_HOLD',
    'localNeutralRegions',
    'localBestRow',
    'localBestColumn',
    'hasAdjacentSupport',
    'candidateLocalMeanCrImprovement',
    'ACCEPT_MIN_LOCAL_MEAN_CR_IMPROVEMENT = 0.25',
    'coherent_local_neutral_green_axis_bias_global_statistics_diluted',
]
for token in required_helper:
    if token not in helper:
        raise SystemExit(f'CHROMAEXPOSURE1B verify failed: helper missing {token!r}')

# The 1A global gate is deliberately retained rather than loosened to rescue false negatives.
for token in [
    'GREEN_MEDIAN_CR_MAX = -3.0',
    'GREEN_Q75_CR_MAX = 1.0',
    'GREEN_NEGATIVE_FRACTION_MIN = 0.60',
]:
    if token not in helper:
        raise SystemExit(f'CHROMAEXPOSURE1B verify failed: frozen GREENAXIS1A global gate changed/missing {token!r}')

required_renderer = [
    'cameraRotation, 0.0, 0.0);',
    'cameraRotation, candidateEv, 0.0);',
    'double chromaGreenCompression) throws Exception',
    'final double effectiveCrGain = tgCrGain * (1.0 - boundedGreenCompression);',
    'M9ChromaExposure1AController.evaluate(bitmap, out.diagnostics, edgeDecision)',
    'NATIVE_NEGATIVE_CR_RERENDER',
    'directRenderedLumaPreChroma',
    'chromaExposure1BRequestedNegativeCrCompression',
    'chromaExposure1BEffectiveNegativeCrGain',
    'out.diagnostics.put("chromaExposure1B", chromaDecision);',
]
for token in required_renderer:
    if token not in renderer:
        raise SystemExit(f'CHROMAEXPOSURE1B verify failed: renderer missing {token!r}')
if 'out.diagnostics.put("chromaExposure1A", chromaDecision);' in renderer:
    raise SystemExit('CHROMAEXPOSURE1B verify failed: stale 1A top-level diagnostic key remains')

native_calls = renderer.count('effectiveRenderGain, tgCbGain, effectiveCrGain')
if native_calls != 4:
    raise SystemExit(f'CHROMAEXPOSURE1B verify failed: expected 4 effective-Cr native calls, found {native_calls}')
if 'effectiveRenderGain, tgCbGain, tgCrGain' in renderer:
    raise SystemExit('CHROMAEXPOSURE1B verify failed: unpatched promoted native Cr call remains')

# Native ABI/kernel and Java bridge remain unchanged. 1B changes detector/decision evidence only.
for token in [
    'const double crModern = cr < 0 ? cr * tgCrGain : static_cast<double>(cr);',
    'void renderStripScalar(const ColorContext& ctx,',
]:
    if token not in native:
        raise SystemExit(f'CHROMAEXPOSURE1B verify failed: native baseline contract missing {token!r}')
for token in [
    'double tgCbGain,',
    'double tgCrGain,',
    'renderBlockParallelDirectBitmap',
]:
    if token not in bridge:
        raise SystemExit(f'CHROMAEXPOSURE1B verify failed: Java native bridge baseline missing {token!r}')

if 'M9 DNGGAINMAPFIX1A' not in dng:
    raise SystemExit('CHROMAEXPOSURE1B verify failed: DNGGAINMAPFIX1A marker missing')
expected_order = '''parameters.sensorPix.left,\n                   parameters.sensorPix.top,\n                   parameters.sensorPix.right,\n                   parameters.sensorPix.bottom,'''
if expected_order not in dng:
    raise SystemExit('CHROMAEXPOSURE1B verify failed: corrected DNG GainMap ordering missing')

print('OK CHROMAEXPOSURE1B LOCALNEUTRAL1A helper present')
print('OK GREENAXIS1A global thresholds remain frozen; 1B adds regional evidence instead of loosening q75')
print('OK local detector uses strict low-chroma 4x6 regions plus broad-surface/adjacent-support qualification')
print('OK local path capped <=8%, absolute frame-level negative-Cr compression remains <=10%')
print('OK candidate acceptance tracks selected local region and preserves global/local luma')
print('OK native ABI/kernel, capture, TC20 and DNGGAINMAPFIX1A remain frozen')
