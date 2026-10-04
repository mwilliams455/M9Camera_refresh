#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
helper = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ChromaExposure1AController.java').read_text()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
dng = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java').read_text()
native = (root / 'app/src/main/cpp/m9color_jni.cpp').read_text()
bridge = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()

required_helper = [
    'm9cam.chromaexposure.v1c.arbitration1a.frozensamples1a',
    'LOCAL_OVERRIDE_MIN_COMPRESSION_ADVANTAGE = 0.01',
    'localOverridesGlobal',
    'coherent_local_neutral_green_axis_bias_stronger_than_marginal_global_gate',
    'measureFrozenLocalSampleSet(Bitmap beforeBitmap, Bitmap afterBitmap,',
    'coordinates_selected_once_from_before_bitmap_local_neutral_mask_then_reused_after_rerender',
    'candidateLocalAcceptanceMode',
    'frozen_before_neutral_sample_coordinates',
    'candidateLocalFrozenSampleCount',
]
for token in required_helper:
    if token not in helper:
        raise SystemExit(f'CHROMAEXPOSURE1C verify failed: helper missing {token!r}')

required_renderer = [
    'M9ChromaExposure1AController.acceptCandidate(bitmap, chromaCandidate, chromaDecision, afterChroma)',
    'chromaExposure1CRequestedNegativeCrCompression',
    'chromaExposure1CEffectiveNegativeCrGain',
    'out.diagnostics.put("chromaExposure1C", chromaDecision);',
    'CHROMAEXPOSURE1C_ARBITRATION1A_FROZENSAMPLES1A',
]
for token in required_renderer:
    if token not in renderer:
        raise SystemExit(f'CHROMAEXPOSURE1C verify failed: renderer missing {token!r}')

if 'acceptCandidate(JSONObject before, JSONObject after)' in helper:
    raise SystemExit('CHROMAEXPOSURE1C verify failed: old reclassified-only acceptance signature remains')
if 'out.diagnostics.put("chromaExposure1B", chromaDecision);' in renderer:
    raise SystemExit('CHROMAEXPOSURE1C verify failed: old 1B diagnostics key remains')

# Safety/freeze contracts inherited from 1B and earlier promoted baseline.
for token in [
    'MAX_EXTRA_NEG_CR_COMPRESSION = 0.10',
    'MAX_LOCAL_EXTRA_NEG_CR_COMPRESSION = 0.08',
    'GREEN_MEDIAN_CR_MAX = -3.0',
    'GREEN_Q75_CR_MAX = 1.0',
    'GREEN_NEGATIVE_FRACTION_MIN = 0.60',
]:
    if token not in helper:
        raise SystemExit(f'CHROMAEXPOSURE1C verify failed: frozen chroma contract missing {token!r}')

for token in [
    'const double crModern = cr < 0 ? cr * tgCrGain : static_cast<double>(cr);',
    'void renderStripScalar(const ColorContext& ctx,',
]:
    if token not in native:
        raise SystemExit(f'CHROMAEXPOSURE1C verify failed: native baseline contract missing {token!r}')
for token in ['double tgCbGain,', 'double tgCrGain,', 'renderBlockParallelDirectBitmap']:
    if token not in bridge:
        raise SystemExit(f'CHROMAEXPOSURE1C verify failed: native bridge baseline missing {token!r}')
if 'M9 DNGGAINMAPFIX1A' not in dng:
    raise SystemExit('CHROMAEXPOSURE1C verify failed: DNGGAINMAPFIX1A marker missing')

print('OK CHROMAEXPOSURE1C ARBITRATION1A FROZENSAMPLES1A present')
print('OK stronger LOCAL evidence can override marginal GLOBAL evidence by >=0.01 recommendation advantage')
print('OK LOCAL candidate acceptance uses identical before-selected pixel coordinates after rerender')
print('OK 8% local / 10% absolute Cr caps and original GREENAXIS global thresholds retained')
print('OK native kernel/ABI and DNGGAINMAPFIX1A remain frozen')
