#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-constraintlocal1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CONSTRAINTLOCAL1A missing expected file: {rel}')
    return p.read_text()

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
guard_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java'
constraint_ref_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java'
virtual_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

negative = read(negative_rel)
meta = read(meta_rel)
gradle = read(gradle_rel)
back = read(back_rel)

if 'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a' not in negative:
    raise SystemExit('CONSTRAINTLOCAL1A requires EXACTID1A / FP1B / SIGNEDCAL1A teacher')
if 'm9cam.foregroundguard.v1a' not in read(guard_rel):
    raise SystemExit('CONSTRAINTLOCAL1A requires FOREGROUNDGUARD1A')
if 'm9cam.constraintref.v1' not in read(constraint_ref_rel):
    raise SystemExit('CONSTRAINTLOCAL1A requires CONSTRAINTREF1A')
expected_version = "versionName '1.55-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a'"
if expected_version not in gradle:
    raise SystemExit('CONSTRAINTLOCAL1A expected FOREGROUNDGUARD1A 1.55 versionName missing')

frozen_rels = [
    guard_rel,
    constraint_ref_rel,
    virtual_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

vars_anchor = '''            int passingReferenceAlignedCandidateCount = 0;
            double conservativePositiveCeilingFromPhotonEv = Double.NaN;
            boolean conservativeMandatoryCeilingFromPhotonAvailable = false;
            double conservativeMandatoryCeilingFromPhotonEv = Double.NaN;
'''
vars_repl = '''            int passingReferenceAlignedCandidateCount = 0;
            double conservativePositiveCeilingFromPhotonEv = Double.NaN;
            boolean conservativeMandatoryCeilingFromPhotonAvailable = false;
            double conservativeMandatoryCeilingFromPhotonEv = Double.NaN;

            // CONSTRAINTLOCAL1A research-only candidate instrumentation.
            org.json.JSONArray constraintLocalCandidates = new org.json.JSONArray();
            CompletedRaw constraintLocalTop1 = null;
            CompletedRaw constraintLocalTop2 = null;
            double constraintLocalTop1Distance = Double.POSITIVE_INFINITY;
            double constraintLocalTop2Distance = Double.POSITIVE_INFINITY;
'''
if vars_anchor not in negative:
    raise SystemExit('CONSTRAINTLOCAL1A envelope variables anchor missing')
negative = negative.replace(vars_anchor, vars_repl, 1)

loop_anchor = '''                double d = current.distance(candidate.scene);
                if (d <= SIMILAR_SCENE_DISTANCE) {
'''
loop_repl = '''                double d = current.distance(candidate.scene);

                double constraintLocalSpatialDistance = spatialTileMedianDistance(
                        current.spatialTileMedians3x3, candidate.scene.spatialTileMedians3x3);
                double constraintLocalAllowance = constraintPositiveAllowance(candidate);
                double constraintLocalProtection = constraintMandatoryProtection(candidate);
                double constraintLocalSourceOffset =
                        candidate.scene != null
                                ? candidate.scene.actualCaptureOffsetFromPhotonEv : Double.NaN;
                double constraintLocalPositiveCeiling =
                        finite(constraintLocalSourceOffset) && finite(constraintLocalAllowance)
                                ? constraintLocalSourceOffset + constraintLocalAllowance
                                : Double.NaN;
                boolean constraintLocalMandatoryAvailable =
                        finite(constraintLocalSourceOffset)
                                && finite(constraintLocalProtection)
                                && constraintLocalProtection < 0.0;
                double constraintLocalMandatoryCeiling =
                        constraintLocalMandatoryAvailable
                                ? constraintLocalSourceOffset + constraintLocalProtection
                                : Double.NaN;

                try {
                    JSONObject candidateDiag = new JSONObject();
                    candidateDiag.put("sourceCaptureSequence",
                            candidate.scene != null ? candidate.scene.sequence : JSONObject.NULL);
                    candidateDiag.put("sourceCompletedSequence", candidate.completedSequence);
                    candidateDiag.put("sourceAgeMs", ageMs);
                    candidateDiag.put("sceneFingerprintDistance", d);
                    candidateDiag.put("spatialTileMedianDistance", constraintLocalSpatialDistance);
                    candidateDiag.put("passesBroadFp1bThreshold",
                            d <= SIMILAR_SCENE_DISTANCE);
                    candidateDiag.put("sourceCaptureIdentity",
                            candidate.scene != null && candidate.scene.captureIdentity != null
                                    ? candidate.scene.captureIdentity : JSONObject.NULL);
                    candidateDiag.put("sourceRawTimestampNs",
                            candidate.scene != null && candidate.scene.rawTimestampNs > 0L
                                    ? candidate.scene.rawTimestampNs : JSONObject.NULL);
                    candidateDiag.put("sourceActualCaptureOffsetFromPhotonEv",
                            finite(constraintLocalSourceOffset)
                                    ? constraintLocalSourceOffset : JSONObject.NULL);
                    candidateDiag.put("rawPositiveAllowanceEv",
                            finite(constraintLocalAllowance)
                                    ? constraintLocalAllowance : JSONObject.NULL);
                    candidateDiag.put("referenceAlignedPositiveCeilingFromPhotonEv",
                            finite(constraintLocalPositiveCeiling)
                                    ? constraintLocalPositiveCeiling : JSONObject.NULL);
                    candidateDiag.put("rawMandatoryProtectionEv",
                            finite(constraintLocalProtection)
                                    ? constraintLocalProtection : JSONObject.NULL);
                    candidateDiag.put("referenceAlignedMandatoryCeilingAvailable",
                            constraintLocalMandatoryAvailable);
                    candidateDiag.put("referenceAlignedMandatoryCeilingFromPhotonEv",
                            constraintLocalMandatoryAvailable
                                    ? constraintLocalMandatoryCeiling : JSONObject.NULL);
                    candidateDiag.put("rawUq25", candidate.q25);
                    candidateDiag.put("rawUq50", candidate.q50);
                    candidateDiag.put("rawUq99_8", candidate.q998);
                    candidateDiag.put("rawHardClipFraction", candidate.clip);
                    constraintLocalCandidates.put(candidateDiag);
                } catch (Exception ignored) {}

                if (d <= SIMILAR_SCENE_DISTANCE && finite(constraintLocalSourceOffset)) {
                    if (d < constraintLocalTop1Distance) {
                        constraintLocalTop2 = constraintLocalTop1;
                        constraintLocalTop2Distance = constraintLocalTop1Distance;
                        constraintLocalTop1 = candidate;
                        constraintLocalTop1Distance = d;
                    } else if (d < constraintLocalTop2Distance) {
                        constraintLocalTop2 = candidate;
                        constraintLocalTop2Distance = d;
                    }
                }

                if (d <= SIMILAR_SCENE_DISTANCE) {
'''
if loop_anchor not in negative:
    raise SystemExit('CONSTRAINTLOCAL1A candidate-loop anchor missing')
negative = negative.replace(loop_anchor, loop_repl, 1)

output_anchor = '''            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);
'''
output_repl = r'''            JSONObject constraintLocal = new JSONObject();
            try {
                constraintLocal.put("schema", "m9cam.constraintlocal.v1a");
                constraintLocal.put("mode", "diagnostic_only_no_exposure_mutation");
                constraintLocal.put("liveEligible", false);
                constraintLocal.put("usedToMutateCaptureTarget", false);
                constraintLocal.put("broadFp1bThreshold", SIMILAR_SCENE_DISTANCE);
                constraintLocal.put("maxFeedbackAgeMs", MAX_FEEDBACK_AGE_MS);
                constraintLocal.put("candidateCount", constraintLocalCandidates.length());
                constraintLocal.put("candidates", constraintLocalCandidates);
                constraintLocal.put("selectionModels",
                        "nearest_vs_top2_nearest_envelope_vs_nearest_plus0p15_local_envelope_vs_existing_broad_envelope");

                int top2Count = 0;
                double top2PositiveCeiling = Double.NaN;
                boolean top2MandatoryAvailable = false;
                double top2MandatoryCeiling = Double.NaN;
                org.json.JSONArray top2Sequences = new org.json.JSONArray();
                CompletedRaw[] top2 = new CompletedRaw[] {
                        constraintLocalTop1, constraintLocalTop2
                };
                for (CompletedRaw c : top2) {
                    if (c == null || c.scene == null) continue;
                    double sourceOffset = c.scene.actualCaptureOffsetFromPhotonEv;
                    if (!finite(sourceOffset)) continue;
                    top2Count++;
                    top2Sequences.put(c.completedSequence);
                    double allowance = constraintPositiveAllowance(c);
                    if (finite(allowance)) {
                        double ceiling = sourceOffset + allowance;
                        top2PositiveCeiling = finite(top2PositiveCeiling)
                                ? Math.min(top2PositiveCeiling, ceiling) : ceiling;
                    }
                    double protection = constraintMandatoryProtection(c);
                    if (finite(protection) && protection < 0.0) {
                        double ceiling = sourceOffset + protection;
                        top2MandatoryCeiling = top2MandatoryAvailable
                                ? Math.min(top2MandatoryCeiling, ceiling) : ceiling;
                        top2MandatoryAvailable = true;
                    }
                }
                constraintLocal.put("top2NearestCandidateCount", top2Count);
                constraintLocal.put("top2NearestCompletedSequences", top2Sequences);
                constraintLocal.put("top2NearestPositiveCeilingFromPhotonEv",
                        finite(top2PositiveCeiling) ? top2PositiveCeiling : JSONObject.NULL);
                constraintLocal.put("top2NearestMandatoryCeilingAvailable",
                        top2MandatoryAvailable);
                constraintLocal.put("top2NearestMandatoryCeilingFromPhotonEv",
                        top2MandatoryAvailable ? top2MandatoryCeiling : JSONObject.NULL);

                double localThreshold = finite(bestDistance)
                        ? Math.min(SIMILAR_SCENE_DISTANCE, bestDistance + 0.15)
                        : Double.NaN;
                int localCount = 0;
                double localPositiveCeiling = Double.NaN;
                boolean localMandatoryAvailable = false;
                double localMandatoryCeiling = Double.NaN;
                org.json.JSONArray localSequences = new org.json.JSONArray();
                if (finite(localThreshold)) {
                    for (int i = history.size() - 1; i >= 0; i--) {
                        CompletedRaw c = history.get(i);
                        if (c == null || c.scene == null) continue;
                        long localAgeMs = Math.max(0L, nowMs - c.completedEpochMs);
                        if (localAgeMs > MAX_FEEDBACK_AGE_MS) continue;
                        double localDistance = current.distance(c.scene);
                        if (localDistance > localThreshold) continue;
                        double sourceOffset = c.scene.actualCaptureOffsetFromPhotonEv;
                        if (!finite(sourceOffset)) continue;
                        localCount++;
                        localSequences.put(c.completedSequence);
                        double allowance = constraintPositiveAllowance(c);
                        if (finite(allowance)) {
                            double ceiling = sourceOffset + allowance;
                            localPositiveCeiling = finite(localPositiveCeiling)
                                    ? Math.min(localPositiveCeiling, ceiling) : ceiling;
                        }
                        double protection = constraintMandatoryProtection(c);
                        if (finite(protection) && protection < 0.0) {
                            double ceiling = sourceOffset + protection;
                            localMandatoryCeiling = localMandatoryAvailable
                                    ? Math.min(localMandatoryCeiling, ceiling) : ceiling;
                            localMandatoryAvailable = true;
                        }
                    }
                }
                constraintLocal.put("localEnvelopeRule",
                        "recent_candidate_distance_le_nearest_plus0p15_capped_at_fp1b_1p0");
                constraintLocal.put("localEnvelopeThreshold",
                        finite(localThreshold) ? localThreshold : JSONObject.NULL);
                constraintLocal.put("localEnvelopeCandidateCount", localCount);
                constraintLocal.put("localEnvelopeCompletedSequences", localSequences);
                constraintLocal.put("localEnvelopePositiveCeilingFromPhotonEv",
                        finite(localPositiveCeiling) ? localPositiveCeiling : JSONObject.NULL);
                constraintLocal.put("localEnvelopeMandatoryCeilingAvailable",
                        localMandatoryAvailable);
                constraintLocal.put("localEnvelopeMandatoryCeilingFromPhotonEv",
                        localMandatoryAvailable ? localMandatoryCeiling : JSONObject.NULL);

                constraintLocal.put("existingBroadEnvelopeCandidateCount",
                        passingReferenceAlignedCandidateCount);
                constraintLocal.put("existingBroadPositiveCeilingFromPhotonEv",
                        finite(conservativePositiveCeilingFromPhotonEv)
                                ? conservativePositiveCeilingFromPhotonEv : JSONObject.NULL);
                constraintLocal.put("existingBroadMandatoryCeilingAvailable",
                        conservativeMandatoryCeilingFromPhotonAvailable);
                constraintLocal.put("existingBroadMandatoryCeilingFromPhotonEv",
                        conservativeMandatoryCeilingFromPhotonAvailable
                                ? conservativeMandatoryCeilingFromPhotonEv : JSONObject.NULL);
                constraintLocal.put("reason",
                        "candidate_level_history_selection_recorded_no_live_exposure_change");
            } catch (Exception ignored) {}
            out.put("constraintLocal1A", constraintLocal);

            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);
'''
if output_anchor not in negative:
    raise SystemExit('CONSTRAINTLOCAL1A output insertion anchor missing')
negative = negative.replace(output_anchor, output_repl, 1)
(root / negative_rel).write_text(negative)

local_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java'
local_p = root / local_rel
if local_p.exists():
    raise SystemExit('CONSTRAINTLOCAL1A target class already exists; refuse ambiguous reapply')
local_java = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONArray;
import org.json.JSONObject;

public final class M9ConstraintLocal1A {
    public static final String SCHEMA = "m9cam.constraintlocal.v1a";
    private M9ConstraintLocal1A() {}

    public static JSONObject evaluate(JSONObject root) {
        JSONObject out = contract();
        try {
            JSONObject scene = root != null ? root.optJSONObject("m9SceneExposureDiagnostic") : null;
            JSONObject split = scene != null ? scene.optJSONObject("captureRenderSplit") : null;
            JSONObject negative = split != null ? split.optJSONObject("m9Negative1A") : null;
            JSONObject local = negative != null ? negative.optJSONObject("constraintLocal1A") : null;
            JSONObject guard = root != null ? root.optJSONObject("m9ForegroundGuard") : null;
            JSONObject ref = root != null ? root.optJSONObject("m9ConstraintRef") : null;

            if (local == null) return invalid(out, "constraintlocal_candidate_block_missing");

            out.put("valid", true);
            out.put("reason", "history_selection_policies_compared_no_live_exposure_change");
            out.put("candidateCount", local.optInt("candidateCount", 0));
            JSONArray candidates = local.optJSONArray("candidates");
            out.put("candidates", candidates != null ? candidates : new JSONArray());
            copy(out, local, "broadFp1bThreshold");
            copy(out, local, "maxFeedbackAgeMs");
            copy(out, local, "selectionModels");
            copy(out, local, "top2NearestCandidateCount");
            copy(out, local, "top2NearestCompletedSequences");
            copy(out, local, "top2NearestPositiveCeilingFromPhotonEv");
            copy(out, local, "top2NearestMandatoryCeilingAvailable");
            copy(out, local, "top2NearestMandatoryCeilingFromPhotonEv");
            copy(out, local, "localEnvelopeRule");
            copy(out, local, "localEnvelopeThreshold");
            copy(out, local, "localEnvelopeCandidateCount");
            copy(out, local, "localEnvelopeCompletedSequences");
            copy(out, local, "localEnvelopePositiveCeilingFromPhotonEv");
            copy(out, local, "localEnvelopeMandatoryCeilingAvailable");
            copy(out, local, "localEnvelopeMandatoryCeilingFromPhotonEv");
            copy(out, local, "existingBroadEnvelopeCandidateCount");
            copy(out, local, "existingBroadPositiveCeilingFromPhotonEv");
            copy(out, local, "existingBroadMandatoryCeilingAvailable");
            copy(out, local, "existingBroadMandatoryCeilingFromPhotonEv");

            double guardedTarget = guard != null
                    ? guard.optDouble("preSensorGuardedTargetFromPhotonEv", Double.NaN)
                    : Double.NaN;
            putFinite(out, "preSensorGuardedTargetFromPhotonEv", guardedTarget);

            double nearestPositive = ref != null
                    ? ref.optDouble("matchedSensorPositiveCeilingFromPhotonEv", Double.NaN)
                    : Double.NaN;
            boolean nearestMandatoryAvailable = ref != null
                    && ref.optBoolean("matchedSensorMandatoryCeilingFromPhotonAvailable", false);
            double nearestMandatory = ref != null
                    ? ref.optDouble("matchedSensorMandatoryCeilingFromPhotonEv", Double.NaN)
                    : Double.NaN;

            putPolicy(out, "nearest", guardedTarget, nearestPositive,
                    nearestMandatoryAvailable, nearestMandatory);
            putPolicy(out, "top2NearestEnvelope", guardedTarget,
                    local.optDouble("top2NearestPositiveCeilingFromPhotonEv", Double.NaN),
                    local.optBoolean("top2NearestMandatoryCeilingAvailable", false),
                    local.optDouble("top2NearestMandatoryCeilingFromPhotonEv", Double.NaN));
            putPolicy(out, "localEnvelope", guardedTarget,
                    local.optDouble("localEnvelopePositiveCeilingFromPhotonEv", Double.NaN),
                    local.optBoolean("localEnvelopeMandatoryCeilingAvailable", false),
                    local.optDouble("localEnvelopeMandatoryCeilingFromPhotonEv", Double.NaN));
            putPolicy(out, "existingBroadEnvelope", guardedTarget,
                    local.optDouble("existingBroadPositiveCeilingFromPhotonEv", Double.NaN),
                    local.optBoolean("existingBroadMandatoryCeilingAvailable", false),
                    local.optDouble("existingBroadMandatoryCeilingFromPhotonEv", Double.NaN));

            out.put("policyAuthority", "diagnostic_comparison_only_none_live");
            out.put("currentLiveExposurePathChanged", false);
        } catch (Throwable t) {
            try {
                invalid(out, "constraintlocal1a_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static void putPolicy(JSONObject out, String name, double request,
                                  double positiveCeiling,
                                  boolean mandatoryAvailable,
                                  double mandatoryCeiling) {
        JSONObject p = new JSONObject();
        try {
            putFinite(p, "positiveCeilingFromPhotonEv", positiveCeiling);
            p.put("mandatoryCeilingAvailable",
                    mandatoryAvailable && finite(mandatoryCeiling));
            putFinite(p, "mandatoryCeilingFromPhotonEv",
                    mandatoryAvailable ? mandatoryCeiling : Double.NaN);
            double constrained = constrain(request, positiveCeiling,
                    mandatoryAvailable, mandatoryCeiling);
            putFinite(p, "counterfactualGuardedTargetFromPhotonEv", constrained);
            if (finite(request) && finite(constrained)) {
                p.put("counterfactualDeltaFromPreSensorGuardEv", constrained - request);
            } else {
                p.put("counterfactualDeltaFromPreSensorGuardEv", JSONObject.NULL);
            }
            out.put(name, p);
        } catch (Exception ignored) {}
    }

    private static double constrain(double request, double positiveCeiling,
                                    boolean mandatoryAvailable,
                                    double mandatoryCeiling) {
        if (!finite(request)) return Double.NaN;
        if (mandatoryAvailable && finite(mandatoryCeiling)) {
            return Math.min(request, mandatoryCeiling);
        }
        if (request > 0.0 && finite(positiveCeiling)) {
            return Math.min(request, positiveCeiling);
        }
        return request;
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("architecture",
                    "compare_nearest_top2_local_and_existing_broad_reference_aligned_raw_history");
            out.put("localRuleCalibration",
                    "nearest_plus0p15_is_research_only_not_frozen_photographic_truth");
        } catch (Exception ignored) {}
        return out;
    }

    private static JSONObject invalid(JSONObject out, String reason) {
        try {
            out.put("valid", false);
            out.put("reason", reason);
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
        } catch (Exception ignored) {}
        return out;
    }

    private static void copy(JSONObject dst, JSONObject src, String key) {
        try { if (src != null && src.has(key)) dst.put(key, src.opt(key)); }
        catch (Exception ignored) {}
    }

    private static void putFinite(JSONObject out, String key, double value) {
        try { out.put(key, finite(value) ? value : JSONObject.NULL); }
        catch (Exception ignored) {}
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }
}
'''
local_p.write_text(local_java)

meta_p = root / meta_rel
meta = meta_p.read_text()
meta_anchor = '''            root.put("m9ForegroundGuard", M9ForegroundGuard1A.evaluate(root));
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
meta_repl = '''            root.put("m9ForegroundGuard", M9ForegroundGuard1A.evaluate(root));
            root.put("m9ConstraintLocal", M9ConstraintLocal1A.evaluate(root));
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
if meta_anchor not in meta:
    raise SystemExit('CONSTRAINTLOCAL1A metadata publication anchor missing')
meta_p.write_text(meta.replace(meta_anchor, meta_repl, 1))

gradle_p = root / gradle_rel
gradle = gradle_p.read_text()
old_version = "versionName '1.55-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a'"
new_version = "versionName '1.56-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a'"
if old_version not in gradle:
    raise SystemExit('CONSTRAINTLOCAL1A 1.55 versionName anchor missing')
gradle_p.write_text(gradle.replace(old_version, new_version, 1))

back_p = root / back_rel
back = back_p.read_text()
marker_anchor = 'constraintref1avirtualbvspatial1bforegroundguard1ascenefingerprint1b'
marker_repl = 'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1ascenefingerprint1b'
if marker_anchor not in back:
    raise SystemExit('CONSTRAINTLOCAL1A forensic marker anchor missing')
back = back.replace(marker_anchor, marker_repl, 1)
if '1.55-' not in back:
    raise SystemExit('CONSTRAINTLOCAL1A backlight version anchor missing')
back_p.write_text(back.replace('1.55-', '1.56-', 1))

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'CONSTRAINTLOCAL1A froze seam changed unexpectedly: {rel}')

print('M9Cam CONSTRAINTLOCAL1A diagnostic history-selection overlay applied')
print(' - candidate-level FP1B RAW history telemetry added')
print(' - compares nearest, top-2 nearest, nearest+0.15 local, and existing broad envelopes')
print(' - aligned source offset + RAW allowance/protection logged per candidate')
print(' - FOREGROUNDGUARD1A +0.50 floor and CONSTRAINTREF1A reference math frozen')
print(' - no Camera2, allocator, motion, renderer, JPEG, DNG or quality mutation')
