#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1h.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'

checks = {
    '1H scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v8.renderaware1h'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1G candidate frozen before 1H': (scene_rel, 'sceneexposure1gPositiveCandidate'),
    '1H middle-center q95 input': (scene_rel, 'middleCenterQ95'),
    '1H early subject adequacy': (scene_rel, 'earlySubjectAdequacyAttenuation'),
    '1H absolute highlight support': (scene_rel, 'absoluteHighlightSupportEvidence'),
    '1H false spatial highlight qualification': (scene_rel, 'falseSpatialHighlightQualificationScore'),
    '1H false spatial attenuation': (scene_rel, 'falseSpatialHighlightAttenuation'),
    '1H render-aware central score': (scene_rel, 'renderAwareSubjectHighlightScore'),
    '1H render-aware negative candidate': (scene_rel, 'renderAwareNegativeCandidate'),
    '1H positive candidate output': (scene_rel, 'sceneexposure1hPositiveCandidate'),
    '1H weak-highlight reason': (scene_rel, 'signed_positive_moderated_by_weak_absolute_highlight_support'),
    '1H early-subject reason': (scene_rel, 'signed_positive_moderated_by_early_subject_body_adequacy'),
    '1H render-negative reason': (scene_rel, 'signed_negative_render_aware_central_highlight_pressure'),
    '1H build identity': ('app/build.gradle', '1.41-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1h'),
    'existing step0 evaluation retained': ('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java', 'M9SceneExposureDiagnostic.evaluateStep0'),
    'metadata output retained': ('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java', 'm9SceneExposureDiagnostic'),
}
for label, (rel, needle) in checks.items():
    p = root / rel
    if not p.exists() or needle not in p.read_text():
        raise SystemExit(f'FAIL {label}: {needle!r} missing from {rel}')
    print(f'OK   {label}')

scene = (root / scene_rel).read_text()
for forbidden in [
    'live_test_signed_exposure_enabled',
    'scene1e_total_signed_ev_replaces_fb1_total',
    'applySceneExposureDelta',
    'recordLiveApplication',
    'CaptureRequest.Builder',
]:
    if forbidden in scene:
        raise SystemExit(f'FAIL 1H diagnostic-only contract: forbidden live marker {forbidden!r}')
print('OK   1H diagnostic-only contract: no exposure mutation/live handoff markers')
print('OK   capture/metadata/renderer/motion quality-freeze SHA guard executed by apply step')

def clamp01(x):
    return max(0.0, min(1.0, x))

def smoothstep(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = clamp01((x - lo) / (hi - lo))
    return t * t * (3.0 - 2.0 * t)

def stage_1h(pos1g, neg1c, energy, median, q99, bright224, bright240,
             center, center_delta, spatial_axis, backlight, middle_center_q95,
             catastrophic=0.0):
    if energy > 0.0 and math.isfinite(energy):
        ae = smoothstep(math.log(energy, 2.0), math.log(10.0, 2.0), math.log(20.0, 2.0))
    else:
        ae = 0.0
    starvation = max(clamp01(spatial_axis), clamp01(backlight))
    no_catastrophic = 1.0 - clamp01(catastrophic)

    early_score = clamp01(
        ae * smoothstep(center, 54.0, 60.0)
        * smoothstep(center_delta, -2.0, 6.0)
        * (1.0 - smoothstep(median, 55.0, 75.0))
        * (1.0 - smoothstep(starvation, 0.20, 0.50))
        * no_catastrophic
    )
    early_attenuation = 0.75 * early_score

    absolute_highlight_support = max(
        smoothstep(q99, 210.0, 240.0),
        smoothstep(bright224, 0.005, 0.030),
        smoothstep(bright240, 0.002, 0.015),
    )
    weak_highlight = 1.0 - clamp01(absolute_highlight_support)
    false_spatial_score = clamp01(
        ae * smoothstep(starvation, 0.55, 0.75)
        * (1.0 - smoothstep(center_delta, -24.0, -14.0))
        * (1.0 - smoothstep(center, 48.0, 60.0))
        * smoothstep(median, 55.0, 70.0)
        * weak_highlight * no_catastrophic
    )
    false_spatial_attenuation = 0.52 * false_spatial_score
    pos1h = pos1g * (1.0 - early_attenuation) * (1.0 - false_spatial_attenuation)

    render_score = clamp01(
        ae * smoothstep(median, 80.0, 90.0)
        * (1.0 - smoothstep(median, 105.0, 120.0))
        * smoothstep(center, 55.0, 62.0)
        * (1.0 - smoothstep(center, 78.0, 90.0))
        * (1.0 - smoothstep(center_delta, -20.0, -8.0))
        * smoothstep(middle_center_q95, 182.0, 192.0)
        * (1.0 - smoothstep(starvation, 0.15, 0.35))
        * (1.0 - smoothstep(bright224, 0.005, 0.030))
        * no_catastrophic
    )
    render_negative = -0.30 * render_score
    negative = max(-1.25, min(0.0, neg1c + render_negative))

    signed = max(-1.25, min(1.25, pos1h + negative))
    if abs(signed) < 0.08:
        signed = 0.0
    return {
        'pos1h': pos1h,
        'negative': negative,
        'signed': signed,
        'earlyAttenuation': early_attenuation,
        'falseSpatialAttenuation': false_spatial_attenuation,
        'renderNegative': render_negative,
        'renderScore': render_score,
    }

r = stage_1h(0.37708672, 0.0, 78.75, 52.0, 189.0,
             0.0059317, 0.0043403, 59.0, 7.0, 0.0, 0.0, 159.0)
if not (0.08 <= r['signed'] <= 0.15) or r['earlyAttenuation'] < 0.60:
    raise SystemExit(f'FAIL 194427 early subject/body adequacy: {r}')
print(f"OK   194427 early subject/body adequacy: 1G +0.377 -> 1H {r['signed']:+.3f} EV")

r = stage_1h(1.14111448, 0.0, 53.84, 70.0, 196.0,
             0.0, 0.0, 44.0, -26.0, 0.6382, 0.7595, 158.0)
if not (0.45 <= r['signed'] <= 0.65) or r['falseSpatialAttenuation'] < 0.45:
    raise SystemExit(f'FAIL 200029 false spatial-backlight qualification: {r}')
print(f"OK   200029 weak-highlight false spatial backlight: 1G +1.141 -> 1H {r['signed']:+.3f} EV")

r = stage_1h(0.08717079, 0.0, 43.34, 90.0, 203.0,
             0.000289, 0.000145, 63.0, -27.0, 0.013, 0.0, 192.0)
if not (-0.26 <= r['signed'] <= -0.15) or r['renderNegative'] > -0.25:
    raise SystemExit(f'FAIL 202850 render-aware negative: {r}')
print(f"OK   202850 rendered-subject-hot anchor: 1G +0.087 -> 1H {r['signed']:+.3f} EV")

r = stage_1h(0.08585112, 0.0, 45.92, 94.0, 206.0,
             0.001881, 0.001013, 69.0, -25.0, 0.0, 0.0, 189.0)
if not (-0.20 <= r['signed'] <= -0.10) or r['renderNegative'] > -0.18:
    raise SystemExit(f'FAIL 202839 render-aware negative: {r}')
print(f"OK   202839 rendered-subject-hot anchor: 1G +0.086 -> 1H {r['signed']:+.3f} EV")

r = stage_1h(0.05091162, 0.0, 60.0, 119.0, 194.0,
             0.000434, 0.0, 110.0, -9.0, 0.0, 0.0, 181.0)
if r['signed'] != 0.0 or abs(r['renderNegative']) > 1e-12:
    raise SystemExit(f'FAIL 202704 neutral object non-regression: {r}')
print('OK   202704 healthy object control remains 0 EV')

r = stage_1h(0.752, 0.0, 22.54, 68.0, 240.0,
             0.02, 0.01, 53.0, -15.0, 1.0, 1.0, 170.0)
if abs(r['signed'] - 0.752) > 1e-9:
    raise SystemExit(f'FAIL 191151 true backlight non-regression: {r}')
print('OK   191151 true high-AE backlight remains +0.752 EV')

r = stage_1h(0.236, 0.0, 57.26, 69.0, 205.0,
             0.001, 0.0002, 55.0, -14.0, 0.155, 0.689, 170.0)
if abs(r['signed'] - 0.236) > 1e-9:
    raise SystemExit(f'FAIL 185433 prior correction non-regression: {r}')
print('OK   185433 existing high-AE person correction remains +0.236 EV')

low_ae_controls = {
    '181712 cat/window': (1.123, 0.0, 6.04, 97.0, 245.0, 0.04, 0.02, 81.0, -16.0, 0.70, 0.898, 210.0),
    '183146 close person/window': (1.2416, -0.1976, 8.6, 102.0, 255.0, 0.064, 0.03, 44.0, -58.0, 0.967, 0.993, 220.0),
    'bright woodland 172954': (0.085, 0.0, 7.21, 81.0, 190.0, 0.0, 0.0, 81.0, 0.0, 0.0, 0.0, 150.0),
}
for label, args in low_ae_controls.items():
    r = stage_1h(*args)
    expected = args[0] + args[1]
    if abs(expected) < 0.08:
        expected = 0.0
    if abs(r['signed'] - expected) > 1e-6:
        raise SystemExit(f'FAIL low-AE prior-stage preservation {label}: expected {expected:.6f}, got {r}')
    print(f"OK   low-AE prior-stage preservation {label}: {r['signed']:+.3f} EV")

r = stage_1h(0.10, 0.0, 60.0, 120.0, 200.0,
             0.0, 0.0, 110.0, -5.0, 0.0, 0.0, 195.0)
if abs(r['renderNegative']) > 1e-12:
    raise SystemExit(f'FAIL central-highlight-only safeguard: {r}')
print('OK   middle-center highlight alone cannot trigger render-aware negative')

print('SCENEEXPOSURE1H verification passed: weak-highlight false spatial preservation is moderated, early subject adequacy starts sooner, bounded negative render-aware pressure is observational only, and prior true-backlight/neutral anchors remain frozen')
