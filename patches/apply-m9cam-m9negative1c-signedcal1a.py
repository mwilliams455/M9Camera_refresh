#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9negative1c-signedcal1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
p = root / negative_rel
if not p.exists():
    raise SystemExit('SIGNEDCAL1A requires generated M9NEGATIVE source')
s = p.read_text()
old_schema = 'm9cam.m9negative.v2.capturemeter1b.scenefingerprint1a'
new_schema = 'm9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a'
if old_schema not in s:
    raise SystemExit('SIGNEDCAL1A requires M9NEGATIVE1B / SCENEFINGERPRINT1A schema')
s = s.replace(old_schema, new_schema, 1)

# Add self-calibration coordinates to each completed RAW record. This is evidence only.
record_anchor = '''            out.put("pendingSceneCount", PENDING.size());\n            out.put("completedRawHistoryCount", COMPLETED.size());\n            out.put("reason", scene != null\n'''
record_repl = '''            out.put("pendingSceneCount", PENDING.size());\n            out.put("completedRawHistoryCount", COMPLETED.size());\n            out.put("signedCalibration1A", buildSignedCalibration(raw, "completed_raw_self"));\n            out.put("reason", scene != null\n'''
if record_anchor not in s:
    raise SystemExit('SIGNEDCAL1A completed RAW output anchor missing')
s = s.replace(record_anchor, record_repl, 1)

# Add the same coordinates for the matched source RAW used by capture-step evaluation.
eval_anchor = '''            out.put("additionalCaptureHeadroomEv", additionalCaptureHeadroomEv);\n            out.put("recommendedCaptureDeltaEv", recommendation);\n            out.put("recommendationBoundNegativeEv", MAX_NEGATIVE_DELTA_EV);\n'''
eval_repl = '''            out.put("additionalCaptureHeadroomEv", additionalCaptureHeadroomEv);\n            out.put("recommendedCaptureDeltaEv", recommendation);\n            out.put("recommendedCaptureDeltaEvModel", "frozen_m9negative1a_formula");\n            out.put("signedCalibration1A", buildSignedCalibration(best, "matched_completed_raw_source"));\n            out.put("recommendationBoundNegativeEv", MAX_NEGATIVE_DELTA_EV);\n'''
if eval_anchor not in s:
    raise SystemExit('SIGNEDCAL1A evaluation output anchor missing')
s = s.replace(eval_anchor, eval_repl, 1)

helper_anchor = '''    private static double normalizedDelta(double a, double b, double scale) {\n'''
helper = r'''    private static JSONObject buildSignedCalibration(CompletedRaw raw, String role) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", "m9cam.signedcal.v1.completedraw_coordinates1a");
            out.put("role", role);
            out.put("mode", "diagnostic_only_counterfactual_raw_scaling");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("sceneAssociationFrozen", "SCENEFINGERPRINT1A");
            out.put("recommendationFormulaFrozen", "M9NEGATIVE1A");
            if (raw == null) {
                out.put("valid", false);
                out.put("reason", "completed_raw_missing");
                return out;
            }

            double highlightStressFromTail = smoothstep(raw.q998, 0.88, 0.98);
            double clipRisk = smoothstep(raw.clip, 0.005, 0.030);
            double meaningfulClipRiskEvidence = clamp01(clipRisk
                    * Math.max(0.35, smoothstep(raw.q998, 0.72, 0.96)));
            double negativeHighlightStressEvidence = clamp01(Math.max(
                    highlightStressFromTail * (0.35 + 0.65 * meaningfulClipRiskEvidence),
                    meaningfulClipRiskEvidence));
            double q50Adequacy = smoothstep(raw.q50, 0.025, 0.080);
            double q25Adequacy = smoothstep(raw.q25, 0.006, 0.025);
            double lowerBodyAdequacy = clamp01(0.68 * q50Adequacy + 0.32 * q25Adequacy);
            double shadowStarvation = clamp01(1.0 - lowerBodyAdequacy);
            double rawHeadroomEv = log2(0.92 / Math.max(raw.q998, 1e-6));
            double additionalCaptureHeadroomEv = clamp(rawHeadroomEv, 0.0, MAX_POSITIVE_DELTA_EV)
                    * (1.0 - 0.80 * meaningfulClipRiskEvidence);
            double positiveCandidateEv = additionalCaptureHeadroomEv
                    * shadowStarvation
                    * (1.0 - 0.65 * negativeHighlightStressEvidence);
            double negativeCandidateBeforeGateEv = -0.35 * meaningfulClipRiskEvidence
                    * (1.0 - shadowStarvation);
            boolean negativeClipGatePass = meaningfulClipRiskEvidence > 0.45;
            boolean negativeBodyGatePass = shadowStarvation < 0.55;
            double negativeCandidateAppliedEv = negativeClipGatePass && negativeBodyGatePass
                    ? negativeCandidateBeforeGateEv : 0.0;
            double combinedBeforeDeadbandEv = clamp(positiveCandidateEv + negativeCandidateAppliedEv,
                    MAX_NEGATIVE_DELTA_EV, MAX_POSITIVE_DELTA_EV);
            double frozenRecommendationEv = Math.abs(combinedBeforeDeadbandEv) < 0.05
                    ? 0.0 : combinedBeforeDeadbandEv;

            out.put("valid", true);
            out.put("rawUq25", raw.q25);
            out.put("rawUq50", raw.q50);
            out.put("rawUq99", raw.q99);
            out.put("rawUq99_5", raw.q995);
            out.put("rawUq99_8", raw.q998);
            out.put("rawHardClipFraction", raw.clip);
            out.put("lowerBodyAdequacy", lowerBodyAdequacy);
            out.put("shadowStarvation", shadowStarvation);
            out.put("meaningfulClipRiskEvidence", meaningfulClipRiskEvidence);
            out.put("negativeHighlightStressEvidence", negativeHighlightStressEvidence);
            out.put("rawHeadroomTo0p92Ev", rawHeadroomEv);
            out.put("positiveCandidateEvBeforeDeadband", positiveCandidateEv);
            out.put("negativeCandidateBeforeGateEv", negativeCandidateBeforeGateEv);
            out.put("negativeClipGatePass", negativeClipGatePass);
            out.put("negativeBodyGatePass", negativeBodyGatePass);
            out.put("negativeGatePass", negativeClipGatePass && negativeBodyGatePass);
            out.put("negativeClipGateMargin", meaningfulClipRiskEvidence - 0.45);
            out.put("negativeBodyGateMargin", 0.55 - shadowStarvation);
            out.put("negativeCandidateAppliedByFrozenGateEv", negativeCandidateAppliedEv);
            out.put("combinedCandidateEvBeforeDeadband", combinedBeforeDeadbandEv);
            out.put("frozenRecommendedCaptureDeltaEv", frozenRecommendationEv);

            JSONObject coordinates = new JSONObject();
            putFinite(coordinates, "evToQ25_0p006", evToTarget(0.006, raw.q25));
            putFinite(coordinates, "evToQ25_0p025", evToTarget(0.025, raw.q25));
            putFinite(coordinates, "evToQ50_0p025", evToTarget(0.025, raw.q50));
            putFinite(coordinates, "evToQ50_0p055", evToTarget(0.055, raw.q50));
            putFinite(coordinates, "evToQ50_0p080", evToTarget(0.080, raw.q50));
            putFinite(coordinates, "evToQ99_8_0p880", evToTarget(0.880, raw.q998));
            putFinite(coordinates, "evToQ99_8_0p920", evToTarget(0.920, raw.q998));
            putFinite(coordinates, "evToQ99_8_0p980", evToTarget(0.980, raw.q998));
            out.put("signedExposureCoordinates", coordinates);

            JSONArray projections = new JSONArray();
            double[] evs = new double[] {-0.50, -0.25, 0.0, 0.25, 0.50};
            for (double ev : evs) projections.put(projectRawQuantiles(raw, ev));
            out.put("counterfactualLinearRawProjections", projections);
            out.put("projectionCaveat",
                    "quantiles_scaled_linearly_and_capped_only; hard_clip_fraction_and_scene_response_are_not_predicted");
            out.put("reason", "signed_calibration_coordinates_recorded_no_live_exposure_change");
        } catch (Exception e) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("usedToMutateCaptureTarget", false);
                out.put("reason", "signed_calibration_exception");
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static JSONObject projectRawQuantiles(CompletedRaw raw, double ev) {
        JSONObject out = new JSONObject();
        try {
            double factor = Math.pow(2.0, ev);
            double q998Uncapped = raw.q998 * factor;
            out.put("deltaEv", ev);
            out.put("linearScaleFactor", factor);
            out.put("projectedRawUq25", clamp(raw.q25 * factor, 0.0, 1.0));
            out.put("projectedRawUq50", clamp(raw.q50 * factor, 0.0, 1.0));
            out.put("projectedRawUq99", clamp(raw.q99 * factor, 0.0, 1.0));
            out.put("projectedRawUq99_5", clamp(raw.q995 * factor, 0.0, 1.0));
            out.put("projectedRawUq99_8", clamp(q998Uncapped, 0.0, 1.0));
            out.put("rawUq99_8Uncapped", q998Uncapped);
            out.put("rawUq99_8WouldReachOrExceedOne", q998Uncapped >= 1.0);
        } catch (Exception ignored) {}
        return out;
    }

    private static double evToTarget(double target, double measured) {
        if (!finite(target) || !finite(measured) || target <= 0.0 || measured <= 0.0) {
            return Double.NaN;
        }
        return log2(target / measured);
    }

    private static void putFinite(JSONObject out, String key, double value) {
        try {
            out.put(key, finite(value) ? value : JSONObject.NULL);
        } catch (Exception ignored) {}
    }

    private static double normalizedDelta(double a, double b, double scale) {
'''
if helper_anchor not in s:
    raise SystemExit('SIGNEDCAL1A helper insertion anchor missing')
s = s.replace(helper_anchor, helper, 1)
p.write_text(s)

coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
cp = root / coord_rel
c = cp.read_text()
old_coord = 'm9cam.exposuresplit.v3.capturemeter1b.m9negative1b.scenefingerprint1a'
new_coord = 'm9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a'
if old_coord not in c:
    raise SystemExit('SIGNEDCAL1A requires M9NEGATIVE1B coordinator schema')
c = c.replace(old_coord, new_coord, 1)
cp.write_text(c)

gradle = root / 'app/build.gradle'
g = gradle.read_text()
old_version = "versionName '1.46-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1b-fp1a-cm1b'"
new_version = "versionName '1.47-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-cm1b'"
if old_version not in g:
    raise SystemExit('SIGNEDCAL1A compact 1.46 versionName missing')
gradle.write_text(g.replace(old_version, new_version, 1))

back = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
if back.exists():
    b = back.read_text()
    old_marker = 'm9negative1bscenefingerprint1acapturemeter1b'
    new_marker = 'm9negative1csignedcal1ascenefingerprint1acapturemeter1b'
    if old_marker not in b:
        raise SystemExit('SIGNEDCAL1A forensic marker anchor missing')
    b = b.replace(old_marker, new_marker, 1)
    if '1.46-' in b:
        b = b.replace('1.46-', '1.47-', 1)
    back.write_text(b)

print('M9Cam M9NEGATIVE1C / SIGNEDCAL1A overlay applied')
print(' - SCENEFINGERPRINT1A distance, threshold and 60s recency gate frozen')
print(' - M9NEGATIVE1A recommendation equations and deadband frozen')
print(' - completed RAWs now emit self signed-calibration coordinates')
print(' - matched source RAWs emit the same coordinate/projection block')
print(' - counterfactual +/-0.25 and +/-0.50 EV projections are diagnostic only')
print(' - no Camera2, renderer, motion allocator, DNG or JPEG mutation')