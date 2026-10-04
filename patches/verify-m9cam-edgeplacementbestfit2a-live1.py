#!/usr/bin/env python3
from pathlib import Path
import math
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-edgeplacementbestfit2a-live1.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('BESTFIT2A LIVE1 verify missing: ' + rel)
    return p.read_text()

def must(rel, token):
    if token not in text(rel):
        raise SystemExit(f'BESTFIT2A LIVE1 verify missing {token!r} in {rel}')

def must_not(rel, token):
    if token in text(rel):
        raise SystemExit(f'BESTFIT2A LIVE1 verify forbidden {token!r} in {rel}')

renderer = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9EdgePlacementBestFit2AController.java'
store = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java'
luma = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java'
image_saver = 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
queue = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java'

# Capture-specific immutable bridge.
for token in [
    'BESTFIT2A_RENDER_SNAPSHOT_BRIDGE',
    'MAX_RENDER_SNAPSHOTS = 32',
    'bytes.clone()',
    'consumeRenderSnapshotForDng',
    'RENDER_SNAPSHOTS.remove',
]:
    must(store, token)

# Exact research branch constants / asymmetry.
for token in [
    'm9cam.edgeplacementbestfit.v2a.live1',
    'A_INTENT_MIN_EV = 0.10',
    'A_UL_SHIFT_MIN_EV = 1.50',
    'A_P75_MAX_Y = 30.0',
    'A_INTEGRAL_SHIFT_MAX_EV = 0.15',
    'B_SCENE_SPREAD_MIN_EV = 1.30',
    'B_BRIGHT_REGION_MIN = 0.20',
    'B_P75_MAX_Y = 15.0',
    'B_GRID_MEAN_MAX_Y = 30.0',
    'B_RETENTION_MAX_EV = -1.50',
    'B_MIN_COLLAPSED = 3',
    'C_UL_SHIFT_MIN_EV = 1.20',
    'C_LOWER_MAX_Y = 18.0',
    'C_UPPER_MIN_Y = 140.0',
    'C_P75_MIN_Y = 120.0',
    'C_CENTER_RETENTION_MIN_EV = -1.00',
    'BRIGHT_SCORE_MIN = 0.60',
    'BRIGHT_GAIN_MIN = 1.50',
    'BRIGHT_FINISHED_MEDIAN_MIN_Y = 75.0',
    'LOCAL_Q95_MIN_Y = 220.0',
    'LOCAL_MINUS_GLOBAL_Q95_MIN_Y = 80.0',
    'DARK_Q95_CEILING_Y = 242.0',
    'DARK_BRIGHT224_DELTA_MAX = 0.040',
    'BRIGHT_PIVOT = 0.85',
    'BRIGHT_MILD_STRENGTH = 0.15',
    'new double[] {0.50, 0.35, 0.25, 0.15}',
    'new double[] {0.25, 0.15}',
    'zero_intent_collapse_vetoed_by_local_subject_survival',
    'coherent_lowkey_plus_actual_broad_opening',
    '(4899 * r + 9617 * g + 1868 * b) >> 14',
]:
    must(controller, token)

# Renderer integration: frozen first, treatment after direct rendered-luma evidence.
for token in [
    'BESTFIT2A_LIVE1 capture-specific immutable evidence bridge',
    'consumeRenderSnapshotForDng(dngPath)',
    'renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0)',
    'M9EdgePlacementBestFit2AController.evaluate',
    'DARK_EXACT_RERENDER_GAIN_OFFSET',
    'BRIGHT_RGB_PIVOT',
    'M9EdgePlacementBestFit2AController.acceptDarkCandidate',
    'M9EdgePlacementBestFit2AController.applyBrightPivot',
    'directRenderedLumaFrozen',
    'edgePlacementBestFit2A',
    'double edgePlacementGainEv',
    'effectiveRenderGain = meter.gain * Math.pow(2.0, edgePlacementGainEv)',
    'edgePlacementRenderGainEv',
    'edgePlacementEffectiveGain',
]:
    must(renderer, token)

# Exactly three native colour invocations must use the bounded effective render gain.
r = text(renderer)
if r.count('effectiveRenderGain, tgCbGain') != 3:
    raise SystemExit('BESTFIT2A LIVE1 verify expected exactly 3 effectiveRenderGain native call sites')
if r.count('meter.gain, tgCbGain') != 0:
    raise SystemExit('BESTFIT2A LIVE1 verify found stale native render call using baseline meter.gain')

# Existing finished-bitmap diagnostic remains attached, now serving selection and final-output truth.
must(luma, 'M9EdgePlacementGate1ADiagnostic.measure(bitmap)')
must(renderer, 'M9RenderedLumaDiagnostic.measure(bitmap)')

# Frozen photographic/capture invariants.
for token in [
    'public static final int JPEG_QUALITY = 95;',
    'private static final double METER_TARGET = 0.107 * (8192.0 / 10000.0);',
    'private static final double HSM_H = 0.25;',
    'private static final double TG_NEG_CB_COMPRESSION = 0.25;',
    'private static final double TG_NEG_CR_COMPRESSION = 0.16;',
    'public static final int SATURATION_BANK = 3;',
    'curve02 normal-ISO sRGB Standard',
]:
    must(renderer, token)

must(image_saver, 'img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream);')
must(queue, 'ImageSaver.Util.saveSingleRaw(')
must('app/build.gradle', '-metadatafix1a-edgeplacementgate1a-bestfit2alive1')

# Controller must never reach capture/allocator/native seams.
for rel in [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/cpp/m9color_jni.cpp',
]:
    must_not(rel, 'BESTFIT2A')
    must_not(rel, 'M9EdgePlacementBestFit2AController')

# Numeric sanity of the fixed prospective bright treatment.
def q14_y(r, g, b):
    return (4899*r + 9617*g + 1868*b) >> 14

def scale_for_y(y, strength=0.15, pivot=0.85):
    yn = y / 255.0
    w = max(0.0, min(1.0, 1.0 - yn/pivot))
    return 2.0 ** (-strength*w)

if q14_y(255,255,255) != 254:
    raise SystemExit('BESTFIT2A LIVE1 Q14 BT601 sanity failed')
if not (scale_for_y(0) < 1.0 and abs(scale_for_y(255)-1.0) < 1e-12):
    raise SystemExit('BESTFIT2A LIVE1 RGB pivot endpoint sanity failed')
if not math.isclose(math.log2(82/66), 0.3131576356, rel_tol=1e-6):
    raise SystemExit('BESTFIT2A LIVE1 prospective 181559 median-shift sanity failed')
if not math.isclose(math.log2(161/141), 0.1913712411, rel_tol=1e-6):
    raise SystemExit('BESTFIT2A LIVE1 prospective 181559 q95-shift sanity failed')

print('M9Cam EDGEPLACEMENTBESTFIT2A LIVE1 verifier PASS')
print(' - immutable capture-specific evidence bridge present and bounded')
print(' - DARK A/B max +0.50, DARK C max +0.25, local-subject veto retained')
print(' - dark candidates are exact full rerenders with baseline TC20 decision + bounded gain offset')
print(' - dark highlight budget q95<=242 and bright224 delta<=0.040 retained')
print(' - BRIGHT LOWKEY+BROAD uses exact RGB-pivot 0.85 / strength 0.15 only')
print(' - DNG, capture exposure, TC20 baseline, native colour equations and JPEG Q95 frozen')
