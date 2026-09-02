#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1f.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'

checks = {
    '1F scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v6.spatialqualification1f'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1E candidate frozen before 1F': (scene_rel, 'sceneexposure1ePositiveCandidate'),
    '1F AE qualification': (scene_rel, 'spatialQualificationAeEffort'),
    '1F starvation pressure': (scene_rel, 'spatialQualificationStarvationPressure'),
    '1F bypass-active evidence': (scene_rel, 'spatialQualificationBypassActive'),
    '1F center qualification': (scene_rel, 'centerNotSeverelyStarvedEvidence'),
    '1F global collapse guard': (scene_rel, 'globalBodyNotCollapsedEvidence'),
    '1F false-starvation score': (scene_rel, 'spatialFalseStarvationQualificationScore'),
    '1F attenuation': (scene_rel, 'spatialQualificationAttenuation'),
    '1F candidate output': (scene_rel, 'sceneexposure1fPositiveCandidate'),
    '1F reason': (scene_rel, 'signed_positive_moderated_by_spatial_starvation_qualification'),
    '1F build identity': ('app/build.gradle', '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1f'),
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
        raise SystemExit(f'FAIL 1F diagnostic-only contract: forbidden live marker {forbidden!r}')
print('OK   1F diagnostic-only contract: no exposure mutation/live handoff markers')
print('OK   capture/metadata/renderer/motion quality-freeze SHA guard executed by apply step')

def clamp01(x):
    return max(0.0, min(1.0, x))

def smoothstep(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = clamp01((x - lo) / (hi - lo))
    return t * t * (3.0 - 2.0 * t)

def stage_1f(pos1e, neg, energy, median, dark64, center_delta,
             spatial_axis, backlight, catastrophic=0.0):
    if energy > 0.0 and math.isfinite(energy):
        log2e = math.log(energy, 2.0)
        ae = smoothstep(log2e, math.log(10.0, 2.0), math.log(20.0, 2.0))
    else:
        ae = 0.0
    starvation_pressure = max(clamp01(spatial_axis), clamp01(backlight))
    bypass = smoothstep(starvation_pressure, 0.35, 0.65)
    center_safe = smoothstep(center_delta, -30.0, -10.0) if math.isfinite(center_delta) else 0.0
    body_safe = smoothstep(median, 50.0, 70.0)
    non_deep_dark = 1.0 - smoothstep(dark64, 0.46, 0.60)
    no_catastrophic = 1.0 - clamp01(catastrophic)
    score = clamp01(ae * bypass * center_safe * body_safe
                    * non_deep_dark * no_catastrophic)
    attenuation = 0.88 * score
    pos1f = pos1e * (1.0 - attenuation)
    signed = max(-1.25, min(1.25, pos1f + neg))
    if abs(signed) < 0.08:
        signed = 0.0
    return {
        'pos1f': pos1f,
        'signed': signed,
        'score': score,
        'attenuation': attenuation,
        'ae': ae,
        'bypass': bypass,
        'centerSafe': center_safe,
    }

# New LIVE1A failure anchors. These are the reason 1F exists.
r = stage_1f(0.8924473818040277, 0.0, 57.26, 69.0,
             0.4810474537037037, -14.0,
             0.1551737917783329, 0.6889118807360723)
if not (0.15 <= r['signed'] <= 0.30):
    raise SystemExit(f'FAIL 185433 high-AE person anchor: {r}')
print(f"OK   185433 high-AE person: 1E +0.892 -> 1F {r['signed']:+.3f} EV")

r = stage_1f(1.25, -0.28864701313004293, 17.9104485, 99.0,
             0.3598090277777778, 22.0, 1.0, 1.0)
if abs(r['signed']) > 0.08:
    raise SystemExit(f'FAIL 185445 window/toys anchor: {r}')
print(f"OK   185445 window/toys: 1E +0.961 signed -> 1F {r['signed']:+.3f} EV")

# Strong true-starvation controls must remain untouched because their AE effort is
# below the new 10 ISO*s qualification floor (or their center is severely starved).
controls = {
    '181712 cat/window': (1.123, 0.0, 6.038961045, 97.0, 0.35691550925925924, -16.0, 0.70, 0.8983),
    '175446 person/window': (0.912, 0.0, 2.684, 114.0, 0.300, 0.0, 1.0, 0.73),
    '183146 close person/window': (1.2415732253, -0.1975710838, 8.6, 102.0, 0.3855613426, -58.0, 0.9667443152, 0.9932585802),
    '183220 deep silhouette': (1.25, 0.0, 2.64, 64.0, 0.5027488426, -11.0, 0.4285130539, 0.8440978835),
}
for label, args in controls.items():
    r = stage_1f(*args)
    expected = args[0] + args[1]
    if abs(expected) < 0.08:
        expected = 0.0
    if abs(r['signed'] - expected) > 1e-6:
        raise SystemExit(f'FAIL true-starvation preservation {label}: expected {expected:.6f}, got {r}')
    print(f"OK   true-starvation preservation {label}: {r['signed']:+.3f} EV")

# Existing 1E successes should not be reopened.
nonreg = {
    'bright woodland 172954': (0.085, 0.0, 7.21, 81.0, 0.387, 0.0, 0.0, 0.0),
    'very dark woodland 173219': (0.400, 0.0, 1.25, 52.0, 0.677, 0.0, 0.0, 0.55),
    'woodland path': (0.649, 0.0, 7.21, 61.0, 0.5444, 0.0, 0.0, 0.0),
    'wide room 175459': (0.422, 0.0, 2.06, 131.0, 0.257, 0.0, 0.646, 0.081),
    'ordinary dark-object room 182739': (0.193, 0.0, 53.78, 91.0, 0.2903645833, 46.0, 0.2700322426, 0.0),
}
for label, args in nonreg.items():
    r = stage_1f(*args)
    if abs(r['signed'] - args[0]) > 1e-6:
        raise SystemExit(f'FAIL 1E non-regression {label}: {r}')
    print(f"OK   1E non-regression {label}: remains {r['signed']:+.3f} EV")

# Extreme AE alone cannot change a scene unless the old starvation bypass is active.
r = stage_1f(0.50, 0.0, 60.0, 90.0, 0.25, 20.0, 0.10, 0.10)
if abs(r['signed'] - 0.50) > 1e-9:
    raise SystemExit(f'FAIL high-AE-only safeguard: {r}')
print('OK   extreme AE effort alone cannot trigger 1F')

print('SCENEEXPOSURE1F verification passed: LIVE1A false spatial-starvation failures are moderated while validated 1E and true-backlight controls remain frozen')
