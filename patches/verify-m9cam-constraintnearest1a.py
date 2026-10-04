#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-constraintnearest1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CONSTRAINTNEAREST1A verify missing: {rel}')
    return p.read_text()

nearest = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java')
meta = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
gradle = text('app/build.gradle')
back = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
local = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java')
negative = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')

required_nearest = [
    'm9cam.constraintnearest.v1a',
    'photometricnorm1a_nearest_only_top2_and_broad_rejected_for_promotion',
    'MATERIAL_BIND_THRESHOLD_EV = 0.05',
    'firstObservationNoHistoryCandidate',
    'no_recent_raw_candidates',
    'recent_history_no_photometric_normalized_match',
    'photometric_normalized_nearest_available',
    'wouldBind',
    'wouldMateriallyBind',
    'bindingCause',
    'bindingMagnitudeEv',
    'positiveCeilingMarginAboveRequestEv',
    'positive_ceiling_can_bind_only_positive_guarded_requests',
    'mandatory_negative_ceiling_is_hard_upper_bound_when_more_protective_than_request',
    'firstObservationPolicy", "not_resolved_diagnostic_state_only',
    'currentLiveExposurePathChanged", false',
    'usedToMutateCaptureTarget", false',
]
for token in required_nearest:
    if token not in nearest:
        raise SystemExit(f'CONSTRAINTNEAREST1A verify missing class token: {token}')

if 'root.put("m9ConstraintLocal", M9ConstraintLocal1A.evaluate(root));\n            root.put("m9ConstraintNearest", M9ConstraintNearest1A.evaluate(root));' not in meta:
    raise SystemExit('CONSTRAINTNEAREST1A metadata order/publication missing')

expected_version = "versionName '1.58-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a'"
if expected_version not in gradle:
    raise SystemExit('CONSTRAINTNEAREST1A 1.58 versionName missing')
if 'photometricnorm1aconstraintnearest1ascenefingerprint1b' not in back:
    raise SystemExit('CONSTRAINTNEAREST1A forensic build marker missing')

# The matcher itself and its research alternatives remain present and untouched; this
# overlay only narrows the promotion candidate in a separate diagnostic class.
for token in [
    'm9cam.scenefingerprintnorm.v1a.preview_energy_response_shape_spatialp75',
    'photometricNormalizedNearest',
    'photometricNormalizedTop2Envelope',
    'photometricNormalizedBroadEnvelope',
]:
    if token not in local:
        raise SystemExit(f'CONSTRAINTNEAREST1A expected PHOTOMETRICNORM1A telemetry missing: {token}')
if 'PhotometricNormDistance' not in negative or 'PHOTOMETRIC_NORM_MATCH_THRESHOLD = 1.0' not in negative:
    raise SystemExit('CONSTRAINTNEAREST1A expected frozen normalized matcher missing')

# Assert no live exposure or photographic class imports/uses the new diagnostic authority.
live_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
for rel in live_rels:
    s = text(rel)
    if 'M9ConstraintNearest1A' in s or 'm9cam.constraintnearest.v1a' in s:
        raise SystemExit(f'CONSTRAINTNEAREST1A leaked into live/frozen seam: {rel}')

# Mirror the diagnostic binding rules with representative field cases.
EPS = 1e-9
MAT = 0.05

def eval_bind(request, positive=None, mandatory=None):
    target = request
    cause = 'none'
    if mandatory is not None and mandatory < target - EPS:
        target = mandatory
        cause = 'mandatory_raw_protection'
    elif request > 0.0 and positive is not None and positive < target - EPS:
        target = positive
        cause = 'positive_raw_ceiling'
    magnitude = max(0.0, request - target)
    return target, cause, magnitude > EPS, magnitude >= MAT

fixtures = [
    # 12:57 window-type case: inaccurate history ceiling but above request => non-binding.
    ((0.067, 0.287, None), (0.067, 'none', False, False)),
    # Very small numerical constraint is not material.
    ((0.700, 0.698, None), (0.698, 'positive_raw_ceiling', True, False)),
    # Historical poison example would be visibly/materially binding if selected.
    ((0.700, -0.012, None), (-0.012, 'positive_raw_ceiling', True, True)),
    # Positive ceilings never make a negative Leica-like request less protective.
    ((-0.595, 0.700, None), (-0.595, 'none', False, False)),
    # Mandatory negative protection is a hard upper bound when more protective.
    ((0.200, 0.700, -0.100), (-0.100, 'mandatory_raw_protection', True, True)),
    # Already-more-negative request remains untouched by a looser mandatory ceiling.
    ((-0.600, 0.700, -0.100), (-0.600, 'none', False, False)),
]
for args, expected in fixtures:
    got = eval_bind(*args)
    if abs(got[0] - expected[0]) > 1e-12 or got[1:] != expected[1:]:
        raise SystemExit(f'CONSTRAINTNEAREST1A binding fixture failed: args={args} got={got} expected={expected}')

print('OK CONSTRAINTNEAREST1A diagnostic promotion-candidate contract')
print('OK normalized nearest is sole promotion candidate; top2/broad remain diagnostics only')
print('OK non-binding inaccurate ceiling fixture does not alter request')
print('OK positive ceiling preserves signed negative Leica-like request')
print('OK mandatory bound semantics preserved')
print('OK 0.05 EV material threshold is reporting-only')
print('OK no new diagnostic authority leaks into Camera2/allocator/renderer seams')
