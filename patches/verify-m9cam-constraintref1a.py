#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-constraintref1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
def read(rel):
    p = root / rel
    if not p.exists(): raise SystemExit(f'missing {rel}')
    return p.read_text()
negative = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
constraint = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java')
constraint_ref = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java')
metadata = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
virtual = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
coordinator = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java')
iso_selector = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
policy = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
gradle = read('app/build.gradle')
backlight = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
compact_version = '1.53-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b-cr1a'
checks = {
    'CONSTRAINTREF1A schema': 'm9cam.constraintref.v1' in constraint_ref,
    'diagnostic-only contract': 'diagnostic_only_no_exposure_mutation' in constraint_ref and 'usedToMutateCaptureTarget", false' in constraint_ref and 'liveEligible", false' in constraint_ref,
    'Photon baseline energy recorded': 'photonBaselineEnergyIsoSeconds' in constraint_ref and 'photonReferenceIso' in constraint_ref and 'photonReferenceExposureNs' in constraint_ref,
    'actual capture energy recorded': 'actualCaptureEnergyIsoSeconds' in constraint_ref and 'actualCaptureIso' in constraint_ref and 'actualCaptureExposureNs' in constraint_ref,
    'reference offset is energy ratio': 'log2(actualEnergy / photonEnergy)' in constraint_ref,
    'positive ceiling conversion': 'sourceOffset + rawAllowance' in constraint_ref and 'sameFrameActualCaptureOffsetFromPhotonEv + Math.max(0.0, allowance)' in constraint_ref,
    'mandatory ceiling conversion': 'sourceOffset + rawProtection' in constraint_ref and 'sameFrameActualCaptureOffsetFromPhotonEv + protection' in constraint_ref,
    'mandatory ceiling semantics': 'Math.min(meterRequestFromPhotonEv,' in constraint_ref and 'mandatoryCeilingFromPhotonEv' in constraint_ref,
    'positive allowance stays a ceiling': 'meterRequestFromPhotonEv > 0.0' in constraint_ref and 'positiveCeilingFromPhotonEv' in constraint_ref,
    'legacy raw-relative comparator retained': 'legacyRawRelativeConstraint' in constraint_ref and 'matchedRawConstrainedMeterRequestEv' in constraint_ref,
    'architecture A logged': 'architectureAReplaceFb1ResultEv' in constraint_ref and 'photon_baseline_to_virtualbv_then_reference_aligned_sensor_constraint' in constraint_ref,
    'architecture B residual logged': 'meterResidualAfterLegacyFb1Ev' in constraint_ref and 'architectureBResidualAfterFb1ResultEv' in constraint_ref,
    'source reference coordinates stored in FP1B scene history': 'double photonBaselineEnergyIsoSeconds = Double.NaN;' in negative and 'double actualCaptureOffsetFromPhotonEv = Double.NaN;' in negative and 'noteCaptureReference' in negative,
    'nearest historical source coordinates surfaced': 'sourcePhotonBaselineEnergyIsoSeconds' in negative and 'sourceActualCaptureOffsetFromPhotonEv' in negative,
    'aligned conservative envelope': 'passingReferenceAlignedCandidateCount' in negative and 'conservativePositiveCeilingFromPhotonEv' in negative and 'conservativeMandatoryCeilingFromPhotonEv' in negative,
    'same-frame reference oracle exact-gated': 'm9ConstraintRefOracle' in negative and 'captureCorrelationExact' in constraint_ref and 'oracleComparisonAccepted' in constraint_ref,
    'EXACTID1A identity fields preserved': 'String captureIdentity = null;' in negative and 'long rawTimestampNs = -1L;' in negative and 'boolean captureIdentityBound = false;' in negative and 'exact_dng_filename_plus_raw_timestamp' in negative and 'fifoFallbackUsedForHistory", false' in negative,
    'FP1B threshold frozen': 'private static final double SIMILAR_SCENE_DISTANCE = 1.0;' in negative,
    'FP1B age frozen': 'private static final long MAX_FEEDBACK_AGE_MS = 60_000L;' in negative,
    'FP1B spatial scale frozen': 'Math.abs(a[i] - b[i]) / 60.0' in negative,
    'SIGNEDCAL negative gate frozen': 'meaningfulClipRiskEvidence > 0.45 && shadowStarvation < 0.55' in negative,
    'SIGNEDCAL raw headroom target frozen': 'log2(0.92 / Math.max(raw.q998, 1e-6))' in negative,
    'VirtualBV center/global weights frozen': 'PROVISIONAL_CENTER_WEIGHT = 0.70' in virtual and 'PROVISIONAL_GLOBAL_WEIGHT = 0.30' in virtual and 'PROVISIONAL_REFERENCE_Y = 100.0' in virtual,
    'legacy CONSTRAINTSPLIT EXACTID schema preserved': 'm9cam.constraintsplit.v3.virtualbv1a_rawconstraint1b.fix1.exactid1a' in constraint,
    'FIX1 mandatory min preserved': 'double constrained = Math.min(meterRequestEv, mandatoryProtectionEv);' in constraint,
    'metadata publishes old and aligned diagnostics side by side': 'root.put("m9ConstraintSplit", m9ConstraintSplit);' in metadata and 'root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));' in metadata,
    'CONSTRAINTREF not wired into live exposure seams': 'M9ConstraintRef1A' not in iso_selector and 'M9ConstraintRef1A' not in policy and 'M9ConstraintRef1A' not in coordinator,
    'renderer has no CONSTRAINTREF live dependency': 'M9ConstraintRef1A' not in renderer and 'm9ConstraintRef' not in renderer,
    'compact version': ("versionName '" + compact_version + "'") in gradle and len(compact_version) < 96,
    'forensic identity': 'virtualbv1aconstraintsplit1afix1exactid1aconstraintref1ascenefingerprint1b' in backlight,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items(): print(('OK   ' if ok else 'FAIL ') + name)
if failed: raise SystemExit('CONSTRAINTREF1A structural self-check failed: ' + ', '.join(failed))

def aligned(meter, offset, positive_allowance=None, mandatory_protection=None):
    pos = None if positive_allowance is None else offset + positive_allowance
    mandatory = None
    if mandatory_protection is not None and mandatory_protection < 0.0: mandatory = offset + mandatory_protection
    if mandatory is not None: return min(meter, mandatory), pos, mandatory
    if meter > 0.0 and pos is not None: return min(meter, pos), pos, mandatory
    return meter, pos, mandatory

def assert_close(name, got, want, eps=1e-9):
    if not math.isfinite(got) or abs(got - want) > eps: raise SystemExit(f'{name} failed: got {got}, expected {want}')
    print(f'FIXTURE {name}: PASS ({got:+.6f} EV)')

offset = math.log2(2.0 / 1.0)
result, pos, mandatory = aligned(0.80, offset, positive_allowance=0.25)
assert_close('positive_ceiling', pos, 1.25)
assert_close('positive_meter_preserved', result, 0.80)
result, pos, mandatory = aligned(0.80, offset, positive_allowance=0.25, mandatory_protection=-0.40)
assert_close('mandatory_ceiling', mandatory, 0.60)
assert_close('mandatory_limits_meter', result, 0.60)
result, pos, mandatory = aligned(-0.50, 0.0, positive_allowance=0.20, mandatory_protection=-0.33)
assert_close('already_negative_meter_preserved', result, -0.50)
anchor_offset = math.log2(1.567751936 / 0.940)
result, pos, _ = aligned(0.792107, anchor_offset, positive_allowance=0.367240)
if pos <= 0.792107: raise SystemExit('08:02 reference fixture failed: aligned ceiling should exceed meter request')
assert_close('080247_meter_preserved', result, 0.792107)
print(f'FIXTURE 080247_aligned_positive_ceiling: PASS ({pos:+.6f} EV)')
print('CONSTRAINTREF1A verification passed')
