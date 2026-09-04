#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-exactid1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
constraint_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java'
renderer_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_p = root / 'app/build.gradle'
back_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

negative = negative_p.read_text()
constraint = constraint_p.read_text()
renderer = renderer_p.read_text()
gradle = gradle_p.read_text()
back = back_p.read_text()

if 'm9cam.constraintsplit.v2.virtualbv1a_rawconstraint1b.fix1' not in constraint:
    raise SystemExit('EXACTID1A requires CONSTRAINTSPLIT1A-FIX1')
if 'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a' not in negative:
    raise SystemExit('EXACTID1A requires M9NEGATIVE1C / FP1B / SIGNEDCAL1A')
if "versionName '1.51-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-cm1b'" not in gradle:
    raise SystemExit('EXACTID1A expected 1.51 FIX1 versionName missing')

import_anchor = '''import java.util.Deque;\nimport java.util.List;\n'''
import_repl = '''import java.util.Deque;\nimport java.util.Iterator;\nimport java.util.List;\nimport java.nio.file.Path;\n'''
if import_anchor not in negative:
    raise SystemExit('EXACTID1A negative imports anchor missing')
negative = negative.replace(import_anchor, import_repl, 1)

note_sig_anchor = '''    public static synchronized boolean noteCaptureConstraint(long sequence,\n                                                             double meterRequestEv,\n                                                             boolean matchedConstraintAvailable,\n                                                             double matchedConstrainedEv,\n                                                             boolean envelopeConstraintAvailable,\n                                                             double envelopeConstrainedEv) {\n'''
note_sig_repl = '''    public static synchronized boolean noteCaptureConstraint(long sequence,\n                                                             double meterRequestEv,\n                                                             boolean matchedConstraintAvailable,\n                                                             double matchedConstrainedEv,\n                                                             boolean envelopeConstraintAvailable,\n                                                             double envelopeConstrainedEv,\n                                                             String captureIdentity,\n                                                             long rawTimestampNs) {\n'''
if note_sig_anchor not in negative:
    raise SystemExit('EXACTID1A noteCaptureConstraint signature anchor missing')
negative = negative.replace(note_sig_anchor, note_sig_repl, 1)

note_body_anchor = '''            scene.envelopeConstrainedEv = scene.envelopeConstraintAvailable\n                    ? envelopeConstrainedEv : Double.NaN;\n            return true;\n'''
note_body_repl = '''            scene.envelopeConstrainedEv = scene.envelopeConstraintAvailable\n                    ? envelopeConstrainedEv : Double.NaN;\n            scene.captureIdentity = normalizeCaptureIdentity(captureIdentity);\n            scene.rawTimestampNs = rawTimestampNs > 0L ? rawTimestampNs : -1L;\n            scene.captureIdentityBound = scene.captureIdentity != null\n                    && scene.rawTimestampNs > 0L;\n            return true;\n'''
if note_body_anchor not in negative:
    raise SystemExit('EXACTID1A capture identity bind anchor missing')
negative = negative.replace(note_body_anchor, note_body_repl, 1)

scene_fields_anchor = '''        boolean envelopeConstraintAvailable = false;\n        double envelopeConstrainedEv = Double.NaN;\n'''
scene_fields_repl = '''        boolean envelopeConstraintAvailable = false;\n        double envelopeConstrainedEv = Double.NaN;\n        String captureIdentity = null;\n        long rawTimestampNs = -1L;\n        boolean captureIdentityBound = false;\n'''
if scene_fields_anchor not in negative:
    raise SystemExit('EXACTID1A SceneSignature identity fields anchor missing')
negative = negative.replace(scene_fields_anchor, scene_fields_repl, 1)

record_sig_anchor = '''    public static synchronized JSONObject recordCompletedRaw(JSONObject renderer,\n                                                             int iso,\n                                                             long exposureTimeNs) {\n'''
record_sig_repl = '''    public static synchronized JSONObject recordCompletedRaw(JSONObject renderer,\n                                                             int iso,\n                                                             long exposureTimeNs,\n                                                             Path dngPath,\n                                                             long rawTimestampNs) {\n'''
if record_sig_anchor not in negative:
    raise SystemExit('EXACTID1A completed RAW signature anchor missing')
negative = negative.replace(record_sig_anchor, record_sig_repl, 1)

poll_anchor = '''            SceneSignature scene = PENDING.pollFirst();\n            if (renderer == null) {\n'''
poll_repl = '''            String completedCaptureIdentity = normalizeCaptureIdentity(\n                    dngPath != null ? dngPath.getFileName().toString() : null);\n            SceneSignature scene = null;\n            SceneSignature fifoFallback = PENDING.peekFirst();\n            int orphanUnboundPrunedCount = 0;\n            if (completedCaptureIdentity != null && rawTimestampNs > 0L) {\n                for (Iterator<SceneSignature> it = PENDING.iterator(); it.hasNext();) {\n                    SceneSignature candidate = it.next();\n                    if (!candidate.captureIdentityBound) continue;\n                    if (!completedCaptureIdentity.equals(candidate.captureIdentity)) continue;\n                    if (candidate.rawTimestampNs != rawTimestampNs) continue;\n                    scene = candidate;\n                    it.remove();\n                    break;\n                }\n            }\n            boolean correlationExact = scene != null;\n            if (correlationExact) {\n                for (Iterator<SceneSignature> it = PENDING.iterator(); it.hasNext();) {\n                    SceneSignature candidate = it.next();\n                    if (!candidate.captureIdentityBound && candidate.sequence < scene.sequence) {\n                        it.remove();\n                        orphanUnboundPrunedCount++;\n                    }\n                }\n            }\n            if (renderer == null) {\n'''
if poll_anchor not in negative:
    raise SystemExit('EXACTID1A FIFO association anchor missing')
negative = negative.replace(poll_anchor, poll_repl, 1)

record_output_anchor = '''            out.put("completedSequence", raw.completedSequence);\n            out.put("captureSequence", scene != null ? scene.sequence : JSONObject.NULL);\n            out.put("sceneAssociationPresent", scene != null);\n            out.put("associationMode", "capture_step_fifo_to_primary_render_completion");\n            out.put("rawUq25", q25);\n'''
record_output_repl = '''            out.put("completedSequence", raw.completedSequence);\n            out.put("captureSequence", scene != null ? scene.sequence : JSONObject.NULL);\n            out.put("sceneAssociationPresent", correlationExact);\n            out.put("correlationExact", correlationExact);\n            out.put("associationMode", correlationExact\n                    ? "exact_dng_filename_plus_raw_timestamp"\n                    : "exact_identity_missing_fifo_diagnostic_only");\n            out.put("completedCaptureIdentity",\n                    completedCaptureIdentity != null\n                            ? completedCaptureIdentity : JSONObject.NULL);\n            out.put("completedRawTimestampNs",\n                    rawTimestampNs > 0L ? rawTimestampNs : JSONObject.NULL);\n            out.put("matchedCaptureIdentity",\n                    scene != null && scene.captureIdentity != null\n                            ? scene.captureIdentity : JSONObject.NULL);\n            out.put("matchedCaptureRawTimestampNs",\n                    scene != null && scene.rawTimestampNs > 0L\n                            ? scene.rawTimestampNs : JSONObject.NULL);\n            out.put("fifoFallbackCaptureSequence",\n                    !correlationExact && fifoFallback != null\n                            ? fifoFallback.sequence : JSONObject.NULL);\n            out.put("fifoFallbackUsedForHistory", false);\n            out.put("orphanUnboundPrunedCount", orphanUnboundPrunedCount);\n            out.put("rawUq25", q25);\n'''
if record_output_anchor not in negative:
    raise SystemExit('EXACTID1A completed RAW output anchor missing')
negative = negative.replace(record_output_anchor, record_output_repl, 1)

reason_anchor = '''            out.put("reason", scene != null\n                    ? "completed_raw_recorded_with_capture_scene_signature"\n                    : "completed_raw_recorded_without_scene_signature");\n'''
reason_repl = '''            out.put("reason", correlationExact\n                    ? "completed_raw_recorded_with_exact_capture_identity"\n                    : "completed_raw_recorded_without_exact_capture_identity_no_history_association");\n'''
if reason_anchor not in negative:
    raise SystemExit('EXACTID1A completed RAW reason anchor missing')
negative = negative.replace(reason_anchor, reason_repl, 1)

oracle_call_anchor = '''                    scene != null && scene.envelopeConstraintAvailable,\n                    scene != null ? scene.envelopeConstrainedEv : Double.NaN));\n'''
oracle_call_repl = '''                    scene != null && scene.envelopeConstraintAvailable,\n                    scene != null ? scene.envelopeConstrainedEv : Double.NaN,\n                    correlationExact));\n'''
if oracle_call_anchor not in negative:
    raise SystemExit('EXACTID1A oracle call correlation anchor missing')
negative = negative.replace(oracle_call_anchor, oracle_call_repl, 1)

helper_anchor = '''    private static double normalizedDelta(double a, double b, double scale) {\n'''
helper_repl = '''    private static String normalizeCaptureIdentity(String identity) {\n        if (identity == null) return null;\n        String s = identity.trim().replace('\\\\', '/');\n        if (s.isEmpty()) return null;\n        int slash = s.lastIndexOf('/');\n        if (slash >= 0 && slash + 1 < s.length()) s = s.substring(slash + 1);\n        return s.isEmpty() ? null : s;\n    }\n\n    private static double normalizedDelta(double a, double b, double scale) {\n'''
if helper_anchor not in negative:
    raise SystemExit('EXACTID1A identity normalizer anchor missing')
negative = negative.replace(helper_anchor, helper_repl, 1)

negative = negative.replace(
        'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a',
        'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a', 1)

constraint_note_anchor = '''            boolean stored = M9NegativeFeedback1A.noteCaptureConstraint(\n                    captureSequence, meterRequestEv, feedbackAvailable, result.constrainedEv,\n                    envelopeConstraintAvailable, envelopeResult.constrainedEv);\n            out.put("captureSequence", captureSequence > 0L\n                    ? captureSequence : JSONObject.NULL);\n            out.put("completionCorrelationStored", stored);\n'''
constraint_note_repl = '''            String captureIdentity = root != null\n                    ? root.optString("dng", "") : "";\n            JSONObject rawIdentity = root != null ? root.optJSONObject("raw") : null;\n            long captureRawTimestampNs = rawIdentity != null\n                    ? rawIdentity.optLong("timestampNs", -1L) : -1L;\n            boolean captureIdentityReady = captureIdentity != null\n                    && !captureIdentity.isEmpty()\n                    && captureRawTimestampNs > 0L;\n            boolean stored = M9NegativeFeedback1A.noteCaptureConstraint(\n                    captureSequence, meterRequestEv, feedbackAvailable, result.constrainedEv,\n                    envelopeConstraintAvailable, envelopeResult.constrainedEv,\n                    captureIdentityReady ? captureIdentity : null,\n                    captureIdentityReady ? captureRawTimestampNs : -1L);\n            out.put("captureSequence", captureSequence > 0L\n                    ? captureSequence : JSONObject.NULL);\n            out.put("captureIdentity",\n                    captureIdentityReady ? captureIdentity : JSONObject.NULL);\n            out.put("captureRawTimestampNs",\n                    captureIdentityReady ? captureRawTimestampNs : JSONObject.NULL);\n            out.put("captureIdentityReady", captureIdentityReady);\n            out.put("completionCorrelationStored", stored);\n            out.put("completionCorrelationExactIdentityBound",\n                    stored && captureIdentityReady);\n'''
if constraint_note_anchor not in constraint:
    raise SystemExit('EXACTID1A constraint capture identity anchor missing')
constraint = constraint.replace(constraint_note_anchor, constraint_note_repl, 1)

oracle_sig_anchor = '''                                            boolean envelopeConstraintAvailable,\n                                            double envelopeConstrainedEv) {\n'''
oracle_sig_repl = '''                                            boolean envelopeConstraintAvailable,\n                                            double envelopeConstrainedEv,\n                                            boolean captureCorrelationExact) {\n'''
if oracle_sig_anchor not in constraint:
    raise SystemExit('EXACTID1A oracle signature anchor missing')
constraint = constraint.replace(oracle_sig_anchor, oracle_sig_repl, 1)

meter_available_anchor = '''            boolean meterAvailable = finite(meterRequestEv);\n            out.put("meterRequestAvailable", meterAvailable);\n'''
meter_available_repl = '''            out.put("captureCorrelationExact", captureCorrelationExact);\n            out.put("oracleComparisonAccepted", captureCorrelationExact);\n            boolean meterAvailable = captureCorrelationExact && finite(meterRequestEv);\n            out.put("meterRequestAvailable", meterAvailable);\n'''
if meter_available_anchor not in constraint:
    raise SystemExit('EXACTID1A oracle exact-gate anchor missing')
constraint = constraint.replace(meter_available_anchor, meter_available_repl, 1)

reason_oracle_anchor = '''            out.put("reason", meterAvailable\n                    ? "same_frame_raw_oracle_constraint_recorded_no_live_exposure_change"\n                    : "same_frame_raw_recorded_but_capture_meter_request_not_correlated");\n'''
reason_oracle_repl = '''            out.put("reason", meterAvailable\n                    ? "same_frame_raw_oracle_constraint_recorded_exact_identity_no_live_exposure_change"\n                    : captureCorrelationExact\n                    ? "same_frame_raw_exact_identity_but_capture_meter_request_missing"\n                    : "same_frame_raw_oracle_rejected_capture_identity_not_exact");\n'''
if reason_oracle_anchor not in constraint:
    raise SystemExit('EXACTID1A oracle reason anchor missing')
constraint = constraint.replace(reason_oracle_anchor, reason_oracle_repl, 1)

constraint = constraint.replace(
        'm9cam.constraintsplit.v2.virtualbv1a_rawconstraint1b.fix1',
        'm9cam.constraintsplit.v3.virtualbv1a_rawconstraint1b.fix1.exactid1a', 1)

renderer_call_anchor = '''                diag.put("m9NegativeCompletedRawFeedback",\n                        M9NegativeFeedback1A.recordCompletedRaw(diag, iso, exposureTimeNs));\n'''
renderer_call_repl = '''                diag.put("m9NegativeCompletedRawFeedback",\n                        M9NegativeFeedback1A.recordCompletedRaw(\n                                diag, iso, exposureTimeNs, dngPath,\n                                frame != null ? frame.timestamp : -1L));\n'''
if renderer_call_anchor not in renderer:
    raise SystemExit('EXACTID1A renderer completed-RAW call anchor missing')
renderer = renderer.replace(renderer_call_anchor, renderer_call_repl, 1)

old_version = "versionName '1.51-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-cm1b'"
new_version = "versionName '1.52-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b'"
gradle = gradle.replace(old_version, new_version, 1)

old_marker = 'virtualbv1aconstraintsplit1afix1scenefingerprint1b'
new_marker = 'virtualbv1aconstraintsplit1afix1exactid1ascenefingerprint1b'
if old_marker not in back:
    raise SystemExit('EXACTID1A forensic marker anchor missing')
back = back.replace(old_marker, new_marker, 1)
if '1.51-' not in back:
    raise SystemExit('EXACTID1A build identity version anchor missing')
back = back.replace('1.51-', '1.52-', 1)

negative_p.write_text(negative)
constraint_p.write_text(constraint)
renderer_p.write_text(renderer)
gradle_p.write_text(gradle)
back_p.write_text(back)

print('M9Cam EXACTID1A diagnostic correlation overlay applied')
print(' - capture scene binds to unique DNG basename + exact ImageFrame timestamp')
print(' - completed primary RAW searches exact identity instead of consuming FIFO')
print(' - FIFO retained only as explicit diagnostic fallback; never enters RAW history/oracle')
print(' - older unbound duplicate diagnostic scenes are pruned after an exact completion')
print(' - same-frame oracle comparison is rejected unless capture/RAW identity is exact')
print(' - FP1B matching, SIGNEDCAL, VIRTUALBV, conservative envelope and photographic math unchanged')
print(' - no Camera2, ISO/shutter allocation, motion, renderer pixels, JPEG or DNG mutation')
