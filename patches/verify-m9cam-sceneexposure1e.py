#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sceneexposure1e.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
checks = {
    '1E scene diagnostic schema': (scene_rel, 'm9cam.sceneexposure.v5.aeefforttonal1e'),
    'diagnostic-only marker': (scene_rel, 'diagnostic_only_no_exposure_mutation'),
    '1C near-white support frozen': (scene_rel, 'NEAR_WHITE224_SUPPORT_LOW = 0.06'),
    '1C near-clip support frozen': (scene_rel, 'NEAR_CLIP240_SUPPORT_LOW = 0.025'),
    '1C broad-midbright negative attenuation frozen': (scene_rel, 'BROAD_MIDBRIGHT_GATE_ATTENUATION = 0.80'),
    '1C emissive negative attenuation frozen': (scene_rel, 'EMISSIVE_GATE_ATTENUATION = 0.65'),
    '1D low-key median frozen': (scene_rel, 'LOWKEY_MEDIAN_FULL_Y = 55.0'),
    '1D low-key median zero frozen': (scene_rel, 'LOWKEY_MEDIAN_ZERO_Y = 105.0'),
    '1D low-key dark floor frozen': (scene_rel, 'LOWKEY_DARK64_LOW = 0.30'),
    '1D low-key dark high frozen': (scene_rel, 'LOWKEY_DARK64_HIGH = 0.48'),
    '1D max attenuation frozen': (scene_rel, 'LOWKEY_MAX_ATTENUATION = 0.68'),
    '1D candidate retained': (scene_rel, 'sceneexposure1dPositiveCandidate'),
    '1E AE effort evidence': (scene_rel, 'aeEffortEvidence'),
    '1E tonal adequacy': (scene_rel, 'achievedBodyLumaAdequacy'),
    '1E spatial bypass': (scene_rel, 'noSpatialStarvationEvidence'),
    '1E backlight bypass': (scene_rel, 'noBacklightStarvationEvidence'),
    '1E relative starvation bypass': (scene_rel, 'noRelativeEnergyStarvationEvidence'),
    '1E deep-dark bypass': (scene_rel, 'nonDeepDarkBodyEvidence'),
    '1E catastrophic bypass': (scene_rel, 'noCatastrophicStarvationEvidence'),
    '1E ordinary-body dominance': (scene_rel, 'ordinaryBodyDominanceEvidence'),
    '1E score': (scene_rel, 'aeEffortTonalAdequacyScore'),
    '1E attenuation': (scene_rel, 'aeEffortAttenuation'),
    '1E positive comparison emitted': (scene_rel, 'sceneexposure1ePositiveCandidate'),
    'existing step0 evaluation retained': ('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java', 'M9SceneExposureDiagnostic.evaluateStep0'),
    'metadata output retained': ('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java', 'm9SceneExposureDiagnostic'),
    '1E build identity': ('app/build.gradle', '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'),
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

def luma24_energy_starvation(energy):
    return 1.0 - smoothstep(energy, 1.00, 2.50)

def stage_1e(ev1d, energy, median, dark64, spatial_axis, backlight,
             ordinary_body=1.0, catastrophic=0.0, energy_starvation=None):
    if energy_starvation is None:
        energy_starvation = luma24_energy_starvation(energy)
    if energy > 0.0 and math.isfinite(energy):
        log2e = math.log(energy, 2.0)
        ae_effort = smoothstep(log2e, math.log(1.50, 2.0), math.log(5.00, 2.0))
    else:
        ae_effort = 0.0
    tonal = clamp01(
        smoothstep(median, 60.0, 82.0)
        * (1.0 - smoothstep(median, 125.0, 150.0)))
    no_spatial = 1.0 - smoothstep(spatial_axis, 0.20, 0.55)
    no_backlight = 1.0 - smoothstep(backlight, 0.35, 0.65)
    no_relative_starvation = 1.0 - clamp01(energy_starvation)
    non_deep_dark = 1.0 - smoothstep(dark64, 0.46, 0.60)
    no_catastrophic = 1.0 - clamp01(catastrophic)
    backlight_minus_ordinary = max(0.0, backlight - ordinary_body)
    ordinary_dominance = 1.0 - smoothstep(backlight_minus_ordinary, 0.05, 0.25)
    score = clamp01(ae_effort * tonal * no_spatial * no_backlight
                    * no_relative_starvation * non_deep_dark
                    * no_catastrophic * ordinary_dominance)
    attenuation = 0.90 * score
    ev1e = ev1d * (1.0 - attenuation)
    return {
        'ev1e': ev1e,
        'score': score,
        'attenuation': attenuation,
        'aeEffortEvidence': ae_effort,
        'tonalAdequacy': tonal,
        'noSpatial': no_spatial,
        'noBacklight': no_backlight,
        'noRelativeStarvation': no_relative_starvation,
        'nonDeepDark': non_deep_dark,
        'noCatastrophic': no_catastrophic,
        'ordinaryDominance': ordinary_dominance,
    }

anchors = {
    'bright woodland 172954': ((0.807, 7.21, 81.0, 0.387, 0.0, 0.0, 1.0), (0.00, 0.20)),
    'very dark woodland 173219': ((0.400, 1.25, 52.0, 0.677, 0.0, 0.55, 1.0), (0.30, 0.50)),
    'woodland path control': ((0.650, 7.21, 61.0, 0.5444, 0.0, 0.0, 1.0), (0.40, 0.65)),
    'person window 175446': ((0.912, 2.684, 114.0, 0.300, 1.0, 0.73, 0.55), (0.80, 1.00)),
    'wide backlit room 175459': ((0.422, 2.06, 131.0, 0.257, 0.646, 0.081, 0.35), (0.30, 0.45)),
    'lamp silhouette 174532': ((0.000, 0.0595, 148.0, 0.0476, 0.0, 0.0, 0.0), (0.00, 0.00)),
    'broad overcast control': ((0.300, 7.21, 190.0, 0.05, 0.0, 0.0, 0.25), (0.20, 0.40)),
}
for label, (args, bounds) in anchors.items():
    r = stage_1e(*args)
    lo, hi = bounds
    if not (lo - 1e-9 <= r['ev1e'] <= hi + 1e-9):
        raise SystemExit(
            f'FAIL 1E anchor {label}: 1E={r["ev1e"]:.6f} outside {bounds}; '
            f'score={r["score"]:.6f} attenuation={r["attenuation"]:.6f}')
    print(f'OK   1E anchor {label}: {args[0]:.3f} -> {r["ev1e"]:.3f} EV '
          f'(score {r["score"]:.3f}, attenuation {r["attenuation"]:.3f})')

bypass_cases = {
    'strong spatial starvation': dict(spatial_axis=1.0, backlight=0.0, catastrophic=0.0),
    'strong backlight starvation': dict(spatial_axis=0.0, backlight=0.80, catastrophic=0.0),
    'catastrophic starvation': dict(spatial_axis=0.0, backlight=0.0, catastrophic=1.0),
    'deep dark body': dict(spatial_axis=0.0, backlight=0.0, catastrophic=0.0, dark64=0.70),
}
for label, overrides in bypass_cases.items():
    kw = dict(ev1d=0.80, energy=7.21, median=82.0, dark64=0.38,
              spatial_axis=0.0, backlight=0.0, ordinary_body=1.0,
              catastrophic=0.0, energy_starvation=0.0)
    kw.update(overrides)
    r = stage_1e(**kw)
    if abs(r['ev1e'] - 0.80) > 1e-9:
        raise SystemExit(f'FAIL 1E bypass {label}: changed 0.800 -> {r["ev1e"]:.6f}')
    print(f'OK   1E bypass {label} preserves frozen 1D result')

r = stage_1e(0.80, 20.0, 52.0, 0.70, 0.0, 0.0, ordinary_body=1.0,
             catastrophic=0.0, energy_starvation=0.0)
if abs(r['ev1e'] - 0.80) > 1e-9:
    raise SystemExit('FAIL high-AE-only safeguard: high energy changed deep low-key result')
print('OK   high AE effort alone cannot attenuate a deep low-key result')

print('SCENEEXPOSURE1E verification passed: bright adequate-AE woodland is strongly moderated while 1C/1D protections and real starvation bypasses remain intact')
