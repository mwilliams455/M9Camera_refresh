package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * SCENEEXPOSURE1B: diagnostic-only signed scene exposure recommendation.
 *
 * Photographic contract:
 * - DOES NOT mutate Photon exposure, FB1, M9 motion caps, ISO, shutter, or renderer math.
 * - DOES NOT alter R3.8/H25/TG1, TC20, Cobalt calibration, SAT3, curve02, BT.601,
 *   JPEG quality, output resolution, or any other frozen M9 rendering stage.
 * - Exists only to improve the recommendation model before any future live promotion.
 *
 * 1B is a narrow calibration revision based on device controls:
 * - ordinary indoor body: 1A was too conservative;
 * - severe window backlight: 1A was already strong/plausible and should be preserved;
 * - healthy centered outdoor subject with dark peripheral structure: 1A over-lifted;
 * - moving-bus backlight: strong spatial starvation remains a valid strong positive case.
 */
public final class M9SceneExposureDiagnostic {
    public static final String SCHEMA = "m9cam.sceneexposure.v2.signedpressure1b";

    private static final double MAX_POSITIVE_EV = 1.25;
    private static final double MAX_NEGATIVE_EV = 1.25;
    private static final double NEUTRAL_DEADBAND_EV = 0.08;

    // 1B ordinary-body calibration. The full-need point remains dark, but the zero-need
    // shoulder is extended from 112 -> 138 so an ordinary indoor body around Y~115 can
    // produce a modest ~+0.3/+0.4 EV diagnostic rather than collapsing to zero.
    private static final double BODY_MEDIAN_FULL_NEED_Y = 72.0;
    private static final double BODY_MEDIAN_ZERO_NEED_Y = 138.0;
    private static final double BODY_DARK64_LOW = 0.14;
    private static final double BODY_DARK64_HIGH = 0.38;
    private static final double CENTER_MEDIAN_FULL_NEED_Y = 72.0;
    private static final double CENTER_MEDIAN_ZERO_NEED_Y = 112.0;

    // Healthy-center protection applies only to moderate positive spatial pressure.
    // It is deliberately disabled as backlight pressure becomes severe so genuine
    // window/interior starvation and the moving-bus case retain the strong 1A response.
    private static final double HEALTHY_CENTER_MEDIAN_LOW_Y = 140.0;
    private static final double HEALTHY_CENTER_MEDIAN_HIGH_Y = 165.0;
    private static final double HEALTHY_CENTER_DELTA_LOW_Y = 12.0;
    private static final double HEALTHY_CENTER_DELTA_HIGH_Y = 28.0;
    private static final double HEALTHY_CENTER_MAX_ATTENUATION = 0.88;
    private static final double SEVERE_BACKLIGHT_PRESERVE_START = 0.72;
    private static final double SEVERE_BACKLIGHT_PRESERVE_FULL = 0.90;

    // Negative pressure remains unchanged from 1A until genuine negative controls are
    // captured. Tiny clipped windows, lamps, or speculars must not alone demand -EV.
    private static final double HOT_MEDIAN_LOW_Y = 150.0;
    private static final double HOT_MEDIAN_HIGH_Y = 205.0;
    private static final double BROAD_BRIGHT192_LOW = 0.18;
    private static final double BROAD_BRIGHT192_HIGH = 0.42;
    private static final double HOT_Q95_LOW_Y = 220.0;
    private static final double HOT_Q95_HIGH_Y = 250.0;
    private static final double Q95_SUPPORT_BRIGHT192_LOW = 0.08;
    private static final double Q95_SUPPORT_BRIGHT192_HIGH = 0.25;
    private static final double BROAD_CLIP240_LOW = 0.04;
    private static final double BROAD_CLIP240_HIGH = 0.18;

    private static JSONObject last = new JSONObject();

    private M9SceneExposureDiagnostic() {}

    public static synchronized void evaluateStep0(int step,
                                                   double previewEnergyIsoSeconds,
                                                   int cameraRotationDegrees) {
        if (step != 0) return;

        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("captureStep", 0);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("calibration", "sceneexposure1b_ordinarybody1a_healthycenter1a_severebacklightfreeze1a");
            out.put("previewLumaInterpretation", "nonlinear_preview_y_pressure_model_not_linear_raw_ev_meter");
            out.put("previewExposureEnergyIsoSeconds", previewEnergyIsoSeconds);
            out.put("cameraRotationDegrees", cameraRotationDegrees);

            JSONObject subject = M9SubjectMotionAnalyzer.snapshotJson(cameraRotationDegrees);
            JSONObject luma = subject.optJSONObject("previewLuma");
            JSONObject global = luma != null ? luma.optJSONObject("global") : null;
            JSONObject center = luma != null ? luma.optJSONObject("center50") : null;
            JSONObject spatial = luma != null ? luma.optJSONObject("spatial3x3") : null;

            long frames = luma != null ? luma.optLong("framesAnalyzed", 0L) : 0L;
            boolean spatialValid = spatial != null && spatial.optBoolean("valid", false);
            boolean valid = frames >= 3L && global != null && spatialValid;
            out.put("valid", valid);
            out.put("previewLumaFrames", frames);
            if (!valid) {
                out.put("recommendedSignedEv", 0.0);
                out.put("reason", "insufficient_preview_luma_history");
                last = out;
                return;
            }

            double median = global.optDouble("median", Double.NaN);
            double q95 = global.optDouble("q95", Double.NaN);
            double q99 = global.optDouble("q99", Double.NaN);
            double dark64 = global.optDouble("darkFractionLE64", Double.NaN);
            double bright192 = global.optDouble("brightFractionGE192", Double.NaN);
            double bright224 = global.optDouble("brightFractionGE224", Double.NaN);
            double bright240 = global.optDouble("brightFractionGE240", Double.NaN);
            double centerMedian = center != null ? center.optDouble("median", Double.NaN) : Double.NaN;
            double centerDelta = center != null
                    ? center.optDouble("medianMinusGlobalMedian", Double.NaN) : Double.NaN;

            valid = finite(median) && finite(q95) && finite(q99) && finite(dark64)
                    && finite(bright192) && finite(bright240) && finite(centerMedian);
            out.put("valid", valid);
            if (!valid) {
                out.put("recommendedSignedEv", 0.0);
                out.put("reason", "non_finite_preview_luma");
                last = out;
                return;
            }

            // Reuse the frozen LUMA2.4 classifier only as a pressure input. Its live FB1
            // behavior and all exposure allocation remain untouched by this class.
            JSONObject preview = new JSONObject();
            preview.put("exposureEnergyIsoSeconds", previewEnergyIsoSeconds);
            JSONObject photon = new JSONObject();
            photon.put("preview", preview);
            JSONObject syntheticRoot = new JSONObject();
            syntheticRoot.put("photonExposureDecision", photon);
            syntheticRoot.put("subjectMotion", subject);
            JSONObject luma24 = M9BacklightDiagnostic.snapshotJson(syntheticRoot);
            JSONObject oldComponents = luma24.optJSONObject("componentScores");
            double backlightPressure = oldComponents != null
                    ? oldComponents.optDouble("backlightStarvationScore", 0.0) : 0.0;
            double contrastIntentProtection = oldComponents != null
                    ? oldComponents.optDouble("landscapeHighContrastProtectionScore", 0.0) : 0.0;

            // ---- positive body/shadow pressure ----
            double medianNeed = 1.0 - smoothstep(median,
                    BODY_MEDIAN_FULL_NEED_Y, BODY_MEDIAN_ZERO_NEED_Y);
            double darkBodyNeed = smoothstep(dark64, BODY_DARK64_LOW, BODY_DARK64_HIGH);
            double centerNeed = 1.0 - smoothstep(centerMedian,
                    CENTER_MEDIAN_FULL_NEED_Y, CENTER_MEDIAN_ZERO_NEED_Y);

            double ordinaryBodyPressure = Math.max(medianNeed,
                    Math.max(0.70 * darkBodyNeed, 0.75 * centerNeed));
            double rawPositivePressure = Math.max(backlightPressure, ordinaryBodyPressure);

            // Healthy-center protection is specifically a moderate-pressure guard. A
            // centered subject that is already comfortably bright should not be lifted
            // merely because peripheral foliage/background is dark. Once backlight
            // pressure reaches the severe range, attenuation smoothly disappears.
            double healthyCenterMedian = smoothstep(centerMedian,
                    HEALTHY_CENTER_MEDIAN_LOW_Y, HEALTHY_CENTER_MEDIAN_HIGH_Y);
            double healthyCenterDelta = finite(centerDelta)
                    ? smoothstep(centerDelta, HEALTHY_CENTER_DELTA_LOW_Y, HEALTHY_CENTER_DELTA_HIGH_Y)
                    : 0.0;
            double healthyCenterProtection = clamp01(healthyCenterMedian * healthyCenterDelta);
            double severeBacklightPreservationWeight = smoothstep(backlightPressure,
                    SEVERE_BACKLIGHT_PRESERVE_START, SEVERE_BACKLIGHT_PRESERVE_FULL);
            double moderatePressureProtectionWeight = 1.0 - severeBacklightPreservationWeight;
            double healthyCenterAttenuation = HEALTHY_CENTER_MAX_ATTENUATION
                    * healthyCenterProtection * moderatePressureProtectionWeight;

            double centerProtectedPositivePressure = clamp01(rawPositivePressure
                    * (1.0 - healthyCenterAttenuation));
            double positivePressure = clamp01(centerProtectedPositivePressure
                    * (1.0 - 0.75 * clamp01(contrastIntentProtection)));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;

            // ---- negative broad/high-key highlight pressure: unchanged from 1A ----
            double hotMedianPressure = smoothstep(median, HOT_MEDIAN_LOW_Y, HOT_MEDIAN_HIGH_Y);
            double broadBrightPressure = smoothstep(bright192,
                    BROAD_BRIGHT192_LOW, BROAD_BRIGHT192_HIGH);
            double hotQ95Pressure = smoothstep(q95, HOT_Q95_LOW_Y, HOT_Q95_HIGH_Y)
                    * smoothstep(bright192,
                    Q95_SUPPORT_BRIGHT192_LOW, Q95_SUPPORT_BRIGHT192_HIGH);
            double broadClipPressure = smoothstep(bright240,
                    BROAD_CLIP240_LOW, BROAD_CLIP240_HIGH);
            double rawNegativePressure = Math.max(hotMedianPressure,
                    Math.max(broadBrightPressure, Math.max(hotQ95Pressure, broadClipPressure)));

            double bodyProtectionAgainstNegative = clamp01(Math.max(backlightPressure,
                    0.80 * centerNeed));
            double negativePressure = clamp01(rawNegativePressure
                    * (1.0 - 0.75 * bodyProtectionAgainstNegative));
            double negativeEvCandidate = -MAX_NEGATIVE_EV * negativePressure;

            double signedEv = clamp(positiveEvCandidate + negativeEvCandidate,
                    -MAX_NEGATIVE_EV, MAX_POSITIVE_EV);
            if (Math.abs(signedEv) < NEUTRAL_DEADBAND_EV) signedEv = 0.0;

            JSONObject inputs = new JSONObject();
            inputs.put("globalMedian", median);
            inputs.put("globalQ95", q95);
            inputs.put("globalQ99", q99);
            inputs.put("darkFractionLE64", dark64);
            inputs.put("brightFractionGE192", bright192);
            inputs.put("brightFractionGE224", bright224);
            inputs.put("brightFractionGE240", bright240);
            inputs.put("centerMedian", centerMedian);
            if (finite(centerDelta)) inputs.put("centerMedianMinusGlobalMedian", centerDelta);
            out.put("inputs", inputs);

            JSONObject positive = new JSONObject();
            positive.put("medianNeed", medianNeed);
            positive.put("darkBodyNeed", darkBodyNeed);
            positive.put("centerNeed", centerNeed);
            positive.put("ordinaryBodyPressure", ordinaryBodyPressure);
            positive.put("luma24BacklightPressure", backlightPressure);
            positive.put("rawPositivePressure", rawPositivePressure);
            positive.put("healthyCenterMedian", healthyCenterMedian);
            positive.put("healthyCenterDelta", healthyCenterDelta);
            positive.put("healthyCenterProtection", healthyCenterProtection);
            positive.put("severeBacklightPreservationWeight", severeBacklightPreservationWeight);
            positive.put("moderatePressureProtectionWeight", moderatePressureProtectionWeight);
            positive.put("healthyCenterAttenuation", healthyCenterAttenuation);
            positive.put("centerProtectedPositivePressure", centerProtectedPositivePressure);
            positive.put("contrastIntentProtection", contrastIntentProtection);
            positive.put("positivePressure", positivePressure);
            positive.put("positiveEvCandidate", positiveEvCandidate);
            out.put("positiveBodyPressure", positive);

            JSONObject negative = new JSONObject();
            negative.put("hotMedianPressure", hotMedianPressure);
            negative.put("broadBright192Pressure", broadBrightPressure);
            negative.put("hotQ95WithBrightSupportPressure", hotQ95Pressure);
            negative.put("broadClip240Pressure", broadClipPressure);
            negative.put("rawNegativePressure", rawNegativePressure);
            negative.put("bodyProtectionAgainstNegative", bodyProtectionAgainstNegative);
            negative.put("negativePressure", negativePressure);
            negative.put("negativeEvCandidate", negativeEvCandidate);
            out.put("negativeHighlightPressure", negative);

            JSONObject legacy = new JSONObject();
            legacy.put("fb1WouldApply", luma24.optBoolean("wouldApply", false));
            legacy.put("fb1RecommendedEv", luma24.optDouble("recommendedExposureCorrectionEv", 0.0));
            legacy.put("fb1Reason", luma24.optString("reason", "unknown"));
            out.put("legacyFb1Reference", legacy);

            JSONObject limits = new JSONObject();
            limits.put("diagnosticPositiveLimitEv", MAX_POSITIVE_EV);
            limits.put("diagnosticNegativeLimitEv", -MAX_NEGATIVE_EV);
            limits.put("neutralDeadbandEv", NEUTRAL_DEADBAND_EV);
            limits.put("ordinaryBodyMedianZeroNeedY", BODY_MEDIAN_ZERO_NEED_Y);
            limits.put("healthyCenterMaxAttenuation", HEALTHY_CENTER_MAX_ATTENUATION);
            limits.put("severeBacklightPreserveStart", SEVERE_BACKLIGHT_PRESERVE_START);
            limits.put("severeBacklightPreserveFull", SEVERE_BACKLIGHT_PRESERVE_FULL);
            out.put("provisionalLimits", limits);

            out.put("positiveEvCandidate", positiveEvCandidate);
            out.put("negativeEvCandidate", negativeEvCandidate);
            out.put("recommendedSignedEv", signedEv);
            out.put("recommendationConfidence", Math.max(positivePressure, negativePressure));
            out.put("pressureConflict", Math.min(positivePressure, negativePressure));
            out.put("direction", signedEv > 0.0 ? "increase" : signedEv < 0.0 ? "decrease" : "neutral");

            if (signedEv > 0.0 && healthyCenterAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_healthy_center");
            } else if (signedEv > 0.0 && backlightPressure >= ordinaryBodyPressure) {
                out.put("reason", "signed_positive_spatial_or_backlight_body_need");
            } else if (signedEv > 0.0) {
                out.put("reason", "signed_positive_ordinary_body_need");
            } else if (signedEv < 0.0) {
                out.put("reason", "signed_negative_broad_highlight_pressure");
            } else if (positivePressure > 0.0 || negativePressure > 0.0) {
                out.put("reason", "signed_pressures_balance_inside_deadband");
            } else {
                out.put("reason", "signed_neutral_no_material_pressure");
            }
        } catch (Exception ignored) {
            try {
                out.put("valid", false);
                out.put("recommendedSignedEv", 0.0);
                out.put("reason", "scene_exposure_diagnostic_exception");
            } catch (Exception ignoredAgain) {}
        }
        last = out;
    }

    public static synchronized JSONObject snapshotJson() {
        try {
            return new JSONObject(last.toString());
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private static double smoothstep(double x, double lo, double hi) {
        if (!finite(x)) return 0.0;
        if (hi <= lo) return x >= hi ? 1.0 : 0.0;
        double t = clamp01((x - lo) / (hi - lo));
        return t * t * (3.0 - 2.0 * t);
    }

    private static double clamp01(double x) {
        return clamp(x, 0.0, 1.0);
    }

    private static double clamp(double x, double lo, double hi) {
        return Math.max(lo, Math.min(hi, x));
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }
}
