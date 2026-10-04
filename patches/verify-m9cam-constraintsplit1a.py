#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-constraintsplit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'missing {rel}')
    return p.read_text()

constraint = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java')
negative = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
metadata = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
virtual = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java')
scene = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java')
coordinator = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
iso_selector = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
policy = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
gradle = read('app/build.gradle')
backlight = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')

compact_version = '1.50-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1a-cm1b'
checks = {
    'CONSTRAINTSPLIT1A schema':
        'm9cam.constraintsplit.v1.virtualbv1a_rawconstraint1a' in constraint,
    'diagnostic-only contract':
        'diagnostic_only_no_exposure_mutation' in constraint
        and 'out.put("liveEligible", false)' in constraint
        and 'out.put("usedToMutateCaptureTarget", false)' in constraint,
    'JPEG excluded as capture input':
        'out.put("jpegBrightnessUsedForCapture", false)' in constraint,
    'positive allowance is ceiling':
        'Math.min(meterRequestEv, positiveAllowanceEv)' in constraint,
    'positive headroom permission not command':
        'positive_headroom_is_permission_not_command' in constraint,
    'negative override uses frozen SIGNEDCAL gate':
        'negativeGatePass' in constraint
        and 'negativeCandidateAppliedByFrozenGateEv' in constraint,
    'no q998-only protection heuristic':
        'rawUq99_8' not in constraint and 'q998' not in constraint,
    'capture top-level publication':
        'root.put("m9ConstraintSplit", M9ConstraintSplit1A.evaluateCapture(root));' in metadata,
    'same-frame oracle publication':
        'out.put("m9ConstraintSplitOracle", M9ConstraintSplit1A.evaluateOracle(' in negative,
    'capture sequence correlation':
        'noteCaptureConstraint' in negative and 'captureSequence' in constraint,
    'matched and oracle comparison':
        'matchedVsOracleConstraintDeltaEv' in constraint
        and 'matchedVsOracleDirectionAgreement' in constraint,
    'positive allowance exposed without math change':
        'out.put("additionalCaptureHeadroomEv", additionalCaptureHeadroomEv);' in negative,
    'stale FP1A text cleaned':
        'sceneAssociationFrozen", "SCENEFINGERPRINT1B"' in negative
        and 'sceneAssociationFrozen", "SCENEFINGERPRINT1A"' not in negative,
    'VIRTUALBV1A weights frozen':
        'PROVISIONAL_CENTER_WEIGHT = 0.70' in virtual
        and 'PROVISIONAL_GLOBAL_WEIGHT = 0.30' in virtual
        and 'PROVISIONAL_REFERENCE_Y = 120.0' in virtual
        and 'PROVISIONAL_BV_CALIBRATION_OFFSET_EV = 0.0' in virtual,
    'SIGNEDCAL1A formula frozen':
        'double positiveCandidateEv = additionalCaptureHeadroomEv' in negative
        and 'double negativeCandidateBeforeGateEv = -0.35 * meaningfulClipRiskEvidence' in negative
        and 'meaningfulClipRiskEvidence > 0.45' in negative
        and 'shadowStarvation < 0.55' in negative,
    'SCENEFINGERPRINT1B frozen':
        'private static final double SIMILAR_SCENE_DISTANCE = 1.0;' in negative
        and 'private static final long MAX_FEEDBACK_AGE_MS = 60_000L;' in negative
        and 'Math.abs(a[i] - b[i]) / 60.0' in negative,
    'SCENEEXPOSURE1H frozen':
        'm9cam.sceneexposure.v8.renderaware1h' in scene,
    'coordinator V5 remains frozen':
        'm9cam.exposuresplit.v5.capturemeter1b.m9negative1c.scenefingerprint1b.signedcal1a'
        in coordinator,
    'no live seam consumes constraint':
        'M9ConstraintSplit1A' not in iso_selector
        and 'M9ConstraintSplit1A' not in renderer
        and 'M9ConstraintSplit1A' not in policy
        and 'm9ConstraintSplit' not in coordinator,
    'compact Android version':
        ("versionName '" + compact_version + "'") in gradle and len(compact_version) < 96,
    'forensic identity':
        'virtualbv1aconstraintsplit1ascenefingerprint1b' in backlight,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('CONSTRAINTSPLIT1A structural self-check failed: ' + ', '.join(failed))

def constrain(meter, allowance=None, protection=0.0, raw=True):
    if not raw:
        return meter, 'no_raw'
    if protection < 0.0 and meter > 0.0:
        return protection, 'override'
    if meter > 0.0 and allowance is not None:
        return min(meter, allowance), 'limit'
    return meter, 'preserve'

fixtures = [
    ('positive_limited', 0.80, 0.30, 0.0, True, 0.30),
    ('positive_negative_override', 0.45, 0.08, -0.327, True, -0.327),
    ('negative_preserved_with_headroom', -0.25, 0.50, 0.0, True, -0.25),
    ('neutral_preserved', 0.0, 0.50, 0.0, True, 0.0),
    ('no_matched_raw', 0.42, None, 0.0, False, 0.42),
]
for name, meter, allowance, protection, raw, expected in fixtures:
    got, reason = constrain(meter, allowance, protection, raw)
    print(f'CS1A {name}: meter={meter:+.3f} result={got:+.3f} reason={reason}')
    if not math.isclose(got, expected, rel_tol=0.0, abs_tol=1e-12):
        raise SystemExit(f'CONSTRAINTSPLIT1A regression failed: {name}')

print('CONSTRAINTSPLIT1A verification passed')

