#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-constraintsplit1a-fix1.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'missing {rel}')
    return p.read_text()

constraint = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java')
negative = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
scene = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java')
coordinator = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
iso_selector = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
policy = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
gradle = read('app/build.gradle')
backlight = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')

compact_version = '1.51-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-cm1b'
checks = {
    'FIX1 schema':
        'm9cam.constraintsplit.v2.virtualbv1a_rawconstraint1b.fix1' in constraint,
    'diagnostic-only contract retained':
        'diagnostic_only_no_exposure_mutation' in constraint
        and 'out.put("liveEligible", false)' in constraint
        and 'out.put("usedToMutateCaptureTarget", false)' in constraint,
    'mandatory protection uses min bound':
        'Math.min(meterRequestEv, mandatoryProtectionEv)' in constraint,
    'positive allowance still ceiling':
        'Math.min(meterRequestEv, positiveAllowanceEv)' in constraint,
    'FP1B nearest selection still present':
        'if (d < bestDistance)' in negative
        and 'bestDistance = d;' in negative,
    'conservative FP1B envelope telemetry':
        'passingConstraintCandidateCount' in negative
        and 'conservativePositiveAllowanceEv' in negative
        and 'strongestMandatoryProtectionEv' in negative
        and 'diagnostic_all_recent_fp1b_passing_completed_raws' in negative,
    'envelope exact positive allowance equations':
        'smoothstep(raw.clip, 0.005, 0.030)' in negative
        and 'smoothstep(raw.q998, 0.72, 0.96)' in negative
        and 'log2(0.92 / Math.max(raw.q998, 1e-6))' in negative
        and '1.0 - 0.80 * meaningfulClipRiskEvidence' in negative,
    'envelope exact mandatory negative equations':
        'smoothstep(raw.q50, 0.025, 0.080)' in negative
        and 'smoothstep(raw.q25, 0.006, 0.025)' in negative
        and 'meaningfulClipRiskEvidence > 0.45' in negative
        and 'shadowStarvation < 0.55' in negative
        and '-0.35 * meaningfulClipRiskEvidence * (1.0 - shadowStarvation)' in negative,
    'nearest/envelope/oracle capture telemetry':
        'nearestRawConstrainedMeterRequestEv' in constraint
        and 'conservativeEnvelopeConstrainedMeterRequestEv' in constraint
        and 'oracleConstrainedMeterRequestEv' in constraint,
    'envelope vs oracle correlation':
        'conservativeEnvelopeVsOracleConstraintDeltaEv' in constraint
        and 'conservativeEnvelopeVsOracleDirectionAgreement' in constraint,
    'capture correlation carries envelope':
        'envelopeConstraintAvailable' in negative
        and 'envelopeConstrainedEv' in negative,
    'SCENEFINGERPRINT1B frozen':
        'private static final double SIMILAR_SCENE_DISTANCE = 1.0;' in negative
        and 'private static final long MAX_FEEDBACK_AGE_MS = 60_000L;' in negative
        and 'Math.abs(a[i] - b[i]) / 60.0' in negative,
    'SCENEEXPOSURE1H frozen':
        'm9cam.sceneexposure.v8.renderaware1h' in scene,
    'coordinator V5 frozen':
        'm9cam.exposuresplit.v5.capturemeter1b.m9negative1c.scenefingerprint1b.signedcal1a'
        in coordinator,
    'no live seam consumes FIX1':
        'M9ConstraintSplit1A' not in iso_selector
        and 'M9ConstraintSplit1A' not in renderer
        and 'M9ConstraintSplit1A' not in policy
        and 'm9ConstraintSplit' not in coordinator,
    'compact Android version':
        ("versionName '" + compact_version + "'") in gradle and len(compact_version) < 96,
    'forensic identity':
        'virtualbv1aconstraintsplit1afix1scenefingerprint1b' in backlight,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 structural self-check failed: ' + ', '.join(failed))

def constrain(meter, allowance=None, protection=0.0, raw=True):
    if not raw:
        return meter, 'no_raw'
    if protection < 0.0:
        return min(meter, protection), 'mandatory_protection'
    if meter > 0.0 and allowance is not None:
        return min(meter, allowance), 'positive_allowance'
    return meter, 'preserve'

fixtures = [
    ('positive_limited', 0.80, 0.30, 0.0, True, 0.30),
    ('positive_negative_override', 0.45, 0.08, -0.327, True, -0.327),
    ('negative_underprotected_fix1', -0.10, 0.50, -0.33, True, -0.33),
    ('negative_already_more_protective_fix1', -0.50, 0.50, -0.33, True, -0.50),
    ('negative_preserved_with_headroom', -0.25, 0.50, 0.0, True, -0.25),
    ('neutral_preserved', 0.0, 0.50, 0.0, True, 0.0),
    ('no_matched_raw', 0.42, None, 0.0, False, 0.42),
]
for name, meter, allowance, protection, raw, expected in fixtures:
    got, reason = constrain(meter, allowance, protection, raw)
    print(f'CS1AF1 {name}: meter={meter:+.3f} result={got:+.3f} reason={reason}')
    if not math.isclose(got, expected, rel_tol=0.0, abs_tol=1e-12):
        raise SystemExit(f'CONSTRAINTSPLIT1A-FIX1 regression failed: {name}')

meter = 0.672
nearest = constrain(meter, 0.200, 0.0, True)[0]
envelope = constrain(meter, 0.069, 0.0, True)[0]
if not envelope <= nearest:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 conservative allowance envelope widened exposure')
print(f'CS1AF1 envelope sanity: meter={meter:+.3f} nearest={nearest:+.3f} envelope={envelope:+.3f}')

print('CONSTRAINTSPLIT1A-FIX1 verification passed')
