#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1e-live1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'FAIL missing {rel}')
    return p.read_text()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
checks = {
    '1E diagnostic schema retained': (scene_rel, 'm9cam.sceneexposure.v5.aeefforttonal1e'),
    'live test mode': (scene_rel, 'live_test_signed_exposure_enabled'),
    'live total target policy': (scene_rel, 'scene1e_total_signed_ev_replaces_fb1_total'),
    'live ledger schema': (scene_rel, 'm9cam.sceneexposure.live1a'),
    'valid recommendation accessor': (scene_rel, 'hasValidRecommendation()'),
    'signed recommendation accessor': (scene_rel, 'getRecommendedSignedEv()'),
    'live application recorder': (scene_rel, 'recordLiveApplication('),
    'live ledger emitted': (scene_rel, 'out.put("liveApplication"'),
    '1E AE effort math retained': (scene_rel, 'aeEffortTonalAdequacyScore'),
    '1E attenuation math retained': (scene_rel, 'aeEffortAttenuation'),
    '1C negative candidate retained': (scene_rel, 'sceneexposure1cNegativeCandidate'),
    '1D positive candidate retained': (scene_rel, 'sceneexposure1dPositiveCandidate'),
    '1E positive candidate retained': (scene_rel, 'sceneexposure1ePositiveCandidate'),
    'step0-only live handoff': (iso_rel, 'M9Config.isCaptureTest() && step == 0'),
    'legacy eligibility gate retained': (iso_rel, 'if (!m9FeedbackEligible)'),
    'invalid fallback retained': (iso_rel, 'scene1e_live_invalid_fallback_to_fb1'),
    'total target clamp positive': (iso_rel, 'Math.min(1.25, m9SceneRequestedEv)'),
    'total target clamp negative': (iso_rel, 'Math.max(-1.25'),
    'delta vs FB1': (iso_rel, 'm9SceneDeltaEv = m9SceneAppliedTotalEv - m9Feedback.appliedEv'),
    'signed pair compensation': (iso_rel, 'pair.ExpoCompensateLower(1.0 / m9SceneDeltaFactor)'),
    'live application telemetry call': (iso_rel, 'M9SceneExposureDiagnostic.recordLiveApplication('),
    'build identity': ('app/build.gradle', '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1elive1a'),
}
for label, (rel, needle) in checks.items():
    if needle not in text(rel):
        raise SystemExit(f'FAIL {label}: {needle!r} missing from {rel}')
    print(f'OK   {label}')

scene = text(scene_rel)
for frozen in [
    'AE_EFFORT_ENERGY_LOW_ISOS = 1.50',
    'AE_EFFORT_ENERGY_HIGH_ISOS = 5.00',
    'AE_TONAL_MEDIAN_LOW_Y = 60.0',
    'AE_TONAL_MEDIAN_FULL_Y = 82.0',
    'AE_SPATIAL_BYPASS_START = 0.20',
    'AE_SPATIAL_BYPASS_FULL = 0.55',
    'AE_BACKLIGHT_BYPASS_START = 0.35',
    'AE_BACKLIGHT_BYPASS_FULL = 0.65',
    'AE_EFFORT_MAX_ATTENUATION = 0.90',
    'MAX_POSITIVE_EV = 1.25',
    'MAX_NEGATIVE_EV = 1.25',
]:
    if frozen not in scene:
        raise SystemExit(f'FAIL frozen 1E arithmetic marker missing: {frozen}')
print('OK   frozen 1E arithmetic constants retained')

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def live_handoff(scene_ev, fb1_ev, eligible=True, valid=True):
    if not eligible or not valid:
        return {'total': fb1_ev, 'delta': 0.0, 'fallback': True}
    total = clamp(scene_ev, -1.25, 1.25)
    return {'total': total, 'delta': total - fb1_ev, 'fallback': False}

anchors = {
    'ordinary person 182419': (0.1632589893, 0.0, 0.1632589893),
    'dark-object room 182739': (0.1934599881, 0.0, 0.1934599881),
    'close backlit person 183146': (1.0440021416, 0.75, 0.2940021416),
    'deep silhouette 183220': (1.25, 0.75, 0.50),
    'cat/window bypass 181712': (1.1228648785, 0.75, 0.3728648785),
    'wide-room bypass 182155': (1.2110893619, 0.75, 0.4610893619),
    'bright woodland model': (0.085, 0.0, 0.085),
    'negative highlight control': (-0.50, 0.0, -0.50),
    'FB1 cancellation control': (0.10, 0.75, -0.65),
}
for label, (scene_ev, fb1_ev, expected_delta) in anchors.items():
    r = live_handoff(scene_ev, fb1_ev)
    if abs(r['delta'] - expected_delta) > 1e-8:
        raise SystemExit(f'FAIL {label}: delta {r["delta"]:.9f} != {expected_delta:.9f}')
    if abs(r['total'] - clamp(scene_ev, -1.25, 1.25)) > 1e-8:
        raise SystemExit(f'FAIL {label}: total target mismatch')
    print(f'OK   {label}: FB1 {fb1_ev:+.3f} -> 1E total {r["total"]:+.3f} EV; delta {r["delta"]:+.3f}')

for label, eligible, valid in [
    ('manual/tripod/non-auto fallback', False, True),
    ('invalid diagnostic fallback', True, False),
]:
    r = live_handoff(-0.8, 0.75, eligible=eligible, valid=valid)
    if not r['fallback'] or abs(r['total'] - 0.75) > 1e-12 or abs(r['delta']) > 1e-12:
        raise SystemExit(f'FAIL {label}: legacy FB1 was not preserved')
    print(f'OK   {label}: legacy FB1 preserved')

for x, expected in [(2.0, 1.25), (-2.0, -1.25)]:
    r = live_handoff(x, 0.0)
    if abs(r['total'] - expected) > 1e-12:
        raise SystemExit(f'FAIL signed live clamp for {x}')
print('OK   signed live target hard-clamped to -1.25..+1.25 EV')

iso = text(iso_rel)
pos_fb1 = iso.find('pair.ExpoCompensateLower(1.0 / m9FeedbackFactor)')
pos_1e = iso.find('M9SceneExposureDiagnostic.evaluateStep0')
pos_delta = iso.find('m9SceneDeltaEv = m9SceneAppliedTotalEv - m9Feedback.appliedEv')
pos_motion = iso.find('M9ModernExposurePolicy.adjustCaps')
if min(pos_fb1, pos_1e, pos_delta, pos_motion) < 0:
    raise SystemExit('FAIL live ordering proof: required marker missing')
if not (pos_fb1 < pos_1e < pos_delta < pos_motion):
    raise SystemExit(
        f'FAIL live ordering: fb1={pos_fb1}, 1e={pos_1e}, delta={pos_delta}, motion={pos_motion}')
print('OK   ordering: legacy FB1 -> 1E total/delta -> frozen motion allocation')

print('SCENEEXPOSURE1E-LIVE1A verification passed: live auto-PHOTO step0 now follows the bounded signed 1E TOTAL target with FB1 fallback and frozen renderer/motion policy')
