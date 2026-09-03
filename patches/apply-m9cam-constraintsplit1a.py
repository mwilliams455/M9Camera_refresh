#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-constraintsplit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
metadata_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
constraint_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java'

negative_p = root / negative_rel
metadata_p = root / metadata_rel
negative = negative_p.read_text()
metadata = metadata_p.read_text()

if 'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a' not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A requires M9NEGATIVE1C / SCENEFINGERPRINT1B / SIGNEDCAL1A')
if 'sceneAssociationFrozen", "SCENEFINGERPRINT1B"' not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A stale scene-association diagnostic text remains')
if 'root.put("m9VirtualBv", M9VirtualBv1A.evaluate(root));' not in metadata:
    raise SystemExit('CONSTRAINTSPLIT1A VIRTUALBV1A metadata anchor missing')

constructor_anchor = '''    private M9NegativeFeedback1A() {}\n'''
constructor_repl = '''    private M9NegativeFeedback1A() {}\n\n    /** Correlates capture-time meter/constraint telemetry with the queued RAW completion. */\n    public static synchronized boolean noteCaptureConstraint(long sequence,\n                                                             double meterRequestEv,\n                                                             boolean matchedConstraintAvailable,\n                                                             double matchedConstrainedEv) {\n        if (sequence <= 0L || !finite(meterRequestEv)) return false;\n        for (SceneSignature scene : PENDING) {\n            if (scene.sequence != sequence) continue;\n            scene.meterRequestEv = meterRequestEv;\n            scene.matchedConstraintAvailable = matchedConstraintAvailable\n                    && finite(matchedConstrainedEv);\n            scene.matchedConstrainedEv = scene.matchedConstraintAvailable\n                    ? matchedConstrainedEv : Double.NaN;\n            return true;\n        }\n        return false;\n    }\n'''
if constructor_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A M9Negative constructor anchor missing')
negative = negative.replace(constructor_anchor, constructor_repl, 1)

best_anchor = '''            CompletedRaw best = null;\n            double bestDistance = Double.POSITIVE_INFINITY;\n'''
best_repl = '''            CompletedRaw best = null;\n            double bestDistance = Double.POSITIVE_INFINITY;\n            double bestSpatialTileMedianDistance = Double.POSITIVE_INFINITY;\n'''
if best_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A best-distance anchor missing')
negative = negative.replace(best_anchor, best_repl, 1)

selection_anchor = '''                if (d < bestDistance) {\n                    bestDistance = d;\n                    best = candidate;\n                }\n'''
selection_repl = '''                if (d < bestDistance) {\n                    bestDistance = d;\n                    bestSpatialTileMedianDistance = spatialTileMedianDistance(\n                            current.spatialTileMedians3x3, candidate.scene.spatialTileMedians3x3);\n                    best = candidate;\n                }\n'''
if selection_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A best-candidate anchor missing')
negative = negative.replace(selection_anchor, selection_repl, 1)

distance_output_anchor = '''            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n'''
distance_output_repl = '''            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("nearestCompletedSpatialTileMedianDistance",\n                    finite(bestSpatialTileMedianDistance) ? bestSpatialTileMedianDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n'''
if distance_output_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A distance-output anchor missing')
negative = negative.replace(distance_output_anchor, distance_output_repl, 1)

signed_output_anchor = '''            out.put("signedCalibration1A", buildSignedCalibration(raw, "completed_raw_self"));\n            out.put("reason", scene != null\n'''
signed_output_repl = '''            JSONObject signedCalibration = buildSignedCalibration(raw, "completed_raw_self");\n            out.put("signedCalibration1A", signedCalibration);\n            out.put("m9ConstraintSplitOracle", M9ConstraintSplit1A.evaluateOracle(\n                    scene != null ? scene.meterRequestEv : Double.NaN,\n                    signedCalibration,\n                    scene != null ? scene.sequence : -1L,\n                    raw.completedSequence,\n                    scene != null && scene.matchedConstraintAvailable,\n                    scene != null ? scene.matchedConstrainedEv : Double.NaN));\n            out.put("reason", scene != null\n'''
if signed_output_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A completed-RAW oracle anchor missing')
negative = negative.replace(signed_output_anchor, signed_output_repl, 1)

allowance_anchor = '''            out.put("rawHeadroomTo0p92Ev", rawHeadroomEv);\n            out.put("positiveCandidateEvBeforeDeadband", positiveCandidateEv);\n'''
allowance_repl = '''            out.put("rawHeadroomTo0p92Ev", rawHeadroomEv);\n            out.put("additionalCaptureHeadroomEv", additionalCaptureHeadroomEv);\n            out.put("positiveCandidateEvBeforeDeadband", positiveCandidateEv);\n'''
if allowance_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A positive-allowance telemetry anchor missing')
negative = negative.replace(allowance_anchor, allowance_repl, 1)

scene_field_anchor = '''        double[] spatialTileMedians3x3;\n'''
scene_field_repl = '''        double[] spatialTileMedians3x3;\n        double meterRequestEv = Double.NaN;\n        boolean matchedConstraintAvailable = false;\n        double matchedConstrainedEv = Double.NaN;\n'''
if scene_field_anchor not in negative:
    raise SystemExit('CONSTRAINTSPLIT1A capture-correlation field anchor missing')
negative = negative.replace(scene_field_anchor, scene_field_repl, 1)
negative_p.write_text(negative)

metadata_anchor = '''            root.put("m9VirtualBv", M9VirtualBv1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
metadata_repl = '''            JSONObject m9VirtualBv = M9VirtualBv1A.evaluate(root);\n            root.put("m9VirtualBv", m9VirtualBv);\n            root.put("m9ConstraintSplit", M9ConstraintSplit1A.evaluateCapture(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if metadata_anchor not in metadata:
    raise SystemExit('CONSTRAINTSPLIT1A metadata publication anchor missing')
metadata_p.write_text(metadata.replace(metadata_anchor, metadata_repl, 1))

constraint = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * CONSTRAINTSPLIT1A separates Leica-like meter demand from Xiaomi RAW safety.
 * It is diagnostic-only: no result from this class is consumed by Camera2,
 * Photon exposure allocation, motion policy, rendering, JPEG, or DNG.
 */
public final class M9ConstraintSplit1A {
    public static final String SCHEMA =
            "m9cam.constraintsplit.v1.virtualbv1a_rawconstraint1a";
    private static final double DIRECTION_DEADBAND_EV = 0.08;

    private M9ConstraintSplit1A() {}

    public static JSONObject evaluateCapture(JSONObject root) {
        JSONObject out = contract();
        try {
            out.put("phase", "capture_with_previous_fp1b_matched_raw");
            JSONObject virtual = root != null ? root.optJSONObject("m9VirtualBv") : null;
            double meterRequestEv = virtual != null
                    ? virtual.optDouble("signedMeterDeltaEv", Double.NaN) : Double.NaN;
            if (!finite(meterRequestEv)) {
                invalid(out, "virtualbv_meter_request_missing");
                return out;
            }

            out.put("valid", true);
            out.put("meterRequestEv", meterRequestEv);
            out.put("meterRequestDirection", direction(meterRequestEv));
            putFinite(out, "virtualBvEv",
                    virtual.optDouble("virtualBvEv", Double.NaN));
            putFinite(out, "photonEquivalentBvEv",
                    virtual.optDouble("photonEquivalentBvEv", Double.NaN));

            JSONObject scene = root.optJSONObject("m9SceneExposureDiagnostic");
            JSONObject split = scene != null ? scene.optJSONObject("captureRenderSplit") : null;
            JSONObject matched = split != null ? split.optJSONObject("m9Negative1A") : null;
            JSONObject queue = split != null
                    ? split.optJSONObject("m9NegativeCaptureSceneQueue") : null;
            long captureSequence = queue != null
                    ? queue.optLong("captureSequence", -1L) : -1L;
            boolean feedbackAvailable = matched != null
                    && matched.optBoolean("feedbackAvailable", false);
            out.put("matchedRawFeedbackAvailable", feedbackAvailable);
            out.put("matchedRawSourceCaptureSequence",
                    feedbackAvailable && matched.has("sourceCaptureSequence")
                            ? matched.optLong("sourceCaptureSequence") : JSONObject.NULL);
            out.put("matchedRawSourceCompletedSequence",
                    feedbackAvailable && matched.has("sourceCompletedSequence")
                            ? matched.optLong("sourceCompletedSequence") : JSONObject.NULL);
            putNullableFinite(out, "matchedRawSceneDistance", matched,
                    "nearestCompletedSceneDistance");
            putNullableFinite(out, "matchedRawSpatialTileMedianDistance", matched,
                    "nearestCompletedSpatialTileMedianDistance");
            out.put("matchedRawAgeMs",
                    feedbackAvailable && matched.has("sourceAgeMs")
                            ? matched.optLong("sourceAgeMs") : JSONObject.NULL);

            Constraint result;
            if (feedbackAvailable) {
                JSONObject signed = matched.optJSONObject("signedCalibration1A");
                result = constrain(meterRequestEv, signed);
                out.put("matchedRawPositiveAllowanceEv",
                        finite(result.positiveAllowanceEv)
                                ? result.positiveAllowanceEv : JSONObject.NULL);
                out.put("matchedRawMandatoryProtectionEv",
                        finite(result.mandatoryProtectionEv)
                                ? result.mandatoryProtectionEv : JSONObject.NULL);
                out.put("matchedRawPositiveCandidateEv",
                        result.positiveCandidateEv);
            } else {
                result = Constraint.noRaw(meterRequestEv,
                        matched != null ? matched.optString("reason", "matched_raw_unavailable")
                                : "matched_raw_diagnostic_missing");
                out.put("matchedRawPositiveAllowanceEv", JSONObject.NULL);
                out.put("matchedRawMandatoryProtectionEv", JSONObject.NULL);
                out.put("matchedRawPositiveCandidateEv", JSONObject.NULL);
            }
            out.put("matchedRawConstrainedMeterRequestEv", result.constrainedEv);
            out.put("matchedRawConstraintReason", result.reason);
            out.put("meterWasLimitedByPositiveAllowance",
                    result.limitedByPositiveAllowance);
            out.put("meterWasOverriddenByMandatoryProtection",
                    result.overriddenByMandatoryProtection);
            out.put("positiveAllowanceMeaning",
                    "ceiling_on_positive_meter_demand_not_a_command_to_raise_exposure");
            out.put("mandatoryProtectionMeaning",
                    "existing_SIGNEDCAL1A_negative_gate_only_no_new_q99_8_heuristic");

            boolean stored = M9NegativeFeedback1A.noteCaptureConstraint(
                    captureSequence, meterRequestEv, feedbackAvailable, result.constrainedEv);
            out.put("captureSequence", captureSequence > 0L
                    ? captureSequence : JSONObject.NULL);
            out.put("completionCorrelationStored", stored);
            out.put("reason", feedbackAvailable
                    ? "meter_request_constrained_by_previous_fp1b_matched_raw_diagnostically"
                    : "meter_request_preserved_without_previous_fp1b_matched_raw");
        } catch (Throwable t) {
            try {
                invalid(out, "constraintsplit_capture_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    public static JSONObject evaluateOracle(double meterRequestEv,
                                            JSONObject sameFrameSignedCalibration,
                                            long captureSequence,
                                            long completedSequence,
                                            boolean matchedConstraintAvailable,
                                            double matchedConstrainedEv) {
        JSONObject out = contract();
        try {
            out.put("phase", "same_frame_completed_raw_oracle");
            out.put("captureSequence", captureSequence > 0L
                    ? captureSequence : JSONObject.NULL);
            out.put("completedSequence", completedSequence > 0L
                    ? completedSequence : JSONObject.NULL);
            boolean meterAvailable = finite(meterRequestEv);
            out.put("meterRequestAvailable", meterAvailable);
            if (meterAvailable) {
                out.put("meterRequestEv", meterRequestEv);
                out.put("meterRequestDirection", direction(meterRequestEv));
            } else {
                out.put("meterRequestEv", JSONObject.NULL);
                out.put("meterRequestDirection", "invalid");
            }

            Constraint oracle = meterAvailable
                    ? constrain(meterRequestEv, sameFrameSignedCalibration)
                    : Constraint.missingMeter(sameFrameSignedCalibration);
            out.put("oraclePositiveAllowanceEv", finite(oracle.positiveAllowanceEv)
                    ? oracle.positiveAllowanceEv : JSONObject.NULL);
            out.put("oracleMandatoryProtectionEv", finite(oracle.mandatoryProtectionEv)
                    ? oracle.mandatoryProtectionEv : JSONObject.NULL);
            out.put("oraclePositiveCandidateEv", finite(oracle.positiveCandidateEv)
                    ? oracle.positiveCandidateEv : JSONObject.NULL);
            out.put("oracleConstrainedMeterRequestEv", finite(oracle.constrainedEv)
                    ? oracle.constrainedEv : JSONObject.NULL);
            out.put("oracleConstraintReason", oracle.reason);
            out.put("meterWasLimitedByPositiveAllowance",
                    oracle.limitedByPositiveAllowance);
            out.put("meterWasOverriddenByMandatoryProtection",
                    oracle.overriddenByMandatoryProtection);

            out.put("matchedRawConstraintAvailable",
                    matchedConstraintAvailable && finite(matchedConstrainedEv));
            if (matchedConstraintAvailable && finite(matchedConstrainedEv)) {
                out.put("matchedRawConstrainedMeterRequestEv", matchedConstrainedEv);
                if (finite(oracle.constrainedEv)) {
                    out.put("matchedVsOracleConstraintDeltaEv",
                            matchedConstrainedEv - oracle.constrainedEv);
                    out.put("matchedVsOracleDirectionAgreement",
                            direction(matchedConstrainedEv)
                                    .equals(direction(oracle.constrainedEv)));
                } else {
                    out.put("matchedVsOracleConstraintDeltaEv", JSONObject.NULL);
                    out.put("matchedVsOracleDirectionAgreement", JSONObject.NULL);
                }
            } else {
                out.put("matchedRawConstrainedMeterRequestEv", JSONObject.NULL);
                out.put("matchedVsOracleConstraintDeltaEv", JSONObject.NULL);
                out.put("matchedVsOracleDirectionAgreement", JSONObject.NULL);
            }
            out.put("meterVsOracleDirectionAgreement",
                    meterAvailable && finite(oracle.constrainedEv)
                            ? direction(meterRequestEv).equals(direction(oracle.constrainedEv))
                            : JSONObject.NULL);
            out.put("valid", meterAvailable
                    && sameFrameSignedCalibration != null
                    && sameFrameSignedCalibration.optBoolean("valid", false));
            out.put("reason", meterAvailable
                    ? "same_frame_raw_oracle_constraint_recorded_no_live_exposure_change"
                    : "same_frame_raw_recorded_but_capture_meter_request_not_correlated");
        } catch (Throwable t) {
            try {
                invalid(out, "constraintsplit_oracle_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static Constraint constrain(double meterRequestEv, JSONObject signed) {
        if (signed == null || !signed.optBoolean("valid", false)) {
            return Constraint.noRaw(meterRequestEv, "raw_constraint_missing_or_invalid");
        }
        double positiveAllowanceEv = signed.optDouble(
                "additionalCaptureHeadroomEv", Double.NaN);
        if (!finite(positiveAllowanceEv)) {
            positiveAllowanceEv = Math.max(0.0, signed.optDouble(
                    "positiveCandidateEvBeforeDeadband", Double.NaN));
        }
        if (finite(positiveAllowanceEv)) {
            positiveAllowanceEv = Math.max(0.0, positiveAllowanceEv);
        }
        double positiveCandidateEv = Math.max(0.0, signed.optDouble(
                "positiveCandidateEvBeforeDeadband", 0.0));
        boolean negativeGatePass = signed.optBoolean("negativeGatePass", false);
        double mandatoryProtectionEv = negativeGatePass
                ? signed.optDouble("negativeCandidateAppliedByFrozenGateEv", 0.0)
                : 0.0;
        if (!finite(mandatoryProtectionEv) || mandatoryProtectionEv >= 0.0) {
            mandatoryProtectionEv = 0.0;
        }

        if (mandatoryProtectionEv < 0.0 && meterRequestEv > 0.0) {
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    positiveCandidateEv, mandatoryProtectionEv,
                    "positive_meter_request_overridden_by_existing_signedcal_negative_gate",
                    false, true);
        }
        if (meterRequestEv > 0.0 && finite(positiveAllowanceEv)) {
            double constrained = Math.min(meterRequestEv, positiveAllowanceEv);
            boolean limited = constrained + 1e-12 < meterRequestEv;
            return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                    positiveCandidateEv, constrained,
                    limited
                            ? "positive_meter_request_limited_by_sensor_positive_allowance"
                            : "positive_meter_request_within_sensor_positive_allowance",
                    limited, false);
        }
        return new Constraint(positiveAllowanceEv, mandatoryProtectionEv,
                positiveCandidateEv, meterRequestEv,
                meterRequestEv < 0.0
                        ? "negative_meter_request_preserved_positive_headroom_is_permission_not_command"
                        : "neutral_meter_request_preserved",
                false, false);
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("jpegBrightnessUsedForCapture", false);
            out.put("meterModelFrozen", "VIRTUALBV1A");
            out.put("sensorConstraintModelFrozen", "SIGNEDCAL1A_M9NEGATIVE1C");
            out.put("sceneAssociationFrozen", "SCENEFINGERPRINT1B");
        } catch (Exception ignored) {}
        return out;
    }

    private static void putNullableFinite(JSONObject out, String outKey,
                                          JSONObject source, String sourceKey) {
        try {
            if (source == null) {
                out.put(outKey, JSONObject.NULL);
                return;
            }
            double v = source.optDouble(sourceKey, Double.NaN);
            out.put(outKey, finite(v) ? v : JSONObject.NULL);
        } catch (Exception ignored) {}
    }

    private static void putFinite(JSONObject out, String key, double value) {
        try {
            out.put(key, finite(value) ? value : JSONObject.NULL);
        } catch (Exception ignored) {}
    }

    private static void invalid(JSONObject out, String reason) {
        try {
            out.put("valid", false);
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("reason", reason);
        } catch (Exception ignored) {}
    }

    private static String direction(double ev) {
        if (!finite(ev)) return "invalid";
        if (Math.abs(ev) < DIRECTION_DEADBAND_EV) return "neutral";
        return ev > 0.0 ? "increase" : "decrease";
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }

    private static final class Constraint {
        final double positiveAllowanceEv;
        final double mandatoryProtectionEv;
        final double positiveCandidateEv;
        final double constrainedEv;
        final String reason;
        final boolean limitedByPositiveAllowance;
        final boolean overriddenByMandatoryProtection;

        Constraint(double positiveAllowanceEv, double mandatoryProtectionEv,
                   double positiveCandidateEv, double constrainedEv, String reason,
                   boolean limitedByPositiveAllowance,
                   boolean overriddenByMandatoryProtection) {
            this.positiveAllowanceEv = positiveAllowanceEv;
            this.mandatoryProtectionEv = mandatoryProtectionEv;
            this.positiveCandidateEv = positiveCandidateEv;
            this.constrainedEv = constrainedEv;
            this.reason = reason;
            this.limitedByPositiveAllowance = limitedByPositiveAllowance;
            this.overriddenByMandatoryProtection = overriddenByMandatoryProtection;
        }

        static Constraint noRaw(double meterRequestEv, String reason) {
            return new Constraint(Double.NaN, Double.NaN, Double.NaN,
                    meterRequestEv, reason, false, false);
        }

        static Constraint missingMeter(JSONObject signed) {
            double allowance = signed != null
                    ? signed.optDouble("additionalCaptureHeadroomEv", Double.NaN)
                    : Double.NaN;
            double protection = signed != null && signed.optBoolean("negativeGatePass", false)
                    ? signed.optDouble("negativeCandidateAppliedByFrozenGateEv", 0.0)
                    : 0.0;
            double candidate = signed != null
                    ? signed.optDouble("positiveCandidateEvBeforeDeadband", Double.NaN)
                    : Double.NaN;
            return new Constraint(allowance, protection, candidate, Double.NaN,
                    "capture_meter_request_missing_for_oracle_correlation",
                    false, false);
        }
    }
}
'''
constraint_p = root / constraint_rel
constraint_p.parent.mkdir(parents=True, exist_ok=True)
constraint_p.write_text(constraint)

gradle_p = root / 'app/build.gradle'
gradle = gradle_p.read_text()
old_version = "versionName '1.49-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cm1b'"
new_version = "versionName '1.50-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1a-cm1b'"
if old_version not in gradle:
    raise SystemExit('CONSTRAINTSPLIT1A expected SCENEFINGERPRINT1B versionName missing')
gradle_p.write_text(gradle.replace(old_version, new_version, 1))

back_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
back = back_p.read_text()
marker = 'm9negative1csignedcal1avirtualbv1ascenefingerprint1bcapturemeter1b'
if marker not in back:
    raise SystemExit('CONSTRAINTSPLIT1A forensic marker anchor missing')
back = back.replace(marker,
        'm9negative1csignedcal1avirtualbv1aconstraintsplit1ascenefingerprint1bcapturemeter1b', 1)
if '1.49-' not in back:
    raise SystemExit('CONSTRAINTSPLIT1A build identity version anchor missing')
back_p.write_text(back.replace('1.49-', '1.50-', 1))

print('M9Cam CONSTRAINTSPLIT1A diagnostic overlay applied')
print(' - VIRTUALBV1A meter request remains independent and frozen')
print(' - existing SIGNEDCAL1A positive headroom becomes an allowance ceiling, not a command')
print(' - existing gated negative candidate may override only a positive meter request')
print(' - FP1B matched-RAW and same-frame RAW oracle constraints are emitted separately')
print(' - capture-sequence correlation is diagnostic state only')
print(' - no Camera2, Photon, FB1, motion, renderer-pixel, JPEG or DNG mutation')

