#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-photometricnorm1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'PHOTOMETRICNORM1A missing expected file: {rel}')
    return p.read_text()


def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
local_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

negative = read(negative_rel)
local = read(local_rel)
gradle = read(gradle_rel)
back = read(back_rel)

if 'constraintLocal1A' not in negative:
    raise SystemExit('PHOTOMETRICNORM1A requires CONSTRAINTLOCAL1A candidate telemetry')
if 'm9cam.constraintlocal.v1a' not in local:
    raise SystemExit('PHOTOMETRICNORM1A requires M9ConstraintLocal1A')
expected_version = "versionName '1.56-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a'"
if expected_version not in gradle:
    raise SystemExit('PHOTOMETRICNORM1A expected CONSTRAINTLOCAL1A 1.56 versionName missing')

# This overlay is association research only. Freeze every photographic/live seam.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

# Add a photometrically normalized, exposure-state-resistant alternative distance.
# It intentionally omits dark/bright threshold fractions and starvation from identity,
# because those terms change when the preview exposure state changes. It uses only
# existing preview luma plus existing preview exposure energy; RAW/JPEG data never enter.
helper_anchor = '''    private static double[] readSpatialTileMedians(JSONObject tiles) {\n'''
helper = r'''    private static final double PHOTOMETRIC_NORM_RESPONSE_SCALE_EV = 1.15;
    private static final double PHOTOMETRIC_NORM_SPATIAL_P75_SCALE_EV = 1.15;
    private static final double PHOTOMETRIC_NORM_SHAPE_SCALE_EV = 0.75;
    private static final double PHOTOMETRIC_NORM_MATCH_THRESHOLD = 1.0;

    private static final class PhotometricNormDistance {
        boolean valid = false;
        double responseDistanceEv = Double.NaN;
        double spatialP75DistanceEv = Double.NaN;
        double shapeDistanceEv = Double.NaN;
        double score = Double.NaN;
    }

    private static PhotometricNormDistance photometricNormalizedDistance(
            SceneSignature a, SceneSignature b) {
        PhotometricNormDistance out = new PhotometricNormDistance();
        if (a == null || b == null
                || !finite(a.previewEnergyIsoSeconds) || a.previewEnergyIsoSeconds <= 0.0
                || !finite(b.previewEnergyIsoSeconds) || b.previewEnergyIsoSeconds <= 0.0) {
            return out;
        }

        double response = 0.0;
        response = Math.max(response, responseDeltaEv(
                a.median, a.previewEnergyIsoSeconds,
                b.median, b.previewEnergyIsoSeconds));
        response = Math.max(response, responseDeltaEv(
                a.center, a.previewEnergyIsoSeconds,
                b.center, b.previewEnergyIsoSeconds));
        response = Math.max(response, responseDeltaEv(
                a.q95, a.previewEnergyIsoSeconds,
                b.q95, b.previewEnergyIsoSeconds));
        response = Math.max(response, responseDeltaEv(
                a.middleCenterQ95, a.previewEnergyIsoSeconds,
                b.middleCenterQ95, b.previewEnergyIsoSeconds));

        double shape = 0.0;
        shape = Math.max(shape, ratioDeltaEv(a.center, a.median, b.center, b.median));
        shape = Math.max(shape, ratioDeltaEv(a.q95, a.median, b.q95, b.median));
        shape = Math.max(shape, ratioDeltaEv(
                a.middleCenterQ95, a.median, b.middleCenterQ95, b.median));
        shape = Math.max(shape, ratioDeltaEv(a.q99, a.median, b.q99, b.median));

        if (!finite(response) || !finite(shape)
                || a.spatialTileMedians3x3 == null || b.spatialTileMedians3x3 == null
                || a.spatialTileMedians3x3.length != 9 || b.spatialTileMedians3x3.length != 9) {
            return out;
        }
        double[] tileDeltaEv = new double[9];
        for (int i = 0; i < 9; i++) {
            tileDeltaEv[i] = responseDeltaEv(
                    a.spatialTileMedians3x3[i], a.previewEnergyIsoSeconds,
                    b.spatialTileMedians3x3[i], b.previewEnergyIsoSeconds);
            if (!finite(tileDeltaEv[i])) return out;
        }
        java.util.Arrays.sort(tileDeltaEv);
        // 7th of 9 ordered samples: robust ~75th percentile, avoiding one/two tile
        // framing shifts from becoming the entire identity as FP1B max-abs currently does.
        double spatialP75 = tileDeltaEv[6];

        out.valid = true;
        out.responseDistanceEv = response;
        out.spatialP75DistanceEv = spatialP75;
        out.shapeDistanceEv = shape;
        out.score = Math.max(response / PHOTOMETRIC_NORM_RESPONSE_SCALE_EV,
                Math.max(spatialP75 / PHOTOMETRIC_NORM_SPATIAL_P75_SCALE_EV,
                        shape / PHOTOMETRIC_NORM_SHAPE_SCALE_EV));
        return out;
    }

    private static double responseDeltaEv(double ya, double ea, double yb, double eb) {
        if (!finite(ya) || !finite(ea) || !finite(yb) || !finite(eb)
                || ya <= 0.0 || ea <= 0.0 || yb <= 0.0 || eb <= 0.0) {
            return Double.NaN;
        }
        return Math.abs(log2((ya / ea) / (yb / eb)));
    }

    private static double ratioDeltaEv(double na, double da, double nb, double db) {
        if (!finite(na) || !finite(da) || !finite(nb) || !finite(db)
                || na <= 0.0 || da <= 0.0 || nb <= 0.0 || db <= 0.0) {
            return Double.NaN;
        }
        return Math.abs(log2((na / da) / (nb / db)));
    }

    private static double[] readSpatialTileMedians(JSONObject tiles) {
'''
if helper_anchor not in negative:
    raise SystemExit('PHOTOMETRICNORM1A spatial-helper anchor missing')
negative = negative.replace(helper_anchor, helper, 1)

loop_anchor = '''                double d = current.distance(candidate.scene);\n\n                double constraintLocalSpatialDistance = spatialTileMedianDistance(\n'''
loop_repl = '''                double d = current.distance(candidate.scene);\n                PhotometricNormDistance photometricNorm =\n                        photometricNormalizedDistance(current, candidate.scene);\n\n                double constraintLocalSpatialDistance = spatialTileMedianDistance(\n'''
if loop_anchor not in negative:
    raise SystemExit('PHOTOMETRICNORM1A candidate-loop anchor missing')
negative = negative.replace(loop_anchor, loop_repl, 1)

candidate_anchor = '''                    candidateDiag.put("sceneFingerprintDistance", d);\n                    candidateDiag.put("spatialTileMedianDistance", constraintLocalSpatialDistance);\n                    candidateDiag.put("passesBroadFp1bThreshold",\n                            d <= SIMILAR_SCENE_DISTANCE);\n'''
candidate_repl = '''                    candidateDiag.put("sceneFingerprintDistance", d);\n                    candidateDiag.put("spatialTileMedianDistance", constraintLocalSpatialDistance);\n                    candidateDiag.put("passesBroadFp1bThreshold",\n                            d <= SIMILAR_SCENE_DISTANCE);\n                    candidateDiag.put("photometricNormalizedValid", photometricNorm.valid);\n                    candidateDiag.put("photometricNormalizedDistance",\n                            photometricNorm.valid ? photometricNorm.score : JSONObject.NULL);\n                    candidateDiag.put("photometricNormalizedResponseDistanceEv",\n                            photometricNorm.valid\n                                    ? photometricNorm.responseDistanceEv : JSONObject.NULL);\n                    candidateDiag.put("photometricNormalizedSpatialP75DistanceEv",\n                            photometricNorm.valid\n                                    ? photometricNorm.spatialP75DistanceEv : JSONObject.NULL);\n                    candidateDiag.put("photometricNormalizedShapeDistanceEv",\n                            photometricNorm.valid\n                                    ? photometricNorm.shapeDistanceEv : JSONObject.NULL);\n                    candidateDiag.put("passesPhotometricNormalizedThreshold",\n                            photometricNorm.valid\n                                    && photometricNorm.score <= PHOTOMETRIC_NORM_MATCH_THRESHOLD);\n'''
if candidate_anchor not in negative:
    raise SystemExit('PHOTOMETRICNORM1A candidate telemetry anchor missing')
negative = negative.replace(candidate_anchor, candidate_repl, 1)
(root / negative_rel).write_text(negative)

# M9ConstraintLocal1A consumes only the candidate diagnostic JSON to compare what the
# normalized matcher WOULD select. It remains diagnostic-only and cannot feed Camera2.
call_anchor = '''            putFinite(out, "preSensorGuardedTargetFromPhotonEv", guardedTarget);\n\n            double nearestPositive = ref != null\n'''
call_repl = '''            putFinite(out, "preSensorGuardedTargetFromPhotonEv", guardedTarget);\n            putPhotometricNormalizedPolicies(out, candidates, guardedTarget);\n\n            double nearestPositive = ref != null\n'''
if call_anchor not in local:
    raise SystemExit('PHOTOMETRICNORM1A local-policy call anchor missing')
local = local.replace(call_anchor, call_repl, 1)

policy_anchor = '''    private static void putPolicy(JSONObject out, String name, double request,\n'''
policy_helper = r'''    private static void putPhotometricNormalizedPolicies(
            JSONObject out, JSONArray candidates, double request) {
        try {
            final double threshold = 1.0;
            JSONObject top1 = null;
            JSONObject top2 = null;
            double top1Score = Double.POSITIVE_INFINITY;
            double top2Score = Double.POSITIVE_INFINITY;
            int passCount = 0;
            JSONArray passSequences = new JSONArray();
            double broadPositive = Double.NaN;
            boolean broadMandatoryAvailable = false;
            double broadMandatory = Double.NaN;

            if (candidates != null) {
                for (int i = 0; i < candidates.length(); i++) {
                    JSONObject c = candidates.optJSONObject(i);
                    if (c == null || !c.optBoolean("photometricNormalizedValid", false)) continue;
                    double score = c.optDouble("photometricNormalizedDistance", Double.NaN);
                    if (!finite(score) || score > threshold) continue;
                    passCount++;
                    if (c.has("sourceCompletedSequence")) {
                        passSequences.put(c.optLong("sourceCompletedSequence"));
                    }
                    double positive = c.optDouble(
                            "referenceAlignedPositiveCeilingFromPhotonEv", Double.NaN);
                    if (finite(positive)) {
                        broadPositive = finite(broadPositive)
                                ? Math.min(broadPositive, positive) : positive;
                    }
                    boolean mandatoryAvailable = c.optBoolean(
                            "referenceAlignedMandatoryCeilingAvailable", false);
                    double mandatory = c.optDouble(
                            "referenceAlignedMandatoryCeilingFromPhotonEv", Double.NaN);
                    if (mandatoryAvailable && finite(mandatory)) {
                        broadMandatory = broadMandatoryAvailable
                                ? Math.min(broadMandatory, mandatory) : mandatory;
                        broadMandatoryAvailable = true;
                    }
                    if (score < top1Score) {
                        top2 = top1;
                        top2Score = top1Score;
                        top1 = c;
                        top1Score = score;
                    } else if (score < top2Score) {
                        top2 = c;
                        top2Score = score;
                    }
                }
            }

            out.put("photometricNormalizedMatcherSchema",
                    "m9cam.scenefingerprintnorm.v1a.preview_energy_response_shape_spatialp75");
            out.put("photometricNormalizedMode", "diagnostic_only_no_association_mutation");
            out.put("photometricNormalizedCalibration",
                    "research_only_20260904_bulb_cat_window_sequence_not_frozen_photographic_truth");
            out.put("photometricNormalizedThreshold", threshold);
            out.put("photometricNormalizedResponseScaleEv", 1.15);
            out.put("photometricNormalizedSpatialP75ScaleEv", 1.15);
            out.put("photometricNormalizedShapeScaleEv", 0.75);
            out.put("photometricNormalizedExcludedIdentityTerms",
                    "dark_bright_threshold_fractions_and_starvation_are_exposure_state_dependent");
            out.put("photometricNormalizedPassCount", passCount);
            out.put("photometricNormalizedPassCompletedSequences", passSequences);
            out.put("photometricNormalizedNearestCompletedSequence",
                    top1 != null && top1.has("sourceCompletedSequence")
                            ? top1.optLong("sourceCompletedSequence") : JSONObject.NULL);
            out.put("photometricNormalizedNearestDistance",
                    top1 != null ? top1Score : JSONObject.NULL);

            double nearestPositive = top1 != null
                    ? top1.optDouble("referenceAlignedPositiveCeilingFromPhotonEv", Double.NaN)
                    : Double.NaN;
            boolean nearestMandatoryAvailable = top1 != null
                    && top1.optBoolean("referenceAlignedMandatoryCeilingAvailable", false);
            double nearestMandatory = top1 != null
                    ? top1.optDouble("referenceAlignedMandatoryCeilingFromPhotonEv", Double.NaN)
                    : Double.NaN;

            double top2Positive = Double.NaN;
            boolean top2MandatoryAvailable = false;
            double top2Mandatory = Double.NaN;
            JSONArray top2Sequences = new JSONArray();
            JSONObject[] selected = new JSONObject[] {top1, top2};
            for (JSONObject c : selected) {
                if (c == null) continue;
                if (c.has("sourceCompletedSequence")) {
                    top2Sequences.put(c.optLong("sourceCompletedSequence"));
                }
                double positive = c.optDouble(
                        "referenceAlignedPositiveCeilingFromPhotonEv", Double.NaN);
                if (finite(positive)) {
                    top2Positive = finite(top2Positive)
                            ? Math.min(top2Positive, positive) : positive;
                }
                boolean mandatoryAvailable = c.optBoolean(
                        "referenceAlignedMandatoryCeilingAvailable", false);
                double mandatory = c.optDouble(
                        "referenceAlignedMandatoryCeilingFromPhotonEv", Double.NaN);
                if (mandatoryAvailable && finite(mandatory)) {
                    top2Mandatory = top2MandatoryAvailable
                            ? Math.min(top2Mandatory, mandatory) : mandatory;
                    top2MandatoryAvailable = true;
                }
            }
            out.put("photometricNormalizedTop2CompletedSequences", top2Sequences);
            putFinite(out, "photometricNormalizedTop2PositiveCeilingFromPhotonEv", top2Positive);
            out.put("photometricNormalizedTop2MandatoryCeilingAvailable", top2MandatoryAvailable);
            putFinite(out, "photometricNormalizedTop2MandatoryCeilingFromPhotonEv",
                    top2MandatoryAvailable ? top2Mandatory : Double.NaN);
            putFinite(out, "photometricNormalizedBroadPositiveCeilingFromPhotonEv", broadPositive);
            out.put("photometricNormalizedBroadMandatoryCeilingAvailable", broadMandatoryAvailable);
            putFinite(out, "photometricNormalizedBroadMandatoryCeilingFromPhotonEv",
                    broadMandatoryAvailable ? broadMandatory : Double.NaN);

            putPolicy(out, "photometricNormalizedNearest", request,
                    nearestPositive, nearestMandatoryAvailable, nearestMandatory);
            putPolicy(out, "photometricNormalizedTop2Envelope", request,
                    top2Positive, top2MandatoryAvailable, top2Mandatory);
            putPolicy(out, "photometricNormalizedBroadEnvelope", request,
                    broadPositive, broadMandatoryAvailable, broadMandatory);
        } catch (Exception ignored) {}
    }

    private static void putPolicy(JSONObject out, String name, double request,
'''
if policy_anchor not in local:
    raise SystemExit('PHOTOMETRICNORM1A local helper anchor missing')
local = local.replace(policy_anchor, policy_helper, 1)
(root / local_rel).write_text(local)

gradle = gradle.replace(
        expected_version,
        "versionName '1.57-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a'",
        1)
(root / gradle_rel).write_text(gradle)

marker_anchor = 'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1ascenefingerprint1b'
marker_repl = 'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1aphotometricnorm1ascenefingerprint1b'
if marker_anchor not in back:
    raise SystemExit('PHOTOMETRICNORM1A forensic marker anchor missing')
back = back.replace(marker_anchor, marker_repl, 1)
if '1.56-' not in back:
    raise SystemExit('PHOTOMETRICNORM1A build version anchor missing')
back = back.replace('1.56-', '1.57-', 1)
(root / back_rel).write_text(back)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'PHOTOMETRICNORM1A frozen seam changed unexpectedly: {rel}')

print('M9Cam PHOTOMETRICNORM1A diagnostic matcher overlay applied')
print(' - existing FP1B remains frozen and authoritative for current history association')
print(' - alternative distance normalizes preview luma by preview exposure energy')
print(' - robust spatial term uses 75th percentile of 3x3 tile response deltas, not max tile')
print(' - exposure-state dark/bright fractions and starvation excluded from alternative identity')
print(' - normalized nearest/top2/broad RAW ceilings are counterfactual only')
print(' - no Camera2, allocator, FB1, motion, renderer, JPEG, DNG or quality mutation')
