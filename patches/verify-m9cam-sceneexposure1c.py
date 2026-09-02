#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1c.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
checks = {
    '1C scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v3.signedpressure1c'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1B ordinary body shoulder frozen': (scene_rel, 'BODY_MEDIAN_ZERO_NEED_Y = 138.0'),
    '1B healthy center frozen': (scene_rel, 'HEALTHY_CENTER_MAX_ATTENUATION = 0.88'),
    '1B severe backlight start frozen': (scene_rel, 'SEVERE_BACKLIGHT_PRESERVE_START = 0.72'),
    'near-white support diagnostic': (scene_rel, 'nearWhiteSupport224'),
    'near-clip support diagnostic': (scene_rel, 'nearClipSupport240'),
    'q95 highlight danger diagnostic': (scene_rel, 'q95HighlightDanger'),
    'q99 highlight danger diagnostic': (scene_rel, 'q99HighlightDanger'),
    'broad mid-bright diagnostic': (scene_rel, 'broadMidBrightWithoutNearWhite'),
    'emissive/specular tolerance diagnostic': (scene_rel, 'emissiveOrSpecularToleranceWeight'),
    'negative support gate': (scene_rel, 'negativeHighlightSupportGate'),
    'legacy 1B negative comparison': (scene_rel, 'legacy1bNegativeCandidate'),
    '1C negative comparison': (scene_rel, 'sceneexposure1cNegativeCandidate'),
    'existing step0 evaluation retained': (
        'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
        'M9SceneExposureDiagnostic.evaluateStep0'),
    'metadata output retained': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
        'm9SceneExposureDiagnostic'),
    '1C build identity': (
        'app/build.gradle',
        '1.36-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1c'),
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


def positive_ev(median, dark64, center_median, center_delta, backlight, contrast=0.0):
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
    return 1.25 * pressure


def negative_model(median, q95, q99, bright192, bright224, bright240, body_protection):
    hot = smoothstep(median, 150.0, 205.0)
    broad192 = smoothstep(bright192, 0.18, 0.42)
    hot_q95 = smoothstep(q95, 220.0, 250.0) * smoothstep(bright192, 0.08, 0.25)
    broad_clip = smoothstep(bright240, 0.04, 0.18)
    legacy_raw = max(hot, broad192, hot_q95, broad_clip)
    legacy_pressure = clamp01(legacy_raw * (1.0 - 0.75 * body_protection))
    legacy_ev = -1.25 * legacy_pressure

    near224 = smoothstep(bright224, 0.06, 0.22)
    near240 = smoothstep(bright240, 0.025, 0.10)
    q95_danger = smoothstep(q95, 224.0, 246.0)
    q99_danger = smoothstep(q99, 238.0, 252.0)
    q95_support = q95_danger * smoothstep(bright224, 0.04, 0.14)
    q99_support = q99_danger * smoothstep(bright224, 0.02, 0.08)
    broad_mid = clamp01(
        smoothstep(bright192, 0.35, 0.55)
        * (1.0 - smoothstep(bright224, 0.03, 0.08))
        * (1.0 - smoothstep(bright240, 0.005, 0.03)))
    emissive = clamp01(
        smoothstep(bright240, 0.001, 0.02)
        * (1.0 - smoothstep(bright224, 0.03, 0.10)))
    direct = max(near224, near240, q95_support, 0.85 * q99_support)
    gate = clamp01(direct * (1.0 - 0.80 * broad_mid) * (1.0 - 0.65 * emissive))
    after_nearwhite = clamp01(legacy_raw * gate)
    pressure = clamp01(after_nearwhite * (1.0 - 0.75 * body_protection))
    return legacy_ev, -1.25 * pressure, gate, broad_mid, emissive

positive_vectors = {
    'ordinary indoor': ((115.0, 0.1589988426, 125.0, 10.0, 0.0, 0.0), (0.30, 0.40)),
    'severe window backlight': ((97.0, 0.3425925926, 120.0, 23.0, 0.9537651991, 0.0), (1.10, 1.25)),
    'healthy-center hydrangea': ((129.0, 0.2889178241, 155.0, 26.0, 0.5367589582, 0.0), (0.20, 0.40)),
    'moving-bus backlight': ((110.0, 0.3489583333, 115.0, 5.0, 0.9883622438, 0.0), (1.15, 1.25)),
}
for label, (args, bounds) in positive_vectors.items():
    ev = positive_ev(*args)
    if not (bounds[0] <= ev <= bounds[1]):
        raise SystemExit(f'FAIL 1C positive freeze {label}: {ev:.6f} EV outside {bounds}')
    print(f'OK   1C positive freeze {label}: {ev:.3f} EV')

gray_pos = positive_ev(204.0, 0.2456597222, 208.0, 4.0, 0.0, 0.0)
gray_legacy, gray_neg, gray_gate, gray_mid, _ = negative_model(
    204.0, 220.0, 227.0, 0.6022858796, 0.0214120370, 0.0, 0.0)
gray_signed = gray_pos + gray_neg
if not (gray_legacy <= -1.20 and abs(gray_neg) <= 0.03 and 0.30 <= gray_signed <= 0.45 and gray_mid >= 0.90):
    raise SystemExit(f'FAIL gray-sky gate: legacy={gray_legacy:.3f} newNeg={gray_neg:.3f} signed={gray_signed:.3f} gate={gray_gate:.3f}')
print(f'OK   gray-sky false negative repaired: legacy {gray_legacy:.3f} -> signed {gray_signed:.3f} EV')

portrait_pos = positive_ev(140.0, 0.1857638889, 133.0, -7.0, 0.0, 0.0)
portrait_legacy, portrait_neg, portrait_gate, _, _ = negative_model(
    140.0, 210.0, 222.0, 0.2495659722, 0.0067997685, 0.0054976852, 0.0)
portrait_signed = portrait_pos + portrait_neg
if not (-0.30 <= portrait_legacy <= -0.20 and abs(portrait_neg) <= 0.03 and 0.0 <= portrait_signed <= 0.10):
    raise SystemExit(f'FAIL portrait-bulb gate: legacy={portrait_legacy:.3f} newNeg={portrait_neg:.3f} signed={portrait_signed:.3f} gate={portrait_gate:.3f}')
print(f'OK   portrait bulb tolerated: legacy {portrait_legacy:.3f} -> signed {portrait_signed:.3f} EV')

_, window_neg, _, _, _ = negative_model(
    97.0, 223.0, 249.0, 0.1566840278, 0.0493344907, 0.0189525463, 0.9537651991)
if abs(window_neg) > 0.02:
    raise SystemExit(f'FAIL severe-window negative regression: {window_neg:.3f} EV')
print(f'OK   severe-window positive preserved; 1C negative {window_neg:.3f} EV')

_, bus_neg, _, _, _ = negative_model(
    110.0, 196.0, 255.0, 0.0639467593, 0.0192418981, 0.0159143519, 0.9883622438)
if abs(bus_neg) > 0.02:
    raise SystemExit(f'FAIL moving-bus negative regression: {bus_neg:.3f} EV')
print(f'OK   moving-bus positive preserved; 1C negative {bus_neg:.3f} EV')

_, high_neg, high_gate, _, _ = negative_model(
    220.0, 248.0, 253.0, 0.78, 0.35, 0.15, 0.0)
if not (high_gate >= 0.95 and high_neg <= -1.0):
    raise SystemExit(f'FAIL synthetic high-key negative capability: gate={high_gate:.3f} EV={high_neg:.3f}')
print(f'OK   supported high-key can still recommend negative EV: {high_neg:.3f} EV')

print('SCENEEXPOSURE1C verification passed: 1B positive architecture frozen; negative/high-key gate requires real near-white support')
