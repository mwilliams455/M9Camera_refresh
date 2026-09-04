#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-constraintref1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
constraint_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java'
metadata_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
virtual_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
gradle_p = root / 'app/build.gradle'
back_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

for p in (negative_p, constraint_p, metadata_p, virtual_p, gradle_p, back_p):
    if not p.exists():
        raise SystemExit(f'CONSTRAINTREF1A missing expected file: {p}')

negative = negative_p.read_text()
constraint = constraint_p.read_text()
metadata = metadata_p.read_text()
virtual = virtual_p.read_text()
gradle = gradle_p.read_text()
back = back_p.read_text()

if 'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a' not in negative:
    raise SystemExit('CONSTRAINTREF1A requires EXACTID1A M9NEGATIVE source')
if 'm9cam.constraintsplit.v3.virtualbv1a_rawconstraint1b.fix1.exactid1a' not in constraint:
    raise SystemExit('CONSTRAINTREF1A requires EXACTID1A CONSTRAINTSPLIT1A-FIX1')
if 'm9cam.virtualbv.v1' not in virtual:
    raise SystemExit('CONSTRAINTREF1A requires VIRTUALBV1A')
if "versionName '1.52-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b'" not in gradle:
    raise SystemExit('CONSTRAINTREF1A expected 1.52 EXACTID1A versionName missing')

scene_fields_anchor = '''        boolean captureIdentityBound = false;\n'''
scene_fields_repl = '''        boolean captureIdentityBound = false;\n        double photonBaselineEnergyIsoSeconds = Double.NaN;\n        double actualCaptureEnergyIsoSeconds = Double.NaN;\n        double actualCaptureOffsetFromPhotonEv = Double.NaN;\n        double legacyFb1RecommendedEv = Double.NaN;\n        double legacyFb1AppliedEv = Double.NaN;\n        double meterRequestFromPhotonEv = Double.NaN;\n        boolean matchedReferenceAlignedConstraintAvailable = false;\n        double matchedReferenceAlignedConstrainedMeterEv = Double.NaN;\n        boolean conservativeReferenceAlignedConstraintAvailable = false;\n        double conservativeReferenceAlignedConstrainedMeterEv = Double.NaN;\n'''
if scene_fields_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A SceneSignature exact-identity field anchor missing')
negative = negative.replace(scene_fields_anchor, scene_fields_repl, 1)

record_method_anchor = '''    public static synchronized JSONObject recordCompletedRaw(JSONObject renderer,\n'''
reference_method = '''    /**\n     * CONSTRAINTREF1A diagnostic reference binding. The sequence already belongs to the\n     * queued SceneSignature; this method does not alter capture allocation or identity.\n     */\n    public static synchronized boolean noteCaptureReference(long sequence,\n                                                             double photonBaselineEnergyIsoSeconds,\n                                                             double actualCaptureEnergyIsoSeconds,\n                                                             double actualCaptureOffsetFromPhotonEv,\n                                                             double legacyFb1RecommendedEv,\n                                                             double legacyFb1AppliedEv,\n                                                             double meterRequestFromPhotonEv,\n                                                             boolean matchedReferenceAlignedConstraintAvailable,\n                                                             double matchedReferenceAlignedConstrainedMeterEv,\n                                                             boolean conservativeReferenceAlignedConstraintAvailable,\n                                                             double conservativeReferenceAlignedConstrainedMeterEv) {\n        if (sequence <= 0L || !finite(meterRequestFromPhotonEv)) return false;\n        for (SceneSignature scene : PENDING) {\n            if (scene.sequence != sequence) continue;\n            scene.photonBaselineEnergyIsoSeconds = photonBaselineEnergyIsoSeconds;\n            scene.actualCaptureEnergyIsoSeconds = actualCaptureEnergyIsoSeconds;\n            scene.actualCaptureOffsetFromPhotonEv = actualCaptureOffsetFromPhotonEv;\n            scene.legacyFb1RecommendedEv = legacyFb1RecommendedEv;\n            scene.legacyFb1AppliedEv = legacyFb1AppliedEv;\n            scene.meterRequestFromPhotonEv = meterRequestFromPhotonEv;\n            scene.matchedReferenceAlignedConstraintAvailable =\n                    matchedReferenceAlignedConstraintAvailable\n                    && finite(matchedReferenceAlignedConstrainedMeterEv);\n            scene.matchedReferenceAlignedConstrainedMeterEv =\n                    scene.matchedReferenceAlignedConstraintAvailable\n                            ? matchedReferenceAlignedConstrainedMeterEv : Double.NaN;\n            scene.conservativeReferenceAlignedConstraintAvailable =\n                    conservativeReferenceAlignedConstraintAvailable\n                    && finite(conservativeReferenceAlignedConstrainedMeterEv);\n            scene.conservativeReferenceAlignedConstrainedMeterEv =\n                    scene.conservativeReferenceAlignedConstraintAvailable\n                            ? conservativeReferenceAlignedConstrainedMeterEv : Double.NaN;\n            return true;\n        }\n        return false;\n    }\n\n    public static synchronized JSONObject recordCompletedRaw(JSONObject renderer,\n'''
if record_method_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A recordCompletedRaw method anchor missing')
negative = negative.replace(record_method_anchor, reference_method, 1)

envelope_vars_anchor = '''            double strongestMandatoryProtectionEv = 0.0;\n'''
envelope_vars_repl = '''            double strongestMandatoryProtectionEv = 0.0;\n            int passingReferenceAlignedCandidateCount = 0;\n            double conservativePositiveCeilingFromPhotonEv = Double.NaN;\n            boolean conservativeMandatoryCeilingFromPhotonAvailable = false;\n            double conservativeMandatoryCeilingFromPhotonEv = Double.NaN;\n'''
if envelope_vars_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A FIX1 envelope-variable anchor missing')
negative = negative.replace(envelope_vars_anchor, envelope_vars_repl, 1)

passing_block_anchor = '''                if (d <= SIMILAR_SCENE_DISTANCE) {\n                    passingConstraintCandidateCount++;\n                    double allowance = constraintPositiveAllowance(candidate);\n                    if (finite(allowance)) {\n                        conservativePositiveAllowanceEv = finite(conservativePositiveAllowanceEv)\n                                ? Math.min(conservativePositiveAllowanceEv, allowance)\n                                : allowance;\n                    }\n                    double protection = constraintMandatoryProtection(candidate);\n                    if (finite(protection) && protection < 0.0) {\n                        strongestMandatoryProtectionEv =\n                                Math.min(strongestMandatoryProtectionEv, protection);\n                    }\n                }\n'''
passing_block_repl = '''                if (d <= SIMILAR_SCENE_DISTANCE) {\n                    passingConstraintCandidateCount++;\n                    double allowance = constraintPositiveAllowance(candidate);\n                    if (finite(allowance)) {\n                        conservativePositiveAllowanceEv = finite(conservativePositiveAllowanceEv)\n                                ? Math.min(conservativePositiveAllowanceEv, allowance)\n                                : allowance;\n                    }\n                    double protection = constraintMandatoryProtection(candidate);\n                    if (finite(protection) && protection < 0.0) {\n                        strongestMandatoryProtectionEv =\n                                Math.min(strongestMandatoryProtectionEv, protection);\n                    }\n                    double sourceOffset = candidate.scene != null\n                            ? candidate.scene.actualCaptureOffsetFromPhotonEv : Double.NaN;\n                    if (finite(sourceOffset)) {\n                        passingReferenceAlignedCandidateCount++;\n                        if (finite(allowance)) {\n                            double positiveCeiling = sourceOffset + allowance;\n                            conservativePositiveCeilingFromPhotonEv =\n                                    finite(conservativePositiveCeilingFromPhotonEv)\n                                            ? Math.min(conservativePositiveCeilingFromPhotonEv, positiveCeiling)\n                                            : positiveCeiling;\n                        }\n                        if (finite(protection) && protection < 0.0) {\n                            double mandatoryCeiling = sourceOffset + protection;\n                            conservativeMandatoryCeilingFromPhotonEv =\n                                    conservativeMandatoryCeilingFromPhotonAvailable\n                                            ? Math.min(conservativeMandatoryCeilingFromPhotonEv, mandatoryCeiling)\n                                            : mandatoryCeiling;\n                            conservativeMandatoryCeilingFromPhotonAvailable = true;\n                        }\n                    }\n                }\n'''
if passing_block_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A FP1B passing-candidate block anchor missing')
negative = negative.replace(passing_block_anchor, passing_block_repl, 1)

threshold_output_anchor = '''            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n'''
threshold_output_repl = '''            out.put("referenceAlignedPassingCandidateCount",\n                    passingReferenceAlignedCandidateCount);\n            out.put("conservativePositiveCeilingFromPhotonEv",\n                    passingReferenceAlignedCandidateCount > 0\n                            && finite(conservativePositiveCeilingFromPhotonEv)\n                                    ? conservativePositiveCeilingFromPhotonEv : JSONObject.NULL);\n            out.put("conservativeMandatoryCeilingFromPhotonAvailable",\n                    conservativeMandatoryCeilingFromPhotonAvailable);\n            out.put("conservativeMandatoryCeilingFromPhotonEv",\n                    conservativeMandatoryCeilingFromPhotonAvailable\n                            ? conservativeMandatoryCeilingFromPhotonEv : JSONObject.NULL);\n            out.put("referenceAlignmentMeaning",\n                    "source_actual_capture_offset_from_photon_plus_raw_relative_constraint");\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n'''
if threshold_output_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A matched-evaluation threshold output anchor missing')
negative = negative.replace(threshold_output_anchor, threshold_output_repl, 1)

source_age_anchor = '''            out.put("sourceAgeMs", Math.max(0L, nowMs - best.completedEpochMs));\n            out.put("associationPolicy", "recent_scene1h_fingerprint_then_completed_raw");\n'''
source_age_repl = '''            out.put("sourceAgeMs", Math.max(0L, nowMs - best.completedEpochMs));\n            out.put("associationPolicy", "recent_scene1h_fingerprint_then_completed_raw");\n            if (best.scene != null) {\n                putFinite(out, "sourcePhotonBaselineEnergyIsoSeconds",\n                        best.scene.photonBaselineEnergyIsoSeconds);\n                putFinite(out, "sourceActualCaptureEnergyIsoSeconds",\n                        best.scene.actualCaptureEnergyIsoSeconds);\n                putFinite(out, "sourceActualCaptureOffsetFromPhotonEv",\n                        best.scene.actualCaptureOffsetFromPhotonEv);\n                putFinite(out, "sourceLegacyFb1RecommendedEv",\n                        best.scene.legacyFb1RecommendedEv);\n                putFinite(out, "sourceLegacyFb1AppliedEv",\n                        best.scene.legacyFb1AppliedEv);\n                putFinite(out, "sourceMeterRequestFromPhotonEv",\n                        best.scene.meterRequestFromPhotonEv);\n            }\n'''
if source_age_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A matched RAW source-coordinate anchor missing')
negative = negative.replace(source_age_anchor, source_age_repl, 1)

completed_energy_anchor = '''            if (finite(raw.energyIsoSeconds)) out.put("captureExposureEnergyIsoSeconds", raw.energyIsoSeconds);\n            out.put("pendingSceneCount", PENDING.size());\n'''
completed_energy_repl = '''            if (finite(raw.energyIsoSeconds)) out.put("captureExposureEnergyIsoSeconds", raw.energyIsoSeconds);\n            if (scene != null) {\n                putFinite(out, "sourcePhotonBaselineEnergyIsoSeconds",\n                        scene.photonBaselineEnergyIsoSeconds);\n                putFinite(out, "sourceActualCaptureEnergyIsoSeconds",\n                        scene.actualCaptureEnergyIsoSeconds);\n                putFinite(out, "sourceActualCaptureOffsetFromPhotonEv",\n                        scene.actualCaptureOffsetFromPhotonEv);\n                putFinite(out, "sourceLegacyFb1RecommendedEv", scene.legacyFb1RecommendedEv);\n                putFinite(out, "sourceLegacyFb1AppliedEv", scene.legacyFb1AppliedEv);\n                putFinite(out, "sourceMeterRequestFromPhotonEv", scene.meterRequestFromPhotonEv);\n            }\n            out.put("pendingSceneCount", PENDING.size());\n'''
if completed_energy_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A completed RAW coordinate output anchor missing')
negative = negative.replace(completed_energy_anchor, completed_energy_repl, 1)

snapshot_anchor = '''                item.put("captureExposureTimeNs", r.exposureTimeNs);\n                completed.put(item);\n'''
snapshot_repl = '''                item.put("captureExposureTimeNs", r.exposureTimeNs);\n                if (r.scene != null) {\n                    putFinite(item, "sourcePhotonBaselineEnergyIsoSeconds",\n                            r.scene.photonBaselineEnergyIsoSeconds);\n                    putFinite(item, "sourceActualCaptureEnergyIsoSeconds",\n                            r.scene.actualCaptureEnergyIsoSeconds);\n                    putFinite(item, "sourceActualCaptureOffsetFromPhotonEv",\n                            r.scene.actualCaptureOffsetFromPhotonEv);\n                }\n                completed.put(item);\n'''
if snapshot_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A history snapshot coordinate anchor missing')
negative = negative.replace(snapshot_anchor, snapshot_repl, 1)

signed_anchor = '''            JSONObject signedCalibration = buildSignedCalibration(raw, "completed_raw_self");\n            out.put("signedCalibration1A", signedCalibration);\n'''
signed_repl = '''            JSONObject signedCalibration = buildSignedCalibration(raw, "completed_raw_self");\n            out.put("signedCalibration1A", signedCalibration);\n            double sameFrameActualCaptureOffsetFromPhotonEv = Double.NaN;\n            if (scene != null && finite(scene.photonBaselineEnergyIsoSeconds)\n                    && scene.photonBaselineEnergyIsoSeconds > 0.0\n                    && finite(raw.energyIsoSeconds) && raw.energyIsoSeconds > 0.0) {\n                sameFrameActualCaptureOffsetFromPhotonEv =\n                        log2(raw.energyIsoSeconds / scene.photonBaselineEnergyIsoSeconds);\n            } else if (scene != null) {\n                sameFrameActualCaptureOffsetFromPhotonEv =\n                        scene.actualCaptureOffsetFromPhotonEv;\n            }\n            putFinite(out, "sameFrameActualCaptureOffsetFromPhotonEv",\n                    sameFrameActualCaptureOffsetFromPhotonEv);\n'''
if signed_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A same-frame signed-calibration anchor missing')
negative = negative.replace(signed_anchor, signed_repl, 1)

oracle_anchor = '''                    scene != null && scene.envelopeConstraintAvailable,\n                    scene != null ? scene.envelopeConstrainedEv : Double.NaN,\n                    correlationExact));\n'''
oracle_repl = '''                    scene != null && scene.envelopeConstraintAvailable,\n                    scene != null ? scene.envelopeConstrainedEv : Double.NaN,\n                    correlationExact));\n            out.put("m9ConstraintRefOracle", M9ConstraintRef1A.evaluateOracle(\n                    scene != null ? scene.meterRequestFromPhotonEv : Double.NaN,\n                    signedCalibration,\n                    sameFrameActualCaptureOffsetFromPhotonEv,\n                    scene != null ? scene.sequence : -1L,\n                    raw.completedSequence,\n                    scene != null && scene.matchedReferenceAlignedConstraintAvailable,\n                    scene != null ? scene.matchedReferenceAlignedConstrainedMeterEv : Double.NaN,\n                    scene != null && scene.conservativeReferenceAlignedConstraintAvailable,\n                    scene != null ? scene.conservativeReferenceAlignedConstrainedMeterEv : Double.NaN,\n                    correlationExact));\n'''
if oracle_anchor not in negative:
    raise SystemExit('CONSTRAINTREF1A EXACTID oracle-call anchor missing')
negative = negative.replace(oracle_anchor, oracle_repl, 1)
negative_p.write_text(negative)

constraint_ref_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java'
if constraint_ref_p.exists():
    raise SystemExit('CONSTRAINTREF1A target class already exists; refuse ambiguous reapply')
constraint_ref = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/** CONSTRAINTREF1A: diagnostic common EV reference for VirtualBV and completed RAW limits. */
public final class M9ConstraintRef1A {
    public static final String SCHEMA = "m9cam.constraintref.v1";
    private static final double DIRECTION_DEADBAND_EV = 0.08;
    private M9ConstraintRef1A() {}

    public static JSONObject evaluateCapture(JSONObject root) {
        JSONObject out = contract();
        try {
            out.put("phase", "capture_reference_alignment_previous_fp1b_raw");
            JSONObject virtual = root != null ? root.optJSONObject("m9VirtualBv") : null;
            JSONObject legacy = root != null ? root.optJSONObject("m9ConstraintSplit") : null;
            if (virtual == null || legacy == null) { invalid(out, "virtualbv_or_legacy_constraintsplit_missing"); return out; }
            double meter = virtual.optDouble("signedMeterDeltaEv", Double.NaN);
            double photonIso = virtual.optDouble("photonReferenceIso", Double.NaN);
            long photonNs = virtual.optLong("photonReferenceExposureNs", 0L);
            double actualIso = virtual.optDouble("actualCaptureIso", Double.NaN);
            long actualNs = virtual.optLong("actualCaptureExposureNs", 0L);
            if ((!finite(actualIso) || actualIso <= 0.0 || actualNs <= 0L) && root != null) {
                JSONObject cr = root.optJSONObject("captureResult");
                if (cr != null) { actualIso = cr.optDouble("iso", Double.NaN); actualNs = cr.optLong("exposureTimeNs", 0L); }
            }
            double photonEnergy = energy(photonIso, photonNs);
            double actualEnergy = energy(actualIso, actualNs);
            double actualOffset = finite(photonEnergy) && photonEnergy > 0.0 && finite(actualEnergy) && actualEnergy > 0.0
                    ? log2(actualEnergy / photonEnergy) : Double.NaN;
            double fb1Recommended = virtual.optDouble("luma24RecommendedEv", Double.NaN);
            double fb1Applied = virtual.optDouble("luma24AppliedEv", Double.NaN);
            if (!finite(fb1Applied)) fb1Applied = 0.0;
            out.put("photonBaselineEnergyIsoSeconds", finite(photonEnergy) ? photonEnergy : JSONObject.NULL);
            out.put("actualCaptureEnergyIsoSeconds", finite(actualEnergy) ? actualEnergy : JSONObject.NULL);
            out.put("actualCaptureOffsetFromPhotonEv", finite(actualOffset) ? actualOffset : JSONObject.NULL);
            out.put("legacyFb1RecommendedEv", finite(fb1Recommended) ? fb1Recommended : JSONObject.NULL);
            out.put("legacyFb1AppliedEv", fb1Applied);
            out.put("meterRequestFromPhotonEv", finite(meter) ? meter : JSONObject.NULL);
            double residual = finite(meter) ? meter - fb1Applied : Double.NaN;
            out.put("meterResidualAfterLegacyFb1Ev", finite(residual) ? residual : JSONObject.NULL);

            JSONObject scene = root.optJSONObject("m9SceneExposureDiagnostic");
            JSONObject split = scene != null ? scene.optJSONObject("captureRenderSplit") : null;
            JSONObject matched = split != null ? split.optJSONObject("m9Negative1A") : null;
            long captureSequence = legacy.optLong("captureSequence", -1L);
            boolean matchedAvailable = legacy.optBoolean("matchedRawFeedbackAvailable", false);
            double rawAllowance = legacy.optDouble("matchedRawPositiveAllowanceEv", Double.NaN);
            double rawProtection = legacy.optDouble("matchedRawMandatoryProtectionEv", Double.NaN);
            double sourceOffset = matched != null ? matched.optDouble("sourceActualCaptureOffsetFromPhotonEv", Double.NaN) : Double.NaN;
            boolean posAvailable = matchedAvailable && finite(sourceOffset) && finite(rawAllowance);
            double posCeiling = posAvailable ? sourceOffset + rawAllowance : Double.NaN;
            boolean mandAvailable = matchedAvailable && finite(sourceOffset) && finite(rawProtection) && rawProtection < 0.0;
            double mandCeiling = mandAvailable ? sourceOffset + rawProtection : Double.NaN;
            AlignedConstraint matchedResult = finite(meter) && matchedAvailable
                    ? constrainAligned(meter, posAvailable, posCeiling, mandAvailable, mandCeiling, "matched_fp1b")
                    : AlignedConstraint.noRaw(meter, "matched_reference_aligned_raw_unavailable");
            out.put("matchedRawAvailable", matchedAvailable);
            out.put("matchedRawSourceCaptureSequence", matchedAvailable && legacy.has("matchedRawSourceCaptureSequence") ? legacy.optLong("matchedRawSourceCaptureSequence") : JSONObject.NULL);
            out.put("matchedRawSourceCompletedSequence", matchedAvailable && legacy.has("matchedRawSourceCompletedSequence") ? legacy.optLong("matchedRawSourceCompletedSequence") : JSONObject.NULL);
            putFinite(out, "matchedRawSceneDistance", legacy.optDouble("matchedRawSceneDistance", Double.NaN));
            putFinite(out, "matchedRawPositiveAllowanceFromActualEv", rawAllowance);
            putFinite(out, "matchedRawMandatoryProtectionFromActualEv", rawProtection);
            putFinite(out, "matchedRawSourceActualCaptureOffsetFromPhotonEv", sourceOffset);
            putFinite(out, "matchedSensorPositiveCeilingFromPhotonEv", posCeiling);
            out.put("matchedSensorMandatoryCeilingFromPhotonAvailable", mandAvailable);
            putFinite(out, "matchedSensorMandatoryCeilingFromPhotonEv", mandCeiling);
            putFinite(out, "matchedReferenceAlignedConstrainedMeterEv", matchedResult.constrainedEv);
            out.put("matchedReferenceAlignedConstraintReason", matchedResult.reason);

            int alignedCount = matched != null ? matched.optInt("referenceAlignedPassingCandidateCount", 0) : 0;
            double envPos = matched != null ? matched.optDouble("conservativePositiveCeilingFromPhotonEv", Double.NaN) : Double.NaN;
            boolean envMandAvailable = matched != null && matched.optBoolean("conservativeMandatoryCeilingFromPhotonAvailable", false);
            double envMand = matched != null ? matched.optDouble("conservativeMandatoryCeilingFromPhotonEv", Double.NaN) : Double.NaN;
            boolean envAvailable = alignedCount > 0 && finite(envPos);
            AlignedConstraint envResult = finite(meter) && envAvailable
                    ? constrainAligned(meter, true, envPos, envMandAvailable && finite(envMand), envMand, "conservative_fp1b_envelope")
                    : AlignedConstraint.noRaw(meter, "conservative_reference_aligned_envelope_unavailable");
            out.put("conservativeEnvelopeReferenceAlignedCandidateCount", alignedCount);
            putFinite(out, "conservativeEnvelopePositiveCeilingFromPhotonEv", envPos);
            out.put("conservativeEnvelopeMandatoryCeilingFromPhotonAvailable", envMandAvailable && finite(envMand));
            putFinite(out, "conservativeEnvelopeMandatoryCeilingFromPhotonEv", envMand);
            putFinite(out, "conservativeReferenceAlignedConstrainedMeterEv", envResult.constrainedEv);
            out.put("conservativeReferenceAlignedConstraintReason", envResult.reason);

            JSONObject legacyRawRelative = new JSONObject();
            putFinite(legacyRawRelative, "positiveAllowanceFromActualEv", rawAllowance);
            putFinite(legacyRawRelative, "mandatoryProtectionFromActualEv", rawProtection);
            putFinite(legacyRawRelative, "oldConstrainedMeterRequestEv", legacy.optDouble("matchedRawConstrainedMeterRequestEv", Double.NaN));
            putFinite(legacyRawRelative, "oldNearestConstrainedMeterRequestEv", legacy.optDouble("nearestRawConstrainedMeterRequestEv", Double.NaN));
            legacyRawRelative.put("meaning", "legacy_diagnostic_mixed_zero_points_retained_for_comparison_only");
            out.put("legacyRawRelativeConstraint", legacyRawRelative);

            double architectureA = finite(matchedResult.constrainedEv) ? matchedResult.constrainedEv : meter;
            out.put("architectureAReplaceFb1ResultEv", finite(architectureA) ? architectureA : JSONObject.NULL);
            out.put("architectureAPath", "photon_baseline_to_virtualbv_then_reference_aligned_sensor_constraint");
            double residualPos = posAvailable ? posCeiling - fb1Applied : Double.NaN;
            double residualMand = mandAvailable ? mandCeiling - fb1Applied : Double.NaN;
            AlignedConstraint residualResult = finite(residual)
                    ? constrainAligned(residual, posAvailable, residualPos, mandAvailable, residualMand, "residual_after_legacy_fb1")
                    : AlignedConstraint.noRaw(Double.NaN, "legacy_fb1_residual_unavailable");
            double architectureB = finite(residualResult.constrainedEv) ? fb1Applied + residualResult.constrainedEv : Double.NaN;
            out.put("architectureBResidualMeterEv", finite(residualResult.constrainedEv) ? residualResult.constrainedEv : JSONObject.NULL);
            out.put("architectureBResidualAfterFb1ResultEv", finite(architectureB) ? architectureB : JSONObject.NULL);
            out.put("architectureBPath", "legacy_fb1_then_virtualbv_residual_with_sensor_constraint_in_residual_coordinates");
            out.put("naiveStackedFb1PlusVirtualBvEv", finite(meter) ? fb1Applied + meter : JSONObject.NULL);

            boolean stored = M9NegativeFeedback1A.noteCaptureReference(captureSequence, photonEnergy, actualEnergy, actualOffset,
                    fb1Recommended, fb1Applied, meter,
                    matchedAvailable && finite(matchedResult.constrainedEv), matchedResult.constrainedEv,
                    envAvailable && finite(envResult.constrainedEv), envResult.constrainedEv);
            out.put("captureSequence", captureSequence > 0L ? captureSequence : JSONObject.NULL);
            out.put("referenceStateStoredForExactRaw", stored);
            out.put("valid", finite(meter) && finite(actualOffset));
            out.put("reason", finite(meter) && finite(actualOffset)
                    ? "reference_aligned_constraints_recorded_no_live_exposure_change"
                    : "reference_alignment_inputs_incomplete_no_live_exposure_change");
        } catch (Throwable t) {
            try { invalid(out, "constraintref_capture_exception"); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    public static JSONObject evaluateOracle(double meterRequestFromPhotonEv, JSONObject sameFrameSignedCalibration,
                                            double sameFrameActualCaptureOffsetFromPhotonEv,
                                            long captureSequence, long completedSequence,
                                            boolean matchedConstraintAvailable, double matchedReferenceAlignedConstrainedMeterEv,
                                            boolean conservativeConstraintAvailable, double conservativeReferenceAlignedConstrainedMeterEv,
                                            boolean captureCorrelationExact) {
        JSONObject out = contract();
        try {
            out.put("phase", "same_frame_reference_aligned_raw_oracle");
            out.put("captureSequence", captureSequence > 0L ? captureSequence : JSONObject.NULL);
            out.put("completedSequence", completedSequence > 0L ? completedSequence : JSONObject.NULL);
            out.put("captureCorrelationExact", captureCorrelationExact);
            out.put("oracleComparisonAccepted", captureCorrelationExact);
            putFinite(out, "meterRequestFromPhotonEv", meterRequestFromPhotonEv);
            putFinite(out, "sameFrameActualCaptureOffsetFromPhotonEv", sameFrameActualCaptureOffsetFromPhotonEv);
            boolean validSigned = sameFrameSignedCalibration != null && sameFrameSignedCalibration.optBoolean("valid", false);
            double allowance = validSigned ? sameFrameSignedCalibration.optDouble("additionalCaptureHeadroomEv", Double.NaN) : Double.NaN;
            boolean negativeGate = validSigned && sameFrameSignedCalibration.optBoolean("negativeGatePass", false);
            double protection = negativeGate ? sameFrameSignedCalibration.optDouble("negativeCandidateAppliedByFrozenGateEv", Double.NaN) : 0.0;
            boolean baseValid = captureCorrelationExact && finite(meterRequestFromPhotonEv)
                    && finite(sameFrameActualCaptureOffsetFromPhotonEv) && validSigned;
            boolean posAvailable = baseValid && finite(allowance);
            double posCeiling = posAvailable ? sameFrameActualCaptureOffsetFromPhotonEv + Math.max(0.0, allowance) : Double.NaN;
            boolean mandAvailable = baseValid && finite(protection) && protection < 0.0;
            double mandCeiling = mandAvailable ? sameFrameActualCaptureOffsetFromPhotonEv + protection : Double.NaN;
            AlignedConstraint oracle = baseValid
                    ? constrainAligned(meterRequestFromPhotonEv, posAvailable, posCeiling, mandAvailable, mandCeiling, "same_frame_oracle")
                    : AlignedConstraint.noRaw(meterRequestFromPhotonEv, "same_frame_reference_oracle_inputs_invalid_or_not_exact");
            putFinite(out, "sameFrameOraclePositiveAllowanceFromActualEv", allowance);
            putFinite(out, "sameFrameOracleMandatoryProtectionFromActualEv", protection);
            putFinite(out, "sameFrameSensorPositiveCeilingFromPhotonEv", posCeiling);
            out.put("sameFrameSensorMandatoryCeilingFromPhotonAvailable", mandAvailable);
            putFinite(out, "sameFrameSensorMandatoryCeilingFromPhotonEv", mandCeiling);
            putFinite(out, "sameFrameReferenceAlignedConstrainedMeterEv", oracle.constrainedEv);
            out.put("sameFrameReferenceAlignedConstraintReason", oracle.reason);
            out.put("matchedReferenceAlignedConstraintAvailable", matchedConstraintAvailable && finite(matchedReferenceAlignedConstrainedMeterEv));
            if (matchedConstraintAvailable && finite(matchedReferenceAlignedConstrainedMeterEv) && finite(oracle.constrainedEv)) {
                out.put("matchedVsOracleReferenceAlignedDeltaEv", matchedReferenceAlignedConstrainedMeterEv - oracle.constrainedEv);
                out.put("matchedVsOracleReferenceAlignedDirectionAgreement", direction(matchedReferenceAlignedConstrainedMeterEv).equals(direction(oracle.constrainedEv)));
            } else {
                out.put("matchedVsOracleReferenceAlignedDeltaEv", JSONObject.NULL);
                out.put("matchedVsOracleReferenceAlignedDirectionAgreement", JSONObject.NULL);
            }
            out.put("conservativeReferenceAlignedConstraintAvailable", conservativeConstraintAvailable && finite(conservativeReferenceAlignedConstrainedMeterEv));
            if (conservativeConstraintAvailable && finite(conservativeReferenceAlignedConstrainedMeterEv) && finite(oracle.constrainedEv)) {
                out.put("conservativeVsOracleReferenceAlignedDeltaEv", conservativeReferenceAlignedConstrainedMeterEv - oracle.constrainedEv);
                out.put("conservativeVsOracleReferenceAlignedDirectionAgreement", direction(conservativeReferenceAlignedConstrainedMeterEv).equals(direction(oracle.constrainedEv)));
            } else {
                out.put("conservativeVsOracleReferenceAlignedDeltaEv", JSONObject.NULL);
                out.put("conservativeVsOracleReferenceAlignedDirectionAgreement", JSONObject.NULL);
            }
            out.put("directionAgreement", finite(oracle.constrainedEv) && finite(meterRequestFromPhotonEv)
                    ? direction(oracle.constrainedEv).equals(direction(meterRequestFromPhotonEv)) : JSONObject.NULL);
            out.put("valid", baseValid && finite(oracle.constrainedEv));
            out.put("reason", baseValid ? "same_frame_reference_aligned_oracle_recorded_exact_identity"
                    : captureCorrelationExact ? "same_frame_reference_oracle_inputs_incomplete"
                    : "same_frame_reference_oracle_rejected_identity_not_exact");
        } catch (Throwable t) {
            try { invalid(out, "constraintref_oracle_exception"); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    private static AlignedConstraint constrainAligned(double meterRequestFromPhotonEv,
                                                       boolean positiveCeilingAvailable, double positiveCeilingFromPhotonEv,
                                                       boolean mandatoryCeilingAvailable, double mandatoryCeilingFromPhotonEv,
                                                       String source) {
        if (!finite(meterRequestFromPhotonEv)) return AlignedConstraint.noRaw(Double.NaN, source + "_meter_missing");
        if (mandatoryCeilingAvailable && finite(mandatoryCeilingFromPhotonEv)) {
            double constrained = Math.min(meterRequestFromPhotonEv, mandatoryCeilingFromPhotonEv);
            return new AlignedConstraint(constrained, constrained + 1e-12 < meterRequestFromPhotonEv
                    ? source + "_mandatory_ceiling_limited_meter" : source + "_meter_already_at_or_below_mandatory_ceiling");
        }
        if (meterRequestFromPhotonEv > 0.0 && positiveCeilingAvailable && finite(positiveCeilingFromPhotonEv)) {
            double constrained = Math.min(meterRequestFromPhotonEv, positiveCeilingFromPhotonEv);
            return new AlignedConstraint(constrained, constrained + 1e-12 < meterRequestFromPhotonEv
                    ? source + "_positive_ceiling_limited_meter" : source + "_positive_meter_within_sensor_ceiling");
        }
        return new AlignedConstraint(meterRequestFromPhotonEv, source + "_meter_preserved");
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA); out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false); out.put("usedToMutateCaptureTarget", false);
            out.put("referenceFrame", "photon_pre_fb1_exposure_baseline");
            out.put("rawConstraintReferenceFrame", "actual_captured_raw");
            out.put("conversionRule", "sensor_ceiling_from_photon_ev_equals_source_actual_capture_offset_plus_raw_relative_constraint");
            out.put("meterModelFrozen", "VIRTUALBV1A"); out.put("sensorConstraintModelFrozen", "SIGNEDCAL1A_M9NEGATIVE1C");
            out.put("sceneAssociationFrozen", "SCENEFINGERPRINT1B"); out.put("identityCorrelationFrozen", "EXACTID1A");
        } catch (Exception ignored) {}
        return out;
    }
    private static double energy(double iso, long exposureNs) {
        if (!finite(iso) || iso <= 0.0 || exposureNs <= 0L) return Double.NaN;
        return iso * (exposureNs / 1_000_000_000.0);
    }
    private static void putFinite(JSONObject out, String key, double value) {
        try { out.put(key, finite(value) ? value : JSONObject.NULL); } catch (Exception ignored) {}
    }
    private static void invalid(JSONObject out, String reason) {
        try { out.put("valid", false); out.put("liveEligible", false); out.put("usedToMutateCaptureTarget", false); out.put("reason", reason); } catch (Exception ignored) {}
    }
    private static String direction(double ev) {
        if (!finite(ev)) return "invalid";
        if (Math.abs(ev) < DIRECTION_DEADBAND_EV) return "neutral";
        return ev > 0.0 ? "increase" : "decrease";
    }
    private static boolean finite(double x) { return !Double.isNaN(x) && !Double.isInfinite(x); }
    private static double log2(double x) { return Math.log(Math.max(x, 1e-12)) / Math.log(2.0); }
    private static final class AlignedConstraint {
        final double constrainedEv; final String reason;
        AlignedConstraint(double constrainedEv, String reason) { this.constrainedEv = constrainedEv; this.reason = reason; }
        static AlignedConstraint noRaw(double meter, String reason) { return new AlignedConstraint(meter, reason); }
    }
}
'''
constraint_ref_p.write_text(constraint_ref)

metadata_anchor = '''            root.put("m9VirtualBv", m9VirtualBv);\n            root.put("m9ConstraintSplit", M9ConstraintSplit1A.evaluateCapture(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
metadata_repl = '''            root.put("m9VirtualBv", m9VirtualBv);\n            JSONObject m9ConstraintSplit = M9ConstraintSplit1A.evaluateCapture(root);\n            root.put("m9ConstraintSplit", m9ConstraintSplit);\n            root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if metadata_anchor not in metadata:
    raise SystemExit('CONSTRAINTREF1A metadata publication anchor missing')
metadata_p.write_text(metadata.replace(metadata_anchor, metadata_repl, 1))

old_version = "versionName '1.52-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b'"
new_version = "versionName '1.53-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b-cr1a'"
gradle_p.write_text(gradle.replace(old_version, new_version, 1))
old_marker = 'virtualbv1aconstraintsplit1afix1exactid1ascenefingerprint1b'
new_marker = 'virtualbv1aconstraintsplit1afix1exactid1aconstraintref1ascenefingerprint1b'
if old_marker not in back:
    raise SystemExit('CONSTRAINTREF1A forensic marker anchor missing')
back = back.replace(old_marker, new_marker, 1)
if '1.52-' not in back:
    raise SystemExit('CONSTRAINTREF1A backlight version identity anchor missing')
back_p.write_text(back.replace('1.52-', '1.53-', 1))

print('M9Cam CONSTRAINTREF1A diagnostic reference alignment applied')
print(' - Photon/pre-FB1 meter zero point is explicit and frozen')
print(' - historical and same-frame RAW constraints translated from actual-capture EV to Photon EV')
print(' - legacy raw-relative CONSTRAINTSPLIT1A/FIX1 retained side by side')
print(' - FP1B and EXACTID1A unchanged; no Camera2, FB1, renderer, JPEG or DNG mutation')
