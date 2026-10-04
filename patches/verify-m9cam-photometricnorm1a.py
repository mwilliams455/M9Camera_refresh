#!/usr/bin/env python3
from pathlib import Path
import math
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-photometricnorm1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'PHOTOMETRICNORM1A verify missing: {rel}')
    return p.read_text()


def require(haystack, needle, label):
    if needle not in haystack:
        raise SystemExit(f'PHOTOMETRICNORM1A verify failed: {label}')
    print('OK  ', label)

negative = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
local = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java')
gradle = text('app/build.gradle')
back = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
policy = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
isoexpo = text('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
guard = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java')
constraint_ref = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java')
virtual = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java')

require(negative, 'PHOTOMETRIC_NORM_RESPONSE_SCALE_EV = 1.15', 'response EV scale')
require(negative, 'PHOTOMETRIC_NORM_SPATIAL_P75_SCALE_EV = 1.15', 'spatial p75 EV scale')
require(negative, 'PHOTOMETRIC_NORM_SHAPE_SCALE_EV = 0.75', 'shape EV scale')
require(negative, 'PHOTOMETRIC_NORM_MATCH_THRESHOLD = 1.0', 'normalized match threshold')
require(negative, 'responseDeltaEv(', 'preview-energy-normalized response helper')
require(negative, 'ratioDeltaEv(', 'exposure-invariant shape helper')
require(negative, 'java.util.Arrays.sort(tileDeltaEv);', 'robust ordered tile response')
require(negative, 'double spatialP75 = tileDeltaEv[6];', '75th percentile of nine tiles')
require(negative, 'photometricNormalizedDistance', 'candidate normalized score')
require(negative, 'photometricNormalizedResponseDistanceEv', 'candidate response component')
require(negative, 'photometricNormalizedSpatialP75DistanceEv', 'candidate spatial component')
require(negative, 'photometricNormalizedShapeDistanceEv', 'candidate shape component')
require(negative, 'passesPhotometricNormalizedThreshold', 'candidate normalized pass flag')
require(negative, 'constraintLocal1A', 'existing CONSTRAINTLOCAL candidate block retained')
require(negative, 'SIMILAR_SCENE_DISTANCE = 1.0', 'legacy FP1B threshold frozen')
require(negative, 'MAX_FEEDBACK_AGE_MS = 60_000L', 'legacy 60s history frozen')
require(local, 'm9cam.constraintlocal.v1a', 'CONSTRAINTLOCAL schema frozen')
require(local, 'm9cam.scenefingerprintnorm.v1a.preview_energy_response_shape_spatialp75',
        'normalized matcher schema')
require(local, 'diagnostic_only_no_association_mutation', 'normalized matcher diagnostic-only')
require(local, 'dark_bright_threshold_fractions_and_starvation_are_exposure_state_dependent',
        'exposure-state identity terms explicitly excluded')
require(local, 'photometricNormalizedNearest', 'normalized nearest policy')
require(local, 'photometricNormalizedTop2Envelope', 'normalized top2 policy')
require(local, 'photometricNormalizedBroadEnvelope', 'normalized broad policy')
require(local, 'photometricNormalizedPassCompletedSequences', 'normalized pass identities')
require(local, 'research_only_20260904_bulb_cat_window_sequence_not_frozen_photographic_truth',
        'corpus calibration explicitly provisional')
require(guard, 'private static final double MAX_FOREGROUND_BUMP_EV = 0.50;',
        'FOREGROUNDGUARD cap frozen')
require(constraint_ref, 'm9cam.constraintref.v1', 'CONSTRAINTREF frozen')
require(virtual, 'PROVISIONAL_REFERENCE_Y = 120.0', 'VIRTUALBV Y120 frozen')
require(gradle,
        "versionName '1.57-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a'",
        '1.57 build identity')
require(back,
        'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1aphotometricnorm1ascenefingerprint1b',
        'forensic marker')

for name, body in [('renderer', renderer), ('exposure policy', policy), ('IsoExpoSelector', isoexpo)]:
    if 'photometricNormalized' in body or 'PHOTOMETRIC_NORM' in body or 'scenefingerprintnorm' in body:
        raise SystemExit(f'PHOTOMETRICNORM1A verify failed: {name} consumes normalized matcher')
print('OK   no live exposure/render seam consumes normalized matcher')

# Field fixture reconstructed from 2026-09-04 CONSTRAINTLOCAL1A sequence.
# This verifies the exact proposed research metric before another field build.
TILES = ['tl','tc','tr','ml','mc','mr','bl','bc','br']
FIX = {
    'bulbA': dict(e=.0412153, med=163, cen=176, q95=183, q99=255, midq=255,
                  tiles=[85,83,148,177,176,177,72,174,44]),
    'bulbB': dict(e=.0259568, med=148, cen=149, q95=173, q99=255, midq=255,
                  tiles=[55,55,61,157,150,159,161,164,162]),
    'catA': dict(e=.0469916, med=77, cen=81, q95=207, q99=237, midq=194,
                 tiles=[189,172,93,148,56,113,50,56,48]),
    'catB': dict(e=.0565076, med=100, cen=94, q95=204, q99=232, midq=195,
                 tiles=[188,110,65,125,66,134,50,86,54]),
    'catC': dict(e=.0493504, med=98, cen=98, q95=204, q99=231, midq=189,
                 tiles=[190,166,48,120,72,136,43,70,53]),
    'windowB': dict(e=.0265733, med=123, cen=160, q95=232, q99=247, midq=220,
                    tiles=[155,146,153,145,177,171,13,12,82]),
    'windowC': dict(e=.0228267, med=116, cen=155, q95=230, q99=246, midq=204,
                    tiles=[150,148,143,138,159,157,16,15,89]),
    'catE': dict(e=.102608, med=135, cen=124, q95=246, q99=255, midq=194,
                 tiles=[213,197,152,86,97,130,103,110,116]),
}

def evratio(a, ea, b, eb):
    return abs(math.log2((a/ea)/(b/eb)))

def ratiod(a, da, b, db):
    return abs(math.log2((a/da)/(b/db)))

def score(a, b):
    x, y = FIX[a], FIX[b]
    response = max(
        evratio(x['med'],x['e'],y['med'],y['e']),
        evratio(x['cen'],x['e'],y['cen'],y['e']),
        evratio(x['q95'],x['e'],y['q95'],y['e']),
        evratio(x['midq'],x['e'],y['midq'],y['e']))
    shape = max(
        ratiod(x['cen'],x['med'],y['cen'],y['med']),
        ratiod(x['q95'],x['med'],y['q95'],y['med']),
        ratiod(x['midq'],x['med'],y['midq'],y['med']),
        ratiod(x['q99'],x['med'],y['q99'],y['med']))
    tile = sorted(evratio(x['tiles'][i],x['e'],y['tiles'][i],y['e']) for i in range(9))[6]
    s = max(response/1.15, tile/1.15, shape/.75)
    return s, response, tile, shape

checks = [
    ('same bulb survives preview exposure shift', 'bulbA', 'bulbB', True, 0.5801),
    ('same cat repeat', 'catA', 'catB', True, 0.5438),
    ('cat to window transition rejected', 'catC', 'windowB', False, 1.4359),
    ('same kitchen window repeat', 'windowB', 'windowC', True, 0.2934),
    ('cat returns after window and reconnects', 'catE', 'catB', True, 0.7548),
    ('returned cat does not match recent window', 'catE', 'windowC', False, 2.1655),
]
for label, a, b, expected_pass, expected in checks:
    s, response, spatial, shape = score(a,b)
    if abs(s-expected) > 0.015:
        raise SystemExit(f'PHOTOMETRICNORM1A fixture drift {label}: {s:.4f} vs {expected:.4f}')
    passed = s <= 1.0
    if passed != expected_pass:
        raise SystemExit(f'PHOTOMETRICNORM1A fixture classification failed {label}: score={s:.4f}')
    print(f'FIXTURE {label}: score={s:.3f} response={response:.3f} spatialP75={spatial:.3f} shape={shape:.3f} pass={passed}')

print('PHOTOMETRICNORM1A verification passed')
print(' - same bulb is recovered despite FP1B raw spatial distance about 1.97')
print(' - cat/window scene transitions remain rejected in the motivating field sequence')
print(' - returned cat can reconnect to prior cat history after an unrelated window frame')
print(' - existing FP1B and all live photographic seams remain unchanged')
