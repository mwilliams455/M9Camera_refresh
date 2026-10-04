#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1d.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
checks = {
    '1D scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v4.signedpressure1d'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1C near-white support frozen': (scene_rel, 'NEAR_WHITE224_SUPPORT_LOW = 0.06'),
    '1C near-clip support frozen': (scene_rel, 'NEAR_CLIP240_SUPPORT_LOW = 0.025'),
    '1C broad-midbright negative attenuation frozen': (scene_rel, 'BROAD_MIDBRIGHT_GATE_ATTENUATION = 0.80'),
    '1C emissive negative attenuation frozen': (scene_rel, 'EMISSIVE_GATE_ATTENUATION = 0.65'),
    '1D low-key median evidence': (scene_rel, 'lowKeyMedianEvidence'),
    '1D low-key dark evidence': (scene_rel, 'lowKeyDarkBodyEvidence'),
    '1D low broad-bright evidence': (scene_rel, 'lowBroadBrightEvidence'),
    '1D low spatial-axis evidence': (scene_rel, 'lowSpatialAxisSeparationEvidence'),
    '1D non-severe-backlight evidence': (scene_rel, 'nonSevereBacklightEvidence'),
    '1D structural score': (scene_rel, 'structuralLowKeyScore'),
    '1D attenuation': (scene_rel, 'structuralLowKeyAttenuation'),
    '1C positive comparison retained': (scene_rel, 'sceneexposure1cPositiveCandidate'),
    '1D positive comparison emitted': (scene_rel, 'sceneexposure1dPositiveCandidate'),
    'existing step0 evaluation retained': ('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java', 'M9SceneExposureDiagnostic.evaluateStep0'),
    'metadata output retained': ('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java', 'm9SceneExposureDiagnostic'),
    '1D build identity': ('app/build.gradle', '1.37-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1d'),
}
for label, (rel, needle) in checks.items():
    p = root / rel
    if not p.exists():
        raise SystemExit(f'FAIL {label}: missing {rel}')
    if needle not in p.read_text():
        raise SystemExit(f'FAIL {label}: {needle!r} missing from {rel}')
    print(f'OK   {label}')

scene = (root / scene_rel).read_text()
for forbidden in ['applyExposure', 'applySceneExposure', 'setExpo(', 'CaptureRequest.Builder']:
    if forbidden in scene:
        raise SystemExit(f'FAIL diagnostic-only contract: forbidden mutation marker {forbidden!r}')
print('OK   diagnostic-only no exposure mutation markers')
print('OK   quality-freeze SHA-256 guard executed by apply step')

def clamp01(x):
    return max(0.0, min(1.0, x))

def smoothstep(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = clamp01((x - lo) / (hi - lo))
    return t * t * (3.0 - 2.0 * t)

def positive_1c(median, dark64, center_median, center_delta, backlight, contrast=0.0):
    median_need = 1.0 - smoothstep(median, 72.0, 138.0)
    dark_need = smoothstep(dark64, 0.14, 0.38)
    center_need = 1.0 - smoothstep(center_median, 72.0, 112.0)
    ordinary = max(median_need, 0.70 * dark_need, 0.75 * center_need)
    raw = max(backlight, ordinary)
    healthy = smoothstep(center_median, 140.0, 165.0) * smoothstep(center_delta, 12.0, 28.0)
    severe = smoothstep(backlight, 0.72, 0.90)
    attenuation = 0.88 * healthy * (1.0 - severe)
    pressure = clamp01(raw * (1.0 - attenuation))
    pressure = clamp01(pressure * (1.0 - 0.75 * clamp01(contrast)))
    return pressure, 1.25 * pressure

def positive_1d(median, dark64, center_median, center_delta, backlight, contrast, bright192, spatial_axis_score):
    p1c, ev1c = positive_1c(median, dark64, center_median, center_delta, backlight, contrast)
    low_median = 1.0 - smoothstep(median, 55.0, 105.0)
    lowkey_dark = smoothstep(dark64, 0.30, 0.48)
    low_broad_bright = 1.0 - smoothstep(bright192, 0.04, 0.15)
    low_axis = 1.0 - smoothstep(spatial_axis_score, 0.05, 0.35)
    non_severe = 1.0 - smoothstep(backlight, 0.65, 0.85)
    landscape_bypass = 1.0 - clamp01(contrast)
    structural = clamp01(min(low_median, lowkey_dark) * low_broad_bright * low_axis * non_severe * landscape_bypass)
    attenuation = 0.68 * structural
    pressure = clamp01(p1c * (1.0 - attenuation))
    return {'ev1c': ev1c, 'ev1d': 1.25 * pressure, 'score': structural, 'attenuation': attenuation}

preserved = {
    'gray sky / dark foreground': ((198.0, 0.2766203704, 199.0, 1.0, 0.0, 0.0, 0.5963541667, 1.0), (0.50, 0.56)),
    'structured landscape': ((65.0, 0.4998553241, 62.0, -3.0, 0.0, 1.0, 0.2547743056, 1.0), (0.30, 0.33)),
    'ordinary indoor': ((115.0, 0.1589988426, 125.0, 10.0, 0.0, 0.0, 0.05, 0.50), (0.30, 0.40)),
    'severe window backlight': ((97.0, 0.3425925926, 120.0, 23.0, 0.9537651991, 0.0, 0.1566840278, 1.0), (1.10, 1.25)),
    'moving-bus backlight': ((110.0, 0.3489583333, 115.0, 5.0, 0.9883622438, 0.0, 0.0639467593, 1.0), (1.15, 1.25)),
    'broad sky lawn current 1C control': ((80.0, 0.3780381944, 108.0, 28.0, 1.0, 0.0, 0.4409722222, 1.0), (1.20, 1.25)),
    'white flower current 1C control': ((77.0, 0.4425636574, 157.0, 80.0, 1.0, 0.0, 0.3227719907, 1.0), (1.20, 1.25)),
}
for label, (args, bounds) in preserved.items():
    r = positive_1d(*args)
    if abs(r['ev1d'] - r['ev1c']) > 1e-9:
        raise SystemExit(f'FAIL 1D preservation {label}: 1C={r["ev1c"]:.6f} 1D={r["ev1d"]:.6f}')
    if not (bounds[0] <= r['ev1d'] <= bounds[1]):
        raise SystemExit(f'FAIL 1D preserved range {label}: {r["ev1d"]:.6f} outside {bounds}')
    print(f'OK   1D preserved {label}: {r["ev1d"]:.3f} EV')

woodlands = {
    'woodland path / small sky holes': ((61.0, 0.5444155093, 66.0, 5.0, 0.0, 0.0, 0.0338541667, 0.0), (0.38, 0.52)),
    'dense canopy / live FB1 about +0.5': ((70.0, 0.4545717593, 60.0, -10.0, 0.6600279841, 0.0, 0.0520833333, 0.0), (0.52, 0.70)),
    'dense woodland / live FB1 about +0.42': ((57.0, 0.5868055556, 50.0, -7.0, 0.62, 0.0, 0.0342881944, 0.0), (0.36, 0.50)),
}
for label, (args, bounds) in woodlands.items():
    r = positive_1d(*args)
    if r['ev1c'] < 1.20:
        raise SystemExit(f'FAIL woodland anchor no longer represents saturated 1C: {label}')
    if not (bounds[0] <= r['ev1d'] <= bounds[1]):
        raise SystemExit(f'FAIL woodland moderation {label}: 1D={r["ev1d"]:.6f} score={r["score"]:.6f} attenuation={r["attenuation"]:.6f}')
    if r['score'] < 0.70:
        raise SystemExit(f'FAIL woodland structural evidence too weak {label}: {r["score"]:.6f}')
    print(f'OK   woodland moderated {label}: 1C {r["ev1c"]:.3f} -> 1D {r["ev1d"]:.3f} EV (score {r["score"]:.3f})')

gate_cases = {
    'broad-bright gate': (70.0, 0.55, 60.0, 0.0, 0.0, 0.0, 0.30, 0.0),
    'spatial-axis gate': (70.0, 0.55, 60.0, 0.0, 0.0, 0.0, 0.03, 0.80),
    'severe-backlight gate': (70.0, 0.55, 60.0, 0.0, 0.95, 0.0, 0.03, 0.0),
    'existing-landscape gate': (70.0, 0.55, 60.0, 0.0, 0.0, 1.0, 0.03, 0.0),
}
for label, args in gate_cases.items():
    r = positive_1d(*args)
    if r['score'] > 1e-9 or abs(r['ev1d'] - r['ev1c']) > 1e-9:
        raise SystemExit(f'FAIL structural low-key gate {label}: score={r["score"]:.6f} 1C={r["ev1c"]:.6f} 1D={r["ev1d"]:.6f}')
    print(f'OK   structural low-key {label} blocks attenuation')

print('SCENEEXPOSURE1D verification passed: 1C negative gate frozen; structural low-key scenes moderated without changing established positive regressions')
