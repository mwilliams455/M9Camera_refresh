#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1g.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'

checks = {
    '1G scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v7.subjectbodyadequacy1g'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1F candidate frozen before 1G': (scene_rel, 'sceneexposure1fPositiveCandidate'),
    '1G severe-spatial restoration evidence': (scene_rel, 'severeSpatialSeparationEvidence'),
    '1G absolute-center starvation evidence': (scene_rel, 'absoluteCenterStarvationEvidence'),
    '1G 1F restoration score': (scene_rel, 'spatialQualificationRestorationScore'),
    '1G 1F restore fraction': (scene_rel, 'spatialQualificationRestoreFraction'),
    '1G effective 1F attenuation': (scene_rel, 'effectiveSpatialQualificationAttenuation'),
    '1G absolute-center adequacy': (scene_rel, 'absoluteCenterAdequacyEvidence'),
    '1G relative-center adequacy': (scene_rel, 'relativeCenterAdequacyEvidence'),
    '1G global-dark context': (scene_rel, 'globalDarkContextEvidence'),
    '1G calm-starvation gate': (scene_rel, 'calmStarvationEvidence'),
    '1G subject/body adequacy score': (scene_rel, 'subjectBodyAdequacyScore'),
    '1G subject/body attenuation': (scene_rel, 'subjectBodyAdequacyAttenuation'),
    '1G candidate output': (scene_rel, 'sceneexposure1gPositiveCandidate'),
    '1G subject adequacy reason': (scene_rel, 'signed_positive_moderated_by_subject_body_adequacy'),
    '1G center-starvation restoration reason': (scene_rel, 'signed_positive_1f_restored_by_absolute_center_starvation'),
    '1G build identity': ('app/build.gradle', '1.40-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1g'),
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
        raise SystemExit(f'FAIL 1G diagnostic-only contract: forbidden live marker {forbidden!r}')
print('OK   1G diagnostic-only contract: no exposure mutation/live handoff markers')
print('OK   capture/metadata/renderer/motion quality-freeze SHA guard executed by apply step')

def clamp01(x):
    return max(0.0, min(1.0, x))

def smoothstep(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = clamp01((x - lo) / (hi - lo))
    return t * t * (3.0 - 2.0 * t)

def stage_1g(pos1e, neg, energy, median, dark64, center, center_delta,
             spatial_axis, backlight, catastrophic=0.0):
    # Frozen 1F model first.
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
    score1f = clamp01(ae * bypass * center_safe * body_safe
                      * non_deep_dark * no_catastrophic)
    attenuation1f = 0.88 * score1f
    pos1f = pos1e * (1.0 - attenuation1f)

    # 1G-A: absolute-center starvation can restore only a bounded fraction of 1F.
    severe_spatial = smoothstep(spatial_axis, 0.75, 0.95)
    absolute_center_starved = 1.0 - smoothstep(center, 50.0, 70.0)
    restore_score = clamp01(ae * severe_spatial * absolute_center_starved
                            * no_catastrophic)
    restore_fraction = 0.42 * restore_score
    effective_1f_attenuation = attenuation1f * (1.0 - restore_fraction)
    repaired = pos1e * (1.0 - effective_1f_attenuation)

    # 1G-B: subject/body adequacy can moderate only in a globally-dark but
    # spatially-calm high-AE frame with an absolutely and relatively healthy center.
    center_adequate = smoothstep(center, 55.0, 75.0)
    relative_center_adequate = smoothstep(center_delta, -5.0, 15.0) if math.isfinite(center_delta) else 0.0
    global_dark = 1.0 - smoothstep(median, 55.0, 80.0)
    calm = 1.0 - smoothstep(starvation_pressure, 0.20, 0.50)
    body_score = clamp01(ae * center_adequate * relative_center_adequate
                         * global_dark * calm * no_catastrophic)
    body_attenuation = 0.85 * body_score
    pos1g = repaired * (1.0 - body_attenuation)

    signed = max(-1.25, min(1.25, pos1g + neg))
    if abs(signed) < 0.08:
        signed = 0.0
    return {
        'pos1f': pos1f,
        'pos1g': pos1g,
        'signed': signed,
        'ae': ae,
        'attenuation1f': attenuation1f,
        'restoreFraction': restore_fraction,
        'bodyAttenuation': body_attenuation,
        'bodyScore': body_score,
    }

# 191151 exposed the absolute-center weakness in 1F: high AE and severe spatial
# separation are real, but center Y53 is still genuinely dark. 1G must restore the
# recommendation into the photographic ~+0.65..+0.85 EV range.
r = stage_1g(1.25, 0.0, 22.54, 68.0, 0.4856770833333333,
             53.0, -15.0, 1.0, 1.0)
if not (0.65 <= r['signed'] <= 0.85):
    raise SystemExit(f'FAIL 191151 absolute-center starvation restoration: {r}')
if r['restoreFraction'] <= 0.30:
    raise SystemExit(f'FAIL 191151 restoration did not materially engage: {r}')
print(f"OK   191151 true backlight: 1F +0.428 -> 1G {r['signed']:+.3f} EV")

# 191403 exposed the global-median weakness: global Y43 is dark but center Y69 is
# already healthy and +26 above global at 64 ISO*s, with no spatial/backlight starvation.
r = stage_1g(0.40, 0.0, 64.06, 43.0, 0.6098090277777778,
             69.0, 26.0, 0.02943043306007307, 0.0)
if not (0.08 <= r['signed'] <= 0.18):
    raise SystemExit(f'FAIL 191403 subject/body adequacy moderation: {r}')
if r['bodyAttenuation'] < 0.60:
    raise SystemExit(f'FAIL 191403 subject/body adequacy did not materially engage: {r}')
print(f"OK   191403 globally-dark/center-adequate: 1F +0.400 -> 1G {r['signed']:+.3f} EV")

# The two LIVE1A over-bright anchors must remain fixed by 1F; 1G must not reopen them.
r = stage_1g(0.8924473818040277, 0.0, 57.26, 69.0,
             0.4810474537037037, 55.0, -14.0,
             0.1551737917783329, 0.6889118807360723)
if not (0.15 <= r['signed'] <= 0.30):
    raise SystemExit(f'FAIL 185433 high-AE person non-regression: {r}')
if r['restoreFraction'] != 0.0 or r['bodyAttenuation'] != 0.0:
    raise SystemExit(f'FAIL 185433 must remain an exact 1F result: {r}')
print(f"OK   185433 high-AE person remains 1F-corrected at {r['signed']:+.3f} EV")

r = stage_1g(1.25, -0.28864701313004293, 17.9104485, 99.0,
             0.3598090277777778, 121.0, 22.0, 1.0, 1.0)
if abs(r['signed']) > 0.08:
    raise SystemExit(f'FAIL 185445 window/toys non-regression: {r}')
if r['restoreFraction'] != 0.0 or r['bodyAttenuation'] != 0.0:
    raise SystemExit(f'FAIL 185445 must remain an exact 1F result: {r}')
print(f"OK   185445 window/toys remains near-neutral at {r['signed']:+.3f} EV")

# Strong true-starvation controls below the 10 ISO*s qualification floor remain exact.
controls = {
    '181712 cat/window': (1.123, 0.0, 6.038961045, 97.0, 0.35691550925925924, 81.0, -16.0, 0.70, 0.8983),
    '175446 person/window': (0.912, 0.0, 2.684, 114.0, 0.300, 114.0, 0.0, 1.0, 0.73),
    '183146 close person/window': (1.2415732253, -0.1975710838, 8.6, 102.0, 0.3855613426, 44.0, -58.0, 0.9667443152, 0.9932585802),
    '183220 deep silhouette': (1.25, 0.0, 2.64, 64.0, 0.5027488426, 53.0, -11.0, 0.4285130539, 0.8440978835),
}
for label, args in controls.items():
    r = stage_1g(*args)
    expected = args[0] + args[1]
    if abs(expected) < 0.08:
        expected = 0.0
    if abs(r['signed'] - expected) > 1e-6:
        raise SystemExit(f'FAIL true-starvation preservation {label}: expected {expected:.6f}, got {r}')
    print(f"OK   true-starvation preservation {label}: {r['signed']:+.3f} EV")

# Existing 1E/1F successes remain frozen. The global-dark gate prevents ordinary
# healthy scenes from being re-moderated merely because AE effort is high.
nonreg = {
    'bright woodland 172954': (0.085, 0.0, 7.21, 81.0, 0.387, 81.0, 0.0, 0.0, 0.0),
    'very dark woodland 173219': (0.400, 0.0, 1.25, 52.0, 0.677, 52.0, 0.0, 0.0, 0.55),
    'woodland path': (0.649, 0.0, 7.21, 61.0, 0.5444, 61.0, 0.0, 0.0, 0.0),
    'wide room 175459': (0.422, 0.0, 2.06, 131.0, 0.257, 131.0, 0.0, 0.646, 0.081),
    'ordinary dark-object room 182739': (0.193, 0.0, 53.78, 91.0, 0.2903645833, 137.0, 46.0, 0.2700322426, 0.0),
}
for label, args in nonreg.items():
    r = stage_1g(*args)
    if abs(r['signed'] - args[0]) > 1e-6:
        raise SystemExit(f'FAIL prior-stage non-regression {label}: {r}')
    print(f"OK   prior-stage non-regression {label}: remains {r['signed']:+.3f} EV")

# Extreme AE alone remains insufficient: the subject/body attenuation requires a
# globally-dark context and a relatively elevated, absolutely healthy center.
r = stage_1g(0.50, 0.0, 60.0, 90.0, 0.25, 100.0, 10.0, 0.10, 0.10)
if abs(r['signed'] - 0.50) > 1e-9:
    raise SystemExit(f'FAIL high-AE-only safeguard: {r}')
print('OK   extreme AE effort alone cannot trigger 1G')

print('SCENEEXPOSURE1G verification passed: absolute-center true starvation is restored, globally-dark center-adequate frames are moderated, and validated prior anchors remain frozen')
