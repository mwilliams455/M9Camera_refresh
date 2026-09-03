#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-constraintsplit1a-fix1.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
constraint_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java'
gradle_p = root / 'app/build.gradle'
back_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

negative = negative_p.read_text()
constraint = constraint_p.read_text()
gradle = gradle_p.read_text()
back = back_p.read_text()

if 'm9cam.constraintsplit.v1.virtualbv1a_rawconstraint1a' not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 requires base CONSTRAINTSPLIT1A')
if 'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a' not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 requires FP1B/SIGNEDCAL1A generated source')

# 1. Mandatory negative RAW protection is a true downstream safety bound.
old_mandatory = '''        if (mandatoryProtectionEv < 0.0 && meterRequestEv > 0.0) {
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    positiveCandidateEv, mandatoryProtectionEv,
                    "positive_meter_request_overridden_by_existing_signedcal_negative_gate",
                    false, true);
        }
'''
new_mandatory = '''        if (mandatoryProtectionEv < 0.0) {
            double constrained = Math.min(meterRequestEv, mandatoryProtectionEv);
            boolean protectionLimited = constrained + 1e-12 < meterRequestEv;
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    positiveCandidateEv, constrained,
                    protectionLimited
                            ? "meter_request_limited_by_existing_signedcal_negative_gate"
                            : "meter_request_already_at_or_below_existing_signedcal_negative_gate",
                    false, protectionLimited);
        }
'''
if old_mandatory not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 mandatory-protection anchor missing')
constraint = constraint.replace(old_mandatory, new_mandatory, 1)

# 2. Diagnostic conservative envelope across every recent FP1B-passing RAW.
vars_anchor = '''            double bestSpatialTileMedianDistance = Double.POSITIVE_INFINITY;
'''
vars_repl = '''            double bestSpatialTileMedianDistance = Double.POSITIVE_INFINITY;
            int passingConstraintCandidateCount = 0;
            double conservativePositiveAllowanceEv = Double.NaN;
            double strongestMandatoryProtectionEv = 0.0;
'''
if vars_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 FP1B envelope variable anchor missing')
negative = negative.replace(vars_anchor, vars_repl, 1)

loop_anchor = '''                double d = current.distance(candidate.scene);
                if (d < bestDistance) {
'''
loop_repl = '''                double d = current.distance(candidate.scene);
                if (d <= SIMILAR_SCENE_DISTANCE) {
                    passingConstraintCandidateCount++;
                    double allowance = constraintPositiveAllowance(candidate);
                    if (finite(allowance)) {
                        conservativePositiveAllowanceEv = finite(conservativePositiveAllowanceEv)
                                ? Math.min(conservativePositiveAllowanceEv, allowance)
                                : allowance;
                    }
                    double protection = constraintMandatoryProtection(candidate);
                    if (finite(protection) && protection < 0.0) {
                        strongestMandatoryProtectionEv =
                                Math.min(strongestMandatoryProtectionEv, protection);
                    }
                }
                if (d < bestDistance) {
'''
if loop_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 FP1B candidate-loop anchor missing')
negative = negative.replace(loop_anchor, loop_repl, 1)

output_anchor = '''            out.put("nearestCompletedSpatialTileMedianDistance",
                    finite(bestSpatialTileMedianDistance) ? bestSpatialTileMedianDistance : JSONObject.NULL);
            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);
'''
output_repl = '''            out.put("nearestCompletedSpatialTileMedianDistance",
                    finite(bestSpatialTileMedianDistance) ? bestSpatialTileMedianDistance : JSONObject.NULL);
            out.put("passingConstraintCandidateCount", passingConstraintCandidateCount);
            out.put("constraintEnvelopeMode",
                    "diagnostic_all_recent_fp1b_passing_completed_raws");
            out.put("conservativePositiveAllowanceEv",
                    passingConstraintCandidateCount > 0 && finite(conservativePositiveAllowanceEv)
                            ? conservativePositiveAllowanceEv : JSONObject.NULL);
            out.put("strongestMandatoryProtectionEv",
                    passingConstraintCandidateCount > 0
                            ? strongestMandatoryProtectionEv : JSONObject.NULL);
            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);
'''
if output_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 FP1B envelope output anchor missing')
negative = negative.replace(output_anchor, output_repl, 1)

helper_anchor = '''    private static JSONObject buildSignedCalibration(CompletedRaw raw, String role) {
'''
helpers = '''    private static double constraintPositiveAllowance(CompletedRaw raw) {
        if (raw == null) return Double.NaN;
        double clipRisk = smoothstep(raw.clip, 0.005, 0.030);
        double meaningfulClipRiskEvidence = clamp01(clipRisk
                * Math.max(0.35, smoothstep(raw.q998, 0.72, 0.96)));
        double rawHeadroomEv = log2(0.92 / Math.max(raw.q998, 1e-6));
        return clamp(rawHeadroomEv, 0.0, MAX_POSITIVE_DELTA_EV)
                * (1.0 - 0.80 * meaningfulClipRiskEvidence);
    }

    private static double constraintMandatoryProtection(CompletedRaw raw) {
        if (raw == null) return 0.0;
        double clipRisk = smoothstep(raw.clip, 0.005, 0.030);
        double meaningfulClipRiskEvidence = clamp01(clipRisk
                * Math.max(0.35, smoothstep(raw.q998, 0.72, 0.96)));
        double q50Adequacy = smoothstep(raw.q50, 0.025, 0.080);
        double q25Adequacy = smoothstep(raw.q25, 0.006, 0.025);
        double lowerBodyAdequacy = clamp01(0.68 * q50Adequacy + 0.32 * q25Adequacy);
        double shadowStarvation = clamp01(1.0 - lowerBodyAdequacy);
        if (meaningfulClipRiskEvidence > 0.45 && shadowStarvation < 0.55) {
            return -0.35 * meaningfulClipRiskEvidence * (1.0 - shadowStarvation);
        }
        return 0.0;
    }

    private static JSONObject buildSignedCalibration(CompletedRaw raw, String role) {
'''
if helper_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 SIGNEDCAL helper anchor missing')
negative = negative.replace(helper_anchor, helpers, 1)

# 3. Carry nearest and envelope constraints to same-frame RAW oracle.
note_sig_anchor = '''    public static synchronized boolean noteCaptureConstraint(long sequence,
                                                             double meterRequestEv,
                                                             boolean matchedConstraintAvailable,
                                                             double matchedConstrainedEv) {
'''
note_sig_repl = '''    public static synchronized boolean noteCaptureConstraint(long sequence,
                                                             double meterRequestEv,
                                                             boolean matchedConstraintAvailable,
                                                             double matchedConstrainedEv,
                                                             boolean envelopeConstraintAvailable,
                                                             double envelopeConstrainedEv) {
'''
if note_sig_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 capture-correlation signature anchor missing')
negative = negative.replace(note_sig_anchor, note_sig_repl, 1)

note_body_anchor = '''            scene.matchedConstrainedEv = scene.matchedConstraintAvailable
                    ? matchedConstrainedEv : Double.NaN;
            return true;
'''
note_body_repl = '''            scene.matchedConstrainedEv = scene.matchedConstraintAvailable
                    ? matchedConstrainedEv : Double.NaN;
            scene.envelopeConstraintAvailable = envelopeConstraintAvailable
                    && finite(envelopeConstrainedEv);
            scene.envelopeConstrainedEv = scene.envelopeConstraintAvailable
                    ? envelopeConstrainedEv : Double.NaN;
            return true;
'''
if note_body_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 capture-correlation body anchor missing')
negative = negative.replace(note_body_anchor, note_body_repl, 1)

scene_field_anchor = '''        double matchedConstrainedEv = Double.NaN;
'''
scene_field_repl = '''        double matchedConstrainedEv = Double.NaN;
        boolean envelopeConstraintAvailable = false;
        double envelopeConstrainedEv = Double.NaN;
'''
if scene_field_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 scene correlation fields anchor missing')
negative = negative.replace(scene_field_anchor, scene_field_repl, 1)

oracle_call_anchor = '''                    scene != null && scene.matchedConstraintAvailable,
                    scene != null ? scene.matchedConstrainedEv : Double.NaN));
'''
oracle_call_repl = '''                    scene != null && scene.matchedConstraintAvailable,
                    scene != null ? scene.matchedConstrainedEv : Double.NaN,
                    scene != null && scene.envelopeConstraintAvailable,
                    scene != null ? scene.envelopeConstrainedEv : Double.NaN));
'''
if oracle_call_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 oracle call anchor missing')
negative = negative.replace(oracle_call_anchor, oracle_call_repl, 1)

capture_output_anchor = '''            out.put("matchedRawConstraintReason", result.reason);
            out.put("meterWasLimitedByPositiveAllowance",
'''
capture_output_repl = '''            out.put("matchedRawConstraintReason", result.reason);
            out.put("nearestRawConstrainedMeterRequestEv",
                    feedbackAvailable ? result.constrainedEv : JSONObject.NULL);

            int passingConstraintCandidateCount = matched != null
                    ? matched.optInt("passingConstraintCandidateCount", 0) : 0;
            double envelopePositiveAllowanceEv = matched != null
                    ? matched.optDouble("conservativePositiveAllowanceEv", Double.NaN)
                    : Double.NaN;
            double envelopeMandatoryProtectionEv = matched != null
                    ? matched.optDouble("strongestMandatoryProtectionEv", Double.NaN)
                    : Double.NaN;
            boolean envelopeConstraintAvailable = feedbackAvailable
                    && passingConstraintCandidateCount > 0
                    && finite(envelopePositiveAllowanceEv)
                    && finite(envelopeMandatoryProtectionEv);
            Constraint envelopeResult = envelopeConstraintAvailable
                    ? constrainEnvelope(meterRequestEv, envelopePositiveAllowanceEv,
                            envelopeMandatoryProtectionEv)
                    : Constraint.noRaw(meterRequestEv, "conservative_fp1b_envelope_unavailable");
            out.put("conservativeEnvelopeAvailable", envelopeConstraintAvailable);
            out.put("conservativeEnvelopePassingRawCount", passingConstraintCandidateCount);
            out.put("conservativeEnvelopePositiveAllowanceEv",
                    envelopeConstraintAvailable
                            ? envelopePositiveAllowanceEv : JSONObject.NULL);
            out.put("conservativeEnvelopeMandatoryProtectionEv",
                    envelopeConstraintAvailable
                            ? envelopeMandatoryProtectionEv : JSONObject.NULL);
            out.put("conservativeEnvelopeConstrainedMeterRequestEv",
                    envelopeConstraintAvailable
                            ? envelopeResult.constrainedEv : JSONObject.NULL);
            out.put("conservativeEnvelopeConstraintReason", envelopeResult.reason);

            out.put("meterWasLimitedByPositiveAllowance",
'''
if capture_output_anchor not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 capture envelope output anchor missing')
constraint = constraint.replace(capture_output_anchor, capture_output_repl, 1)

note_call_anchor = '''            boolean stored = M9NegativeFeedback1A.noteCaptureConstraint(
                    captureSequence, meterRequestEv, feedbackAvailable, result.constrainedEv);
'''
note_call_repl = '''            boolean stored = M9NegativeFeedback1A.noteCaptureConstraint(
                    captureSequence, meterRequestEv, feedbackAvailable, result.constrainedEv,
                    envelopeConstraintAvailable, envelopeResult.constrainedEv);
'''
if note_call_anchor not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 capture note call anchor missing')
constraint = constraint.replace(note_call_anchor, note_call_repl, 1)

oracle_sig_anchor = '''                                            boolean matchedConstraintAvailable,
                                            double matchedConstrainedEv) {
'''
oracle_sig_repl = '''                                            boolean matchedConstraintAvailable,
                                            double matchedConstrainedEv,
                                            boolean envelopeConstraintAvailable,
                                            double envelopeConstrainedEv) {
'''
if oracle_sig_anchor not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 oracle signature anchor missing')
constraint = constraint.replace(oracle_sig_anchor, oracle_sig_repl, 1)

oracle_output_anchor = '''            out.put("meterVsOracleDirectionAgreement",
'''
oracle_output_repl = '''            out.put("conservativeEnvelopeConstraintAvailable",
                    envelopeConstraintAvailable && finite(envelopeConstrainedEv));
            if (envelopeConstraintAvailable && finite(envelopeConstrainedEv)) {
                out.put("conservativeEnvelopeConstrainedMeterRequestEv",
                        envelopeConstrainedEv);
                if (finite(oracle.constrainedEv)) {
                    out.put("conservativeEnvelopeVsOracleConstraintDeltaEv",
                            envelopeConstrainedEv - oracle.constrainedEv);
                    out.put("conservativeEnvelopeVsOracleDirectionAgreement",
                            direction(envelopeConstrainedEv)
                                    .equals(direction(oracle.constrainedEv)));
                } else {
                    out.put("conservativeEnvelopeVsOracleConstraintDeltaEv",
                            JSONObject.NULL);
                    out.put("conservativeEnvelopeVsOracleDirectionAgreement",
                            JSONObject.NULL);
                }
            } else {
                out.put("conservativeEnvelopeConstrainedMeterRequestEv",
                        JSONObject.NULL);
                out.put("conservativeEnvelopeVsOracleConstraintDeltaEv",
                        JSONObject.NULL);
                out.put("conservativeEnvelopeVsOracleDirectionAgreement",
                        JSONObject.NULL);
            }

            out.put("meterVsOracleDirectionAgreement",
'''
if oracle_output_anchor not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 oracle envelope output anchor missing')
constraint = constraint.replace(oracle_output_anchor, oracle_output_repl, 1)

constraint_helper_anchor = '''    private static JSONObject contract() {
'''
constraint_helper = '''    private static Constraint constrainEnvelope(double meterRequestEv,
                                                double positiveAllowanceEv,
                                                double mandatoryProtectionEv) {
        if (!finite(positiveAllowanceEv) || !finite(mandatoryProtectionEv)) {
            return Constraint.noRaw(meterRequestEv, "conservative_fp1b_envelope_invalid");
        }
        positiveAllowanceEv = Math.max(0.0, positiveAllowanceEv);
        if (mandatoryProtectionEv >= 0.0) mandatoryProtectionEv = 0.0;
        if (mandatoryProtectionEv < 0.0) {
            double constrained = Math.min(meterRequestEv, mandatoryProtectionEv);
            boolean protectionLimited = constrained + 1e-12 < meterRequestEv;
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    Double.NaN, constrained,
                    protectionLimited
                            ? "conservative_envelope_mandatory_protection_limited_meter"
                            : "meter_already_at_or_below_conservative_envelope_protection",
                    false, protectionLimited);
        }
        if (meterRequestEv > 0.0) {
            double constrained = Math.min(meterRequestEv, positiveAllowanceEv);
            boolean limited = constrained + 1e-12 < meterRequestEv;
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    Double.NaN, constrained,
                    limited
                            ? "positive_meter_request_limited_by_conservative_fp1b_allowance"
                            : "positive_meter_request_within_conservative_fp1b_allowance",
                    limited, false);
        }
        return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                Double.NaN, meterRequestEv,
                meterRequestEv < 0.0
                        ? "negative_meter_request_preserved_by_conservative_envelope"
                        : "neutral_meter_request_preserved_by_conservative_envelope",
                false, false);
    }

    private static JSONObject contract() {
'''
if constraint_helper_anchor not in constraint:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 constraint helper anchor missing')
constraint = constraint.replace(constraint_helper_anchor, constraint_helper, 1)

constraint = constraint.replace(
        'm9cam.constraintsplit.v1.virtualbv1a_rawconstraint1a',
        'm9cam.constraintsplit.v2.virtualbv1a_rawconstraint1b.fix1', 1)

old_version = "versionName '1.50-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1a-cm1b'"
new_version = "versionName '1.51-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-cm1b'"
if old_version not in gradle:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 expected 1.50 versionName missing')
gradle = gradle.replace(old_version, new_version, 1)

old_marker = 'virtualbv1aconstraintsplit1ascenefingerprint1b'
new_marker = 'virtualbv1aconstraintsplit1afix1scenefingerprint1b'
if old_marker not in back:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 forensic marker anchor missing')
back = back.replace(old_marker, new_marker, 1)
if '1.50-' not in back:
    raise SystemExit('CONSTRAINTSPLIT1A-FIX1 build identity version anchor missing')
back = back.replace('1.50-', '1.51-', 1)

negative_p.write_text(negative)
constraint_p.write_text(constraint)
gradle_p.write_text(gradle)
back_p.write_text(back)

print('M9Cam CONSTRAINTSPLIT1A-FIX1 diagnostic overlay applied')
print(' - mandatory SIGNEDCAL negative protection now uses min(meter, protection)')
print(' - negative Leica-like meter demand can never be made less protective by RAW safety')
print(' - nearest FP1B selection remains frozen and unchanged')
print(' - adds conservative allowance/mandatory-protection envelope across all recent FP1B passers')
print(' - nearest, conservative-envelope and same-frame oracle constraints are correlated')
print(' - envelope uses exact frozen SIGNEDCAL thresholds/equations without new heuristics')
print(' - no Camera2, Photon, FB1, motion, renderer-pixel, JPEG or DNG mutation')
