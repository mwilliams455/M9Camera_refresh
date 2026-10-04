#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-constraintnearest1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CONSTRAINTNEAREST1A missing expected file: {rel}')
    return p.read_text()


def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
local_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java'
negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

meta = read(meta_rel)
local = read(local_rel)
negative = read(negative_rel)
gradle = read(gradle_rel)
back = read(back_rel)

if 'm9cam.constraintlocal.v1a' not in local:
    raise SystemExit('CONSTRAINTNEAREST1A requires CONSTRAINTLOCAL1A')
if 'm9cam.scenefingerprintnorm.v1a.preview_energy_response_shape_spatialp75' not in local:
    raise SystemExit('CONSTRAINTNEAREST1A requires PHOTOMETRICNORM1A policy telemetry')
if 'photometricNormalizedDistance' not in negative:
    raise SystemExit('CONSTRAINTNEAREST1A requires PHOTOMETRICNORM1A candidate telemetry')
expected_version = "versionName '1.57-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a'"
if expected_version not in gradle:
    raise SystemExit('CONSTRAINTNEAREST1A expected PHOTOMETRICNORM1A 1.57 versionName missing')

# Promotion-candidate diagnostic only. Freeze matcher, sensor math, guard, live exposure,
# renderer and quality seams. Only metadata publication/build identity may change.
frozen_rels = [
    negative_rel,
    local_rel,
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

nearest_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java'
nearest_p = root / nearest_rel
if nearest_p.exists():
    raise SystemExit('CONSTRAINTNEAREST1A target class already exists; refuse ambiguous reapply')

nearest_java = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * Diagnostic-only promotion candidate for RAW-history sensor constraints.
 *
 * PHOTOMETRICNORM1A nearest is the only history policy evaluated here. The class does
 * not mutate Camera2, the allocator, FOREGROUNDGUARD1A, CONSTRAINTREF1A, FP1B, or the
 * renderer. It answers the narrower question: would the nearest normalized RAW ceiling
 * actually bind the signed foreground-guard request, and by how much?
 */
public final class M9ConstraintNearest1A {
    public static final String SCHEMA = "m9cam.constraintnearest.v1a";
    private static final double MATERIAL_BIND_THRESHOLD_EV = 0.05;
    private static final double NUMERIC_EPS_EV = 1e-9;

    private M9ConstraintNearest1A() {}

    public static JSONObject evaluate(JSONObject root) {
        JSONObject out = contract();
        try {
            JSONObject local = root != null ? root.optJSONObject("m9ConstraintLocal") : null;
            if (local == null || !local.optBoolean("valid", false)) {
                return invalid(out, "constraintlocal_or_photometricnorm_telemetry_missing");
            }

            double request = local.optDouble("preSensorGuardedTargetFromPhotonEv", Double.NaN);
            int candidateCount = local.optInt("candidateCount", 0);
            int passCount = local.optInt("photometricNormalizedPassCount", 0);
            double nearestDistance = local.optDouble(
                    "photometricNormalizedNearestDistance", Double.NaN);
            long nearestSequence = local.optLong(
                    "photometricNormalizedNearestCompletedSequence", Long.MIN_VALUE);
            JSONObject nearest = local.optJSONObject("photometricNormalizedNearest");

            putFinite(out, "preSensorGuardedTargetFromPhotonEv", request);
            out.put("recentCandidateCount", candidateCount);
            out.put("photometricNormalizedPassCount", passCount);
            putFinite(out, "nearestDistance", nearestDistance);
            if (nearestSequence != Long.MIN_VALUE) {
                out.put("nearestCompletedSequence", nearestSequence);
            } else {
                out.put("nearestCompletedSequence", JSONObject.NULL);
            }

            String historyState;
            if (candidateCount <= 0) {
                historyState = "no_recent_raw_candidates";
            } else if (passCount <= 0 || nearest == null) {
                historyState = "recent_history_no_photometric_normalized_match";
            } else {
                historyState = "photometric_normalized_nearest_available";
            }
            out.put("historyState", historyState);
            out.put("firstObservationNoHistoryCandidate",
                    "no_recent_raw_candidates".equals(historyState));

            if (!finite(request)) {
                return invalid(out, "pre_sensor_guarded_target_missing");
            }
            if (passCount <= 0 || nearest == null) {
                out.put("valid", true);
                out.put("historyConstraintAvailable", false);
                out.put("wouldBind", false);
                out.put("wouldMateriallyBind", false);
                out.put("bindingCause", "none_no_normalized_nearest");
                out.put("counterfactualTargetFromPhotonEv", request);
                out.put("bindingDeltaEv", 0.0);
                out.put("bindingMagnitudeEv", 0.0);
                out.put("reason", "no_transferable_nearest_history_raw_no_history_constraint");
                return out;
            }

            double positive = nearest.optDouble("positiveCeilingFromPhotonEv", Double.NaN);
            boolean mandatoryAvailable = nearest.optBoolean("mandatoryCeilingAvailable", false);
            double mandatory = nearest.optDouble("mandatoryCeilingFromPhotonEv", Double.NaN);
            putFinite(out, "nearestPositiveCeilingFromPhotonEv", positive);
            out.put("nearestMandatoryCeilingAvailable",
                    mandatoryAvailable && finite(mandatory));
            putFinite(out, "nearestMandatoryCeilingFromPhotonEv",
                    mandatoryAvailable ? mandatory : Double.NaN);

            double target = request;
            String cause = "none";
            if (mandatoryAvailable && finite(mandatory) && mandatory < target - NUMERIC_EPS_EV) {
                target = mandatory;
                cause = "mandatory_raw_protection";
            } else if (request > 0.0 && finite(positive)
                    && positive < target - NUMERIC_EPS_EV) {
                target = positive;
                cause = "positive_raw_ceiling";
            }

            double delta = target - request;
            double magnitude = Math.max(0.0, request - target);
            boolean wouldBind = magnitude > NUMERIC_EPS_EV;
            boolean materially = magnitude >= MATERIAL_BIND_THRESHOLD_EV;

            out.put("valid", true);
            out.put("historyConstraintAvailable", true);
            out.put("wouldBind", wouldBind);
            out.put("wouldMateriallyBind", materially);
            out.put("bindingCause", cause);
            out.put("counterfactualTargetFromPhotonEv", target);
            out.put("bindingDeltaEv", delta);
            out.put("bindingMagnitudeEv", magnitude);
            if (finite(positive)) {
                out.put("positiveCeilingMarginAboveRequestEv", positive - request);
            } else {
                out.put("positiveCeilingMarginAboveRequestEv", JSONObject.NULL);
            }
            out.put("reason", wouldBind
                    ? (materially
                        ? "normalized_nearest_would_materially_bind_guarded_request"
                        : "normalized_nearest_would_only_numerically_bind_guarded_request")
                    : "normalized_nearest_available_but_non_binding_for_guarded_request");
        } catch (Throwable t) {
            try {
                invalid(out, "constraintnearest1a_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("historyAuthorityCandidate",
                    "photometricnorm1a_nearest_only_top2_and_broad_rejected_for_promotion");
            out.put("materialBindThresholdEv", MATERIAL_BIND_THRESHOLD_EV);
            out.put("materialBindCalibration",
                    "research_only_0p05ev_reporting_threshold_not_photographic_exposure_policy");
            out.put("positiveConstraintRule",
                    "positive_ceiling_can_bind_only_positive_guarded_requests");
            out.put("mandatoryConstraintRule",
                    "mandatory_negative_ceiling_is_hard_upper_bound_when_more_protective_than_request");
            out.put("firstObservationPolicy", "not_resolved_diagnostic_state_only");
            out.put("currentLiveExposurePathChanged", false);
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

    private static void putFinite(JSONObject out, String key, double value) {
        try { out.put(key, finite(value) ? value : JSONObject.NULL); }
        catch (Exception ignored) {}
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }
}
'''
nearest_p.write_text(nearest_java)

meta_p = root / meta_rel
meta = meta_p.read_text()
meta_anchor = '''            root.put("m9ConstraintLocal", M9ConstraintLocal1A.evaluate(root));
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
meta_repl = '''            root.put("m9ConstraintLocal", M9ConstraintLocal1A.evaluate(root));
            root.put("m9ConstraintNearest", M9ConstraintNearest1A.evaluate(root));
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
if meta_anchor not in meta:
    raise SystemExit('CONSTRAINTNEAREST1A metadata publication anchor missing')
meta_p.write_text(meta.replace(meta_anchor, meta_repl, 1))

gradle_p = root / gradle_rel
gradle = gradle_p.read_text()
new_version = "versionName '1.58-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a'"
gradle_p.write_text(gradle.replace(expected_version, new_version, 1))

back_p = root / back_rel
back = back_p.read_text()
marker_anchor = 'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1aphotometricnorm1ascenefingerprint1b'
marker_repl = 'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1aphotometricnorm1aconstraintnearest1ascenefingerprint1b'
if marker_anchor not in back:
    raise SystemExit('CONSTRAINTNEAREST1A forensic marker anchor missing')
back = back.replace(marker_anchor, marker_repl, 1)
if '1.57-' not in back:
    raise SystemExit('CONSTRAINTNEAREST1A build version anchor missing')
back_p.write_text(back.replace('1.57-', '1.58-', 1))

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'CONSTRAINTNEAREST1A frozen seam changed unexpectedly: {rel}')

print('M9Cam CONSTRAINTNEAREST1A diagnostic promotion-candidate overlay applied')
print(' - PHOTOMETRICNORM1A nearest is the sole RAW-history promotion candidate')
print(' - top-2 and broad remain visible in CONSTRAINTLOCAL but are rejected for promotion')
print(' - logs whether nearest positive/mandatory ceiling would bind guarded request and by how much')
print(' - reports no-history vs no-normalized-match states for first-observation investigation')
print(' - 0.05 EV materiality threshold is reporting-only research calibration')
print(' - no FP1B, matcher, Camera2, allocator, guard, constraint math, renderer, JPEG or DNG mutation')
