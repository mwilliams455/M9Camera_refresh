package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * SCENEEXPOSURE1C: diagnostic-only signed scene exposure recommendation.
 *
 * 1C freezes the successful 1B positive architecture and repairs only the
 * negative/high-key interpretation. Broad >=192 brightness is no longer enough
 * to demand negative EV: meaningful near-white/highlight-danger support is required.
 */
public final class M9SceneExposureDiagnostic {
    public static final String SCHEMA = "m9cam.sceneexposure.v3.signedpressure1c";

    private static final double MAX_POSITIVE_EV = 1.25;
    private static final double MAX_NEGATIVE_EV = 1.25;
    private static final double NEUTRAL_DEADBAND_EV = 0.08;

    // Frozen from SCENEEXPOSURE1B positive architecture.
    private static final double BODY_MEDIAN_FULL_NEED_Y = 72.0;
    private static final double BODY_MEDIAN_ZERO_NEED_Y = 138.0;
    private static final double BODY_DARK64_LOW = 0.14;
    private static final double BODY_DARK64_HIGH = 0.38;
    private static final double CENTER_MEDIAN_FULL_NEED_Y = 72.0;
    private static final double CENTER_MEDIAN_ZERO_NEED_Y = 112.0;

    private static final double HEALTHY_CENTER_MEDIAN_LOW_Y = 140.0;
    private static final double HEALTHY_CENTER_MEDIAN_HIGH_Y = 165.0;
    private static final double HEALTHY_CENTER_DELTA_LOW_Y = 12.0;
    private static final double HEALTHY_CENTER_DELTA_HIGH_Y = 28.0;
    private static final double HEALTHY_CENTER_MAX_ATTENUATION = 0.88;
    private static final double SEVERE_BACKLIGHT_PRESERVE_START = 0.72;
    private static final double SEVERE_BACKLIGHT_PRESERVE_FULL = 0.90;

    // Legacy 1B negative candidate retained for side-by-side forensic output.
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

    // SCENEEXPOSURE1C negative/high-key support gate.
    private static final double NEAR_WHITE224_SUPPORT_LOW = 0.06;
    private static final double NEAR_WHITE224_SUPPORT_HIGH = 0.22;
    private static final double NEAR_CLIP240_SUPPORT_LOW = 0.025;
    private static final double NEAR_CLIP240_SUPPORT_HIGH = 0.10;
    private static final double Q95_DANGER_LOW_Y = 224.0;
    private static final double Q95_DANGER_HIGH_Y = 246.0;
    private static final double Q99_DANGER_LOW_Y = 238.0;
    private static final double Q99_DANGER_HIGH_Y = 252.0;
    private static final double Q95_NEARWHITE_SUPPORT_LOW = 0.04;
    private static final double Q95_NEARWHITE_SUPPORT_HIGH = 0.14;
    private static final double Q99_NEARWHITE_SUPPORT_LOW = 0.02;
    private static final double Q99_NEARWHITE_SUPPORT_HIGH = 0.08;
    private static final double MIDBRIGHT192_LOW = 0.35;
    private static final double MIDBRIGHT192_HIGH = 0.55;
    private static final double MIDBRIGHT_224_PROTECTION_LOW = 0.03;
    private static final double MIDBRIGHT_224_PROTECTION_HIGH = 0.08;
    private static final double MIDBRIGHT_240_PROTECTION_LOW = 0.005;
    private static final double MIDBRIGHT_240_PROTECTION_HIGH = 0.03;
    private static final double EMISSIVE_240_LOW = 0.001;
    private static final double EMISSIVE_240_HIGH = 0.02;
    private static final double EMISSIVE_224_BROAD_LOW = 0.03;
    private static final double EMISSIVE_224_BROAD_HIGH = 0.10;
    private static final double BROAD_MIDBRIGHT_GATE_ATTENUATION = 0.80;
    private static final double EMISSIVE_GATE_ATTENUATION = 0.65;

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
            out.put("calibration", "sceneexposure1c_negative_nearwhitegate1a_positive1b_frozen");
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
                    && finite(bright192) && finite(bright224) && finite(bright240)
                    && finite(centerMedian);
            out.put("valid", valid);
            if (!valid) {
                out.put("recommendedSignedEv", 0.0);
                out.put("reason", "non_finite_preview_luma");
                last = out;
                return;
            }

            // Reuse frozen LUMA2.4 only as pressure input. Live FB1 remains untouched.
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

            // ---- positive body/shadow pressure: intentionally frozen from 1B ----
            double medianNeed = 1.0 - smoothstep(median,
                    BODY_MEDIAN_FULL_NEED_Y, BODY_MEDIAN_ZERO_NEED_Y);
            double darkBodyNeed = smoothstep(dark64, BODY_DARK64_LOW, BODY_DARK64_HIGH);
            double centerNeed = 1.0 - smoothstep(centerMedian,
                    CENTER_MEDIAN_FULL_NEED_Y, CENTER_MEDIAN_ZERO_NEED_Y);

            double ordinaryBodyPressure = Math.max(medianNeed,
                    Math.max(0.70 * darkBodyNeed, 0.75 * centerNeed));
            double rawPositivePressure = Math.max(backlightPressure, ordinaryBodyPressure);

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

            // ---- legacy 1B negative candidate, retained for direct comparison ----
            double hotMedianPressure = smoothstep(median, HOT_MEDIAN_LOW_Y, HOT_MEDIAN_HIGH_Y);
            double broadBrightPressure = smoothstep(bright192,
                    BROAD_BRIGHT192_LOW, BROAD_BRIGHT192_HIGH);
            double hotQ95Pressure = smoothstep(q95, HOT_Q95_LOW_Y, HOT_Q95_HIGH_Y)
                    * smoothstep(bright192,
                    Q95_SUPPORT_BRIGHT192_LOW, Q95_SUPPORT_BRIGHT192_HIGH);
            double broadClipPressure = smoothstep(bright240,
                    BROAD_CLIP240_LOW, BROAD_CLIP240_HIGH);
            double legacy1bRawNegativePressure = Math.max(hotMedianPressure,
                    Math.max(broadBrightPressure, Math.max(hotQ95Pressure, broadClipPressure)));

            double bodyProtectionAgainstNegative = clamp01(Math.max(backlightPressure,
                    0.80 * centerNeed));
            double legacy1bNegativePressure = clamp01(legacy1bRawNegativePressure
                    * (1.0 - 0.75 * bodyProtectionAgainstNegative));
            double legacy1bNegativeCandidate = -MAX_NEGATIVE_EV * legacy1bNegativePressure;

            // ---- SCENEEXPOSURE1C near-white/highlight-danger support ----
            double nearWhiteSupport224 = smoothstep(bright224,
                    NEAR_WHITE224_SUPPORT_LOW, NEAR_WHITE224_SUPPORT_HIGH);
            double nearClipSupport240 = smoothstep(bright240,
                    NEAR_CLIP240_SUPPORT_LOW, NEAR_CLIP240_SUPPORT_HIGH);
            double q95HighlightDanger = smoothstep(q95, Q95_DANGER_LOW_Y, Q95_DANGER_HIGH_Y);
            double q99HighlightDanger = smoothstep(q99, Q99_DANGER_LOW_Y, Q99_DANGER_HIGH_Y);
            double q95NearWhiteSupport = q95HighlightDanger * smoothstep(bright224,
                    Q95_NEARWHITE_SUPPORT_LOW, Q95_NEARWHITE_SUPPORT_HIGH);
            double q99NearWhiteSupport = q99HighlightDanger * smoothstep(bright224,
                    Q99_NEARWHITE_SUPPORT_LOW, Q99_NEARWHITE_SUPPORT_HIGH);

            double broadMidBrightWithoutNearWhite = clamp01(
                    smoothstep(bright192, MIDBRIGHT192_LOW, MIDBRIGHT192_HIGH)
                    * (1.0 - smoothstep(bright224,
                    MIDBRIGHT_224_PROTECTION_LOW, MIDBRIGHT_224_PROTECTION_HIGH))
                    * (1.0 - smoothstep(bright240,
                    MIDBRIGHT_240_PROTECTION_LOW, MIDBRIGHT_240_PROTECTION_HIGH)));

            double emissiveOrSpecularToleranceWeight = clamp01(
                    smoothstep(bright240, EMISSIVE_240_LOW, EMISSIVE_240_HIGH)
                    * (1.0 - smoothstep(bright224,
                    EMISSIVE_224_BROAD_LOW, EMISSIVE_224_BROAD_HIGH)));

            double directHighlightSupport = Math.max(nearWhiteSupport224,
                    Math.max(nearClipSupport240,
                    Math.max(q95NearWhiteSupport, 0.85 * q99NearWhiteSupport)));
            double negativeHighlightSupportGate = clamp01(directHighlightSupport
                    * (1.0 - BROAD_MIDBRIGHT_GATE_ATTENUATION * broadMidBrightWithoutNearWhite)
                    * (1.0 - EMISSIVE_GATE_ATTENUATION * emissiveOrSpecularToleranceWeight));

            double negativeAfterNearWhiteGate = clamp01(legacy1bRawNegativePressure
                    * negativeHighlightSupportGate);
            double negativeAfterBodyProtection = clamp01(negativeAfterNearWhiteGate
                    * (1.0 - 0.75 * bodyProtectionAgainstNegative));
            double negativePressure = negativeAfterBodyProtection;
            double negativeEvCandidate = -MAX_NEGATIVE_EV * negativePressure;
            double sceneexposure1cNegativeCandidate = negativeEvCandidate;

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
            negative.put("legacy1bRawNegativePressure", legacy1bRawNegativePressure);
            negative.put("legacy1bNegativePressure", legacy1bNegativePressure);
            negative.put("legacy1bNegativeCandidate", legacy1bNegativeCandidate);
            negative.put("nearWhiteSupport224", nearWhiteSupport224);
            negative.put("nearClipSupport240", nearClipSupport240);
            negative.put("q95HighlightDanger", q95HighlightDanger);
            negative.put("q99HighlightDanger", q99HighlightDanger);
            negative.put("q95NearWhiteSupport", q95NearWhiteSupport);
            negative.put("q99NearWhiteSupport", q99NearWhiteSupport);
            negative.put("broadMidBrightWithoutNearWhite", broadMidBrightWithoutNearWhite);
            negative.put("emissiveOrSpecularToleranceWeight", emissiveOrSpecularToleranceWeight);
            negative.put("directHighlightSupport", directHighlightSupport);
            negative.put("negativeHighlightSupportGate", negativeHighlightSupportGate);
            negative.put("negativeAfterNearWhiteGate", negativeAfterNearWhiteGate);
            negative.put("bodyProtectionAgainstNegative", bodyProtectionAgainstNegative);
            negative.put("negativeAfterBodyProtection", negativeAfterBodyProtection);
            negative.put("negativePressure", negativePressure);
            negative.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            negative.put("negativeEvCandidate", negativeEvCandidate);
            if (negativeHighlightSupportGate <= 0.02 && broadMidBrightWithoutNearWhite >= 0.50) {
                negative.put("negativeGateReason", "broad_midbright_without_nearwhite_support");
            } else if (negativeHighlightSupportGate <= 0.02 && emissiveOrSpecularToleranceWeight >= 0.10) {
                negative.put("negativeGateReason", "small_emissive_or_specular_highlight_tolerated");
            } else if (negativeHighlightSupportGate <= 0.02) {
                negative.put("negativeGateReason", "insufficient_nearwhite_highlight_support");
            } else {
                negative.put("negativeGateReason", "supported_highlight_danger");
            }
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
            limits.put("nearWhite224SupportLow", NEAR_WHITE224_SUPPORT_LOW);
            limits.put("nearWhite224SupportHigh", NEAR_WHITE224_SUPPORT_HIGH);
            limits.put("nearClip240SupportLow", NEAR_CLIP240_SUPPORT_LOW);
            limits.put("nearClip240SupportHigh", NEAR_CLIP240_SUPPORT_HIGH);
            out.put("provisionalLimits", limits);

            out.put("positiveEvCandidate", positiveEvCandidate);
            out.put("legacy1bNegativeCandidate", legacy1bNegativeCandidate);
            out.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            out.put("negativeEvCandidate", negativeEvCandidate);
            out.put("recommendedSignedEv", signedEv);
            out.put("recommendationConfidence", Math.max(positivePressure, negativePressure));
            out.put("pressureConflict", Math.min(positivePressure, negativePressure));
            out.put("direction", signedEv > 0.0 ? "increase" : signedEv < 0.0 ? "decrease" : "neutral");

            if (signedEv > 0.0 && legacy1bNegativeCandidate < -0.20
                    && negativeHighlightSupportGate < 0.05) {
                out.put("reason", "signed_positive_after_false_highkey_negative_suppressed");
            } else if (signedEv > 0.0 && healthyCenterAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_healthy_center");
            } else if (signedEv > 0.0 && backlightPressure >= ordinaryBodyPressure) {
                out.put("reason", "signed_positive_spatial_or_backlight_body_need");
            } else if (signedEv > 0.0) {
                out.put("reason", "signed_positive_ordinary_body_need");
            } else if (signedEv < 0.0) {
                out.put("reason", "signed_negative_supported_highlight_danger");
            } else if (legacy1bNegativeCandidate < -NEUTRAL_DEADBAND_EV
                    && negativeHighlightSupportGate < 0.05) {
                out.put("reason", "signed_neutral_legacy_negative_suppressed_without_highlight_support");
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
