package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * v0.7N LUMA2.4-SPATIAL2-FB1 live-feedback scorer.
 *
 * Direct derivative of v0.7L. The frozen LUMA2.2 scalar branches are retained:
 *   1) relative backlight structure x low preview-energy starvation;
 *   2) center-body protection on that relative branch;
 *   3) catastrophic whole-preview collapse branch.
 *
 * LUMA2.4 adds two orientation-aware spatial mechanisms using the v0.7L 3x3
 * displayed-space preview-luma snapshot:
 *
 *   A. SPATIAL2 landscape/high-contrast guard. Broad bright occupancy that is
 *      concentrated in the displayed top row AND has strong top-row median
 *      heterogeneity attenuates ordinary relative/spatial backlight evidence.
 *      The catastrophic preview-collapse branch is never suppressed.
 *
 *   B. Spatial foreground-starvation branch. A sufficiently dark scene body,
 *      meaningful highlight support, strong axis-wise displayed-space median
 *      separation, and a collapsed dark region can establish backlight
 *      starvation even when absolute ISO*shutter exposure energy is high.
 *
 * FB1 is the first bounded live-feedback candidate. The LUMA2.4 thresholds are
 * unchanged from field-validated v0.7M. Only when the classifier crosses the
 * existing would-apply gate does it return 0..+0.75 EV for the Photon target
 * exposure energy. The actual pre/post target and resulting capture allocation
 * are logged separately for auditability.
 */
public final class M9BacklightDiagnostic {
    public static final String BUILD_VERSION = "1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a";
    public static final String SCHEMA = "m9cam.backlightdiagnostic.v4.luma2p4";

    // Frozen LUMA2/LUMA2.1 ramps.
    private static final double DARK64_LOW = 0.20;
    private static final double DARK64_HIGH = 0.35;
    private static final double BRIGHT192_LOW = 0.04;
    private static final double BRIGHT192_HIGH = 0.10;
    private static final double SEPARATION_LOW = 60.0;
    private static final double SEPARATION_HIGH = 110.0;
    private static final double ENERGY_FULL_SCORE = 1.00;
    private static final double ENERGY_ZERO_SCORE = 2.50;
    private static final double ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR = 0.62;

    // Frozen LUMA2.2 center-body protection.
    private static final double CENTER_PROTECTION_START_Y = 16.0;
    private static final double CENTER_PROTECTION_FULL_Y = 28.0;

    // Frozen LUMA2.2 catastrophic/global preview-collapse branch.
    private static final double CATA_ENERGY_FULL_SCORE = 0.03;
    private static final double CATA_ENERGY_ZERO_SCORE = 0.12;
    private static final double CATA_MEDIAN_FULL_DARK_Y = 32.0;
    private static final double CATA_MEDIAN_ZERO_DARK_Y = 64.0;
    private static final double CATA_Q95_FULL_DARK_Y = 64.0;
    private static final double CATA_Q95_ZERO_DARK_Y = 96.0;
    private static final double CATA_Q99_FULL_DARK_Y = 80.0;
    private static final double CATA_Q99_ZERO_DARK_Y = 112.0;

    // SPATIAL2 guard from the dual-proxy 191721/191728 replay. This is a
    // protection against usable bright-sky/high-contrast landscapes. All three
    // conditions must be present; missing spatial data is neutral (guard 0).
    private static final double LANDSCAPE_BRIGHT192_LOW = 0.15;
    private static final double LANDSCAPE_BRIGHT192_HIGH = 0.20;
    private static final double LANDSCAPE_TOP_BRIGHT_SHARE_LOW = 0.72;
    private static final double LANDSCAPE_TOP_BRIGHT_SHARE_HIGH = 0.90;
    private static final double LANDSCAPE_TOP_MEDIAN_HETERO_LOW = 0.28;
    private static final double LANDSCAPE_TOP_MEDIAN_HETERO_HIGH = 0.55;

    // New high-energy spatial foreground-starvation branch. These provisional
    // ramps are constrained by the exact v0.7L preview-Y captures 065330 and
    // 065403 (positive) versus 072515 (negative). The dark-body floor prevents
    // bright-window structure by itself from becoming a positive trigger.
    private static final double SPATIAL_DARK64_LOW = 0.28;
    private static final double SPATIAL_DARK64_HIGH = 0.35;
    private static final double SPATIAL_Q95_LOW_Y = 135.0;
    private static final double SPATIAL_Q95_HIGH_Y = 175.0;
    private static final double SPATIAL_BRIGHT192_LOW = 0.008;
    private static final double SPATIAL_BRIGHT192_HIGH = 0.035;
    private static final double SPATIAL_AXIS_SPREAD_LOW = 0.30;
    private static final double SPATIAL_AXIS_SPREAD_HIGH = 0.48;
    private static final double SPATIAL_LOW_REGION_RATIO_FULL = 0.28;
    private static final double SPATIAL_LOW_REGION_RATIO_ZERO = 0.40;

    // Frozen recommendation gate/cap.
    private static final double APPLY_SCORE = 0.50;
    private static final double EV_RAMP_LOW = 0.35;
    private static final double EV_RAMP_HIGH = 0.85;
    private static final double MAX_RECOMMENDED_EV = 0.75;

    private static JSONObject lastLiveFeedback = new JSONObject();

    public static final class LiveFeedbackDecision {
        public final boolean valid;
        public final boolean wouldApply;
        public final double recommendedEv;
        public final double appliedEv;
        public final String reason;
        private final JSONObject classifierSnapshot;

        LiveFeedbackDecision(boolean valid, boolean wouldApply, double recommendedEv,
                             double appliedEv, String reason, JSONObject classifierSnapshot) {
            this.valid = valid;
            this.wouldApply = wouldApply;
            this.recommendedEv = recommendedEv;
            this.appliedEv = appliedEv;
            this.reason = reason;
            this.classifierSnapshot = classifierSnapshot;
        }
    }

    private M9BacklightDiagnostic() {}

    public static JSONObject buildIdentityJson() {
        JSONObject o = new JSONObject();
        try {
            o.put("version", BUILD_VERSION);
            o.put("instrumentation", "LUMA2.4-SPATIAL2-FB1");
            o.put("diagnosticOnly", false);
            o.put("exposureFeedbackEnabled", true);
            o.put("subjectMotionSchemaExpected", "m9cam.subjectmotion.v3.luma1");
            o.put("previewLumaSchemaExpected", "m9cam.previewluma.v2.spatial1");
            o.put("spatialPreviewLumaSchemaExpected", "m9cam.previewluma.spatial3x3.v1");
            o.put("backlightScorer", "LUMA2.4");
            o.put("spatialScoringEnabled", true);
            o.put("spatialExposureFeedbackEnabled", true);
            o.put("backlightDiagnosticSchema", SCHEMA);
            o.put("rendererSchemaFrozen", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1");
        } catch (Exception ignored) {
        }
        return o;
    }

    public static JSONObject snapshotJson(JSONObject root) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "live_feedback_enabled");
            JSONObject liveFeedback = feedbackSnapshotJson();
            out.put("appliedExposureCorrectionEv", liveFeedback.optDouble("appliedExposureCorrectionEv", 0.0));

            JSONObject photon = root != null ? root.optJSONObject("photonExposureDecision") : null;
            JSONObject preview = photon != null ? photon.optJSONObject("preview") : null;
            JSONObject subject = root != null ? root.optJSONObject("subjectMotion") : null;
            JSONObject luma = subject != null ? subject.optJSONObject("previewLuma") : null;
            JSONObject global = luma != null ? luma.optJSONObject("global") : null;
            JSONObject center = luma != null ? luma.optJSONObject("center50") : null;
            JSONObject spatial = luma != null ? luma.optJSONObject("spatial3x3") : null;

            boolean valid = preview != null && global != null;
            out.put("valid", valid);
            if (!valid) {
                out.put("wouldApply", false);
                out.put("recommendedExposureCorrectionEv", 0.0);
                out.put("reason", "missing_preview_energy_or_luma");
                return out;
            }

            double energy = preview.optDouble("exposureEnergyIsoSeconds", Double.NaN);
            double dark64 = global.optDouble("darkFractionLE64", Double.NaN);
            double bright192 = global.optDouble("brightFractionGE192", Double.NaN);
            double bright224 = global.optDouble("brightFractionGE224", Double.NaN);
            double bright240 = global.optDouble("brightFractionGE240", Double.NaN);
            double median = global.optDouble("median", Double.NaN);
            double q95 = global.optDouble("q95", Double.NaN);
            double q99 = global.optDouble("q99", Double.NaN);
            double separation = global.optDouble("q95MinusMedian", q95 - median);
            double centerMedianDelta = center != null
                    ? center.optDouble("medianMinusGlobalMedian", Double.NaN)
                    : Double.NaN;

            valid = finite(energy) && finite(dark64) && finite(bright192)
                    && finite(median) && finite(q95) && finite(q99) && finite(separation);
            out.put("valid", valid);
            if (!valid) {
                out.put("wouldApply", false);
                out.put("recommendedExposureCorrectionEv", 0.0);
                out.put("reason", "non_finite_preview_energy_or_luma");
                return out;
            }

            // ---- Frozen LUMA2.2 scalar branch ----
            double darkScore = smoothstep(dark64, DARK64_LOW, DARK64_HIGH);
            double brightScore = smoothstep(bright192, BRIGHT192_LOW, BRIGHT192_HIGH);
            double separationScore = smoothstep(separation, SEPARATION_LOW, SEPARATION_HIGH);

            double relativeProduct = Math.max(0.0, darkScore * separationScore);
            double relativeStructureScore = relativeProduct > 0.0
                    ? Math.cbrt(relativeProduct)
                    : 0.0;
            double absoluteBrightConfidenceMultiplier =
                    ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR
                            + (1.0 - ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR) * brightScore;
            double structureScore = clamp01(
                    relativeStructureScore * absoluteBrightConfidenceMultiplier);
            double energyStarvationScore =
                    1.0 - smoothstep(energy, ENERGY_FULL_SCORE, ENERGY_ZERO_SCORE);
            double rawRelativeBacklightStarvationScore =
                    clamp01(structureScore * energyStarvationScore);

            double centerBodyProtectionScore = finite(centerMedianDelta)
                    ? smoothstep(centerMedianDelta,
                            CENTER_PROTECTION_START_Y,
                            CENTER_PROTECTION_FULL_Y)
                    : 0.0;
            double centerBodyProtectionMultiplier = 1.0 - centerBodyProtectionScore;
            double centerProtectedRelativeScore = clamp01(
                    rawRelativeBacklightStarvationScore * centerBodyProtectionMultiplier);

            // ---- Frozen catastrophic branch ----
            double catastrophicEnergyStarvationScore =
                    1.0 - smoothstep(energy, CATA_ENERGY_FULL_SCORE, CATA_ENERGY_ZERO_SCORE);
            double catastrophicMedianDarkScore =
                    1.0 - smoothstep(median, CATA_MEDIAN_FULL_DARK_Y, CATA_MEDIAN_ZERO_DARK_Y);
            double catastrophicQ95DarkScore =
                    1.0 - smoothstep(q95, CATA_Q95_FULL_DARK_Y, CATA_Q95_ZERO_DARK_Y);
            double catastrophicQ99DarkScore =
                    1.0 - smoothstep(q99, CATA_Q99_FULL_DARK_Y, CATA_Q99_ZERO_DARK_Y);
            double collapseProduct = Math.max(0.0,
                    catastrophicMedianDarkScore
                            * catastrophicQ95DarkScore
                            * catastrophicQ99DarkScore);
            double catastrophicPreviewCollapseScore = collapseProduct > 0.0
                    ? Math.cbrt(collapseProduct)
                    : 0.0;
            double catastrophicAeStarvationScore = clamp01(
                    catastrophicEnergyStarvationScore * catastrophicPreviewCollapseScore);

            // ---- LUMA2.4 SPATIAL2 ----
            SpatialFeatures sf = spatialFeatures(spatial, q95);

            double landscapeBroadBrightScore = smoothstep(
                    bright192, LANDSCAPE_BRIGHT192_LOW, LANDSCAPE_BRIGHT192_HIGH);
            double landscapeTopBrightConcentrationScore = sf.valid
                    ? smoothstep(sf.topBrightShare,
                            LANDSCAPE_TOP_BRIGHT_SHARE_LOW,
                            LANDSCAPE_TOP_BRIGHT_SHARE_HIGH)
                    : 0.0;
            double landscapeTopMedianHeterogeneityScore = sf.valid
                    ? smoothstep(sf.topMedianHeterogeneity,
                            LANDSCAPE_TOP_MEDIAN_HETERO_LOW,
                            LANDSCAPE_TOP_MEDIAN_HETERO_HIGH)
                    : 0.0;
            double landscapeProduct = Math.max(0.0,
                    landscapeBroadBrightScore
                            * landscapeTopBrightConcentrationScore
                            * landscapeTopMedianHeterogeneityScore);
            double landscapeHighContrastProtectionScore = landscapeProduct > 0.0
                    ? Math.cbrt(landscapeProduct)
                    : 0.0;
            double landscapeProtectionMultiplier =
                    1.0 - landscapeHighContrastProtectionScore;

            // The landscape guard is allowed to protect both ordinary low-energy
            // relative evidence and the new high-energy spatial branch, but never
            // the catastrophic whole-preview-collapse branch.
            double protectedRelativeBacklightStarvationScore = clamp01(
                    centerProtectedRelativeScore * landscapeProtectionMultiplier);

            double spatialDarkBodyScore = smoothstep(
                    dark64, SPATIAL_DARK64_LOW, SPATIAL_DARK64_HIGH);
            double spatialHighlightQ95Score = smoothstep(
                    q95, SPATIAL_Q95_LOW_Y, SPATIAL_Q95_HIGH_Y);
            double spatialBrightSupportScore = smoothstep(
                    bright192, SPATIAL_BRIGHT192_LOW, SPATIAL_BRIGHT192_HIGH);
            double spatialAxisSeparationScore = sf.valid
                    ? smoothstep(sf.normalizedAxisMedianSpread,
                            SPATIAL_AXIS_SPREAD_LOW,
                            SPATIAL_AXIS_SPREAD_HIGH)
                    : 0.0;
            double spatialLowRegionCollapseScore = sf.valid
                    ? 1.0 - smoothstep(sf.lowRegionMedianOverQ95,
                            SPATIAL_LOW_REGION_RATIO_FULL,
                            SPATIAL_LOW_REGION_RATIO_ZERO)
                    : 0.0;

            double spatialProduct = Math.max(0.0,
                    spatialDarkBodyScore
                            * spatialHighlightQ95Score
                            * spatialBrightSupportScore
                            * spatialAxisSeparationScore
                            * spatialLowRegionCollapseScore);
            double rawSpatialBacklightStarvationScore = spatialProduct > 0.0
                    ? Math.pow(spatialProduct, 1.0 / 5.0)
                    : 0.0;
            double protectedSpatialBacklightStarvationScore = clamp01(
                    rawSpatialBacklightStarvationScore * landscapeProtectionMultiplier);

            // Final LUMA2.4 union. Catastrophic preview collapse stays independent
            // and authoritative. Exposure feedback remains OFF in this build.
            double backlightStarvationScore = Math.max(
                    catastrophicAeStarvationScore,
                    Math.max(protectedRelativeBacklightStarvationScore,
                            protectedSpatialBacklightStarvationScore));
            double recommendationStrength =
                    smoothstep(backlightStarvationScore, EV_RAMP_LOW, EV_RAMP_HIGH);
            double recommendedEv = MAX_RECOMMENDED_EV * recommendationStrength;
            boolean wouldApply = backlightStarvationScore >= APPLY_SCORE;

            JSONObject inputs = new JSONObject();
            inputs.put("previewExposureEnergyIsoSeconds", energy);
            inputs.put("globalMedian", median);
            inputs.put("globalQ95", q95);
            inputs.put("globalQ99", q99);
            inputs.put("darkFractionLE64", dark64);
            inputs.put("brightFractionGE192", bright192);
            inputs.put("brightFractionGE224", bright224);
            inputs.put("brightFractionGE240", bright240);
            inputs.put("q95MinusMedian", separation);
            if (finite(centerMedianDelta)) {
                inputs.put("centerMedianMinusGlobalMedian", centerMedianDelta);
            }
            inputs.put("spatialValid", sf.valid);
            if (sf.valid) {
                inputs.put("spatialAxisMedianSpreadY", sf.axisMedianSpreadY);
                inputs.put("spatialAxisMedianSpreadOverQ95", sf.normalizedAxisMedianSpread);
                inputs.put("spatialLowRegionMedianY", sf.lowRegionMedianY);
                inputs.put("spatialLowRegionMedianOverQ95", sf.lowRegionMedianOverQ95);
                inputs.put("spatialTopBrightShare", sf.topBrightShare);
                inputs.put("spatialTopRowMedianHeterogeneityOverQ95", sf.topMedianHeterogeneity);
            }
            out.put("inputs", inputs);

            JSONObject components = new JSONObject();
            components.put("darkBodyScore", darkScore);
            components.put("brightPopulationScore", brightScore);
            components.put("bodyHighlightSeparationScore", separationScore);
            components.put("relativeBodyHighlightStructureScore", relativeStructureScore);
            components.put("absoluteBrightConfidenceMultiplier", absoluteBrightConfidenceMultiplier);
            components.put("backlightStructureScore", structureScore);
            components.put("energyStarvationScore", energyStarvationScore);
            components.put("rawRelativeBacklightStarvationScore", rawRelativeBacklightStarvationScore);
            components.put("centerBodyProtectionScore", centerBodyProtectionScore);
            components.put("centerBodyProtectionMultiplier", centerBodyProtectionMultiplier);
            components.put("centerProtectedRelativeBacklightStarvationScore", centerProtectedRelativeScore);
            components.put("landscapeBroadBrightScore", landscapeBroadBrightScore);
            components.put("landscapeTopBrightConcentrationScore", landscapeTopBrightConcentrationScore);
            components.put("landscapeTopMedianHeterogeneityScore", landscapeTopMedianHeterogeneityScore);
            components.put("landscapeHighContrastProtectionScore", landscapeHighContrastProtectionScore);
            components.put("landscapeProtectionMultiplier", landscapeProtectionMultiplier);
            components.put("protectedRelativeBacklightStarvationScore", protectedRelativeBacklightStarvationScore);
            components.put("spatialDarkBodyScore", spatialDarkBodyScore);
            components.put("spatialHighlightQ95Score", spatialHighlightQ95Score);
            components.put("spatialBrightSupportScore", spatialBrightSupportScore);
            components.put("spatialAxisSeparationScore", spatialAxisSeparationScore);
            components.put("spatialLowRegionCollapseScore", spatialLowRegionCollapseScore);
            components.put("rawSpatialBacklightStarvationScore", rawSpatialBacklightStarvationScore);
            components.put("protectedSpatialBacklightStarvationScore", protectedSpatialBacklightStarvationScore);
            components.put("catastrophicEnergyStarvationScore", catastrophicEnergyStarvationScore);
            components.put("catastrophicMedianDarkScore", catastrophicMedianDarkScore);
            components.put("catastrophicQ95DarkScore", catastrophicQ95DarkScore);
            components.put("catastrophicQ99DarkScore", catastrophicQ99DarkScore);
            components.put("catastrophicPreviewCollapseScore", catastrophicPreviewCollapseScore);
            components.put("catastrophicAeStarvationScore", catastrophicAeStarvationScore);
            components.put("backlightStarvationScore", backlightStarvationScore);
            out.put("componentScores", components);

            JSONObject thresholds = new JSONObject();
            thresholds.put("dark64RampLow", DARK64_LOW);
            thresholds.put("dark64RampHigh", DARK64_HIGH);
            thresholds.put("bright192RampLow", BRIGHT192_LOW);
            thresholds.put("bright192RampHigh", BRIGHT192_HIGH);
            thresholds.put("absoluteBrightConfidenceFloor", ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR);
            thresholds.put("q95MinusMedianRampLow", SEPARATION_LOW);
            thresholds.put("q95MinusMedianRampHigh", SEPARATION_HIGH);
            thresholds.put("energyFullScoreIsoSeconds", ENERGY_FULL_SCORE);
            thresholds.put("energyZeroScoreIsoSeconds", ENERGY_ZERO_SCORE);
            thresholds.put("centerProtectionStartY", CENTER_PROTECTION_START_Y);
            thresholds.put("centerProtectionFullY", CENTER_PROTECTION_FULL_Y);
            thresholds.put("catastrophicEnergyFullScoreIsoSeconds", CATA_ENERGY_FULL_SCORE);
            thresholds.put("catastrophicEnergyZeroScoreIsoSeconds", CATA_ENERGY_ZERO_SCORE);
            thresholds.put("catastrophicMedianFullDarkY", CATA_MEDIAN_FULL_DARK_Y);
            thresholds.put("catastrophicMedianZeroDarkY", CATA_MEDIAN_ZERO_DARK_Y);
            thresholds.put("catastrophicQ95FullDarkY", CATA_Q95_FULL_DARK_Y);
            thresholds.put("catastrophicQ95ZeroDarkY", CATA_Q95_ZERO_DARK_Y);
            thresholds.put("catastrophicQ99FullDarkY", CATA_Q99_FULL_DARK_Y);
            thresholds.put("catastrophicQ99ZeroDarkY", CATA_Q99_ZERO_DARK_Y);
            thresholds.put("landscapeBright192RampLow", LANDSCAPE_BRIGHT192_LOW);
            thresholds.put("landscapeBright192RampHigh", LANDSCAPE_BRIGHT192_HIGH);
            thresholds.put("landscapeTopBrightShareRampLow", LANDSCAPE_TOP_BRIGHT_SHARE_LOW);
            thresholds.put("landscapeTopBrightShareRampHigh", LANDSCAPE_TOP_BRIGHT_SHARE_HIGH);
            thresholds.put("landscapeTopMedianHeterogeneityRampLow", LANDSCAPE_TOP_MEDIAN_HETERO_LOW);
            thresholds.put("landscapeTopMedianHeterogeneityRampHigh", LANDSCAPE_TOP_MEDIAN_HETERO_HIGH);
            thresholds.put("spatialDark64RampLow", SPATIAL_DARK64_LOW);
            thresholds.put("spatialDark64RampHigh", SPATIAL_DARK64_HIGH);
            thresholds.put("spatialQ95RampLowY", SPATIAL_Q95_LOW_Y);
            thresholds.put("spatialQ95RampHighY", SPATIAL_Q95_HIGH_Y);
            thresholds.put("spatialBright192RampLow", SPATIAL_BRIGHT192_LOW);
            thresholds.put("spatialBright192RampHigh", SPATIAL_BRIGHT192_HIGH);
            thresholds.put("spatialAxisSpreadRampLow", SPATIAL_AXIS_SPREAD_LOW);
            thresholds.put("spatialAxisSpreadRampHigh", SPATIAL_AXIS_SPREAD_HIGH);
            thresholds.put("spatialLowRegionRatioFull", SPATIAL_LOW_REGION_RATIO_FULL);
            thresholds.put("spatialLowRegionRatioZero", SPATIAL_LOW_REGION_RATIO_ZERO);
            thresholds.put("wouldApplyScore", APPLY_SCORE);
            thresholds.put("recommendationRampLow", EV_RAMP_LOW);
            thresholds.put("recommendationRampHigh", EV_RAMP_HIGH);
            thresholds.put("maxRecommendedExposureCorrectionEv", MAX_RECOMMENDED_EV);
            out.put("provisionalThresholds", thresholds);

            out.put("wouldApply", wouldApply);
            out.put("recommendedExposureCorrectionEv", recommendedEv);
            out.put("maximumRecommendedExposureCorrectionEv", MAX_RECOMMENDED_EV);
            out.put("feedbackEnabled", true);

            boolean catastrophicDominant = catastrophicAeStarvationScore >= backlightStarvationScore
                    && catastrophicAeStarvationScore > 0.0;
            boolean spatialDominant = protectedSpatialBacklightStarvationScore >= backlightStarvationScore
                    && protectedSpatialBacklightStarvationScore > 0.0;
            boolean landscapeSuppressedCandidate = landscapeHighContrastProtectionScore > 0.0
                    && Math.max(centerProtectedRelativeScore, rawSpatialBacklightStarvationScore) >= APPLY_SCORE
                    && Math.max(protectedRelativeBacklightStarvationScore,
                            protectedSpatialBacklightStarvationScore) < APPLY_SCORE;
            boolean centerSuppressedCandidate = centerBodyProtectionScore > 0.0
                    && rawRelativeBacklightStarvationScore >= APPLY_SCORE
                    && centerProtectedRelativeScore < APPLY_SCORE;

            if (catastrophicDominant && wouldApply) {
                out.put("reason", "catastrophic_ae_starvation_candidate");
            } else if (spatialDominant && wouldApply) {
                out.put("reason", "spatial_foreground_starvation_candidate");
            } else if (landscapeSuppressedCandidate) {
                out.put("reason", "spatial_landscape_protected_high_contrast_control");
            } else if (centerSuppressedCandidate && !wouldApply) {
                out.put("reason", "center_body_protected_high_contrast_control");
            } else if (!wouldApply && relativeStructureScore <= 0.0
                    && catastrophicAeStarvationScore <= 0.0
                    && rawSpatialBacklightStarvationScore <= 0.0) {
                out.put("reason", "no_backlight_starvation_structure");
            } else if (!wouldApply && energyStarvationScore <= 0.0
                    && rawSpatialBacklightStarvationScore <= 0.0
                    && catastrophicAeStarvationScore <= 0.0) {
                out.put("reason", "structure_present_but_no_starvation_branch");
            } else if (!wouldApply) {
                out.put("reason", "weak_backlight_starvation_candidate");
            } else if (brightScore <= 0.0) {
                out.put("reason", "relative_backlight_starvation_candidate_low_absolute_bright");
            } else {
                out.put("reason", "backlight_starvation_candidate");
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    /**
     * Evaluate the exact frozen LUMA2.4 scorer against the latest preview-Y frame at
     * exposure-decision time. This method does not mutate Photon exposure by itself.
     */
    public static synchronized LiveFeedbackDecision evaluateLiveFeedback(
            double previewEnergyIsoSeconds, int cameraRotationDegrees, boolean eligible,
            String eligibilityReason) {
        JSONObject score = new JSONObject();
        boolean valid = false;
        boolean wouldApply = false;
        double recommendedEv = 0.0;
        double appliedEv = 0.0;
        String reason = "missing_preview_luma";
        try {
            JSONObject subject = M9SubjectMotionAnalyzer.snapshotJson(cameraRotationDegrees);
            JSONObject luma = subject.optJSONObject("previewLuma");
            long lumaFrames = luma != null ? luma.optLong("framesAnalyzed", 0L) : 0L;
            JSONObject spatial = luma != null ? luma.optJSONObject("spatial3x3") : null;
            boolean spatialReady = spatial != null && spatial.optBoolean("valid", false);

            if (lumaFrames < 3L || luma == null || !spatialReady) {
                reason = "insufficient_preview_luma_history";
            } else {
                JSONObject preview = new JSONObject();
                preview.put("exposureEnergyIsoSeconds", previewEnergyIsoSeconds);
                JSONObject photon = new JSONObject();
                photon.put("preview", preview);
                JSONObject syntheticRoot = new JSONObject();
                syntheticRoot.put("photonExposureDecision", photon);
                syntheticRoot.put("subjectMotion", subject);
                score = snapshotJson(syntheticRoot);
                score.remove("appliedExposureCorrectionEv");
                score.remove("feedbackEnabled");

                valid = score.optBoolean("valid", false);
                wouldApply = score.optBoolean("wouldApply", false);
                recommendedEv = clamp(score.optDouble("recommendedExposureCorrectionEv", 0.0),
                        0.0, MAX_RECOMMENDED_EV);
                String scoreReason = score.optString("reason", "luma2p4_no_reason");

                if (!eligible) {
                    appliedEv = 0.0;
                    reason = eligibilityReason != null && !eligibilityReason.isEmpty()
                            ? eligibilityReason : "feedback_not_eligible";
                } else if (!valid) {
                    appliedEv = 0.0;
                    reason = "classifier_invalid";
                } else if (!wouldApply) {
                    appliedEv = 0.0;
                    reason = scoreReason;
                } else {
                    appliedEv = recommendedEv;
                    reason = scoreReason;
                }
            }
        } catch (Exception ignored) {
            valid = false;
            wouldApply = false;
            recommendedEv = 0.0;
            appliedEv = 0.0;
            reason = "live_feedback_exception";
        }
        return new LiveFeedbackDecision(valid, wouldApply, recommendedEv, appliedEv, reason, score);
    }

    /** Record the exact target-energy mutation handed to the existing allocator. */
    public static synchronized void recordLiveFeedbackApplication(
            LiveFeedbackDecision decision,
            double previewEnergyIsoSeconds,
            int cameraRotationDegrees,
            long preTargetExposureNs,
            int preTargetIsoNormalized,
            long postTargetExposureNs,
            int postTargetIsoNormalized) {
        JSONObject o = new JSONObject();
        try {
            double preEnergyNsIso = (double) preTargetExposureNs * Math.max(1, preTargetIsoNormalized);
            double postEnergyNsIso = (double) postTargetExposureNs * Math.max(1, postTargetIsoNormalized);
            double factor = preEnergyNsIso > 0.0 ? postEnergyNsIso / preEnergyNsIso : 1.0;
            o.put("schema", "m9cam.backlightfeedback.v1");
            o.put("enabled", true);
            o.put("classifier", "LUMA2.4-SPATIAL2");
            o.put("previewExposureEnergyIsoSeconds", previewEnergyIsoSeconds);
            o.put("cameraRotationDegrees", cameraRotationDegrees);
            o.put("valid", decision != null && decision.valid);
            o.put("wouldApply", decision != null && decision.wouldApply);
            o.put("recommendedExposureCorrectionEv", decision != null ? decision.recommendedEv : 0.0);
            o.put("appliedExposureCorrectionEv", decision != null ? decision.appliedEv : 0.0);
            o.put("requestedExposureFactor", decision != null ? Math.pow(2.0, decision.appliedEv) : 1.0);
            o.put("reason", decision != null ? decision.reason : "missing_live_decision");
            o.put("preCorrectionTargetExposureNs", preTargetExposureNs);
            o.put("preCorrectionTargetIsoNormalized", preTargetIsoNormalized);
            o.put("preCorrectionTargetEnergyNsIso", preEnergyNsIso);
            o.put("postCorrectionTargetExposureNs", postTargetExposureNs);
            o.put("postCorrectionTargetIsoNormalized", postTargetIsoNormalized);
            o.put("postCorrectionTargetEnergyNsIso", postEnergyNsIso);
            o.put("actualTargetEnergyGainRatio", factor);
            o.put("actualTargetEnergyGainEv", factor > 0.0 ? Math.log(factor) / Math.log(2.0) : 0.0);
            if (decision != null && decision.classifierSnapshot != null) {
                o.put("classifierAtDecision", new JSONObject(decision.classifierSnapshot.toString()));
            }
        } catch (Exception ignored) {
        }
        lastLiveFeedback = o;
    }

    public static synchronized JSONObject feedbackSnapshotJson() {
        try { return new JSONObject(lastLiveFeedback.toString()); }
        catch (Exception e) { return new JSONObject(); }
    }

    private static double clamp(double x, double lo, double hi) {
        return Math.max(lo, Math.min(hi, x));
    }

    private static SpatialFeatures spatialFeatures(JSONObject spatial, double q95) {
        SpatialFeatures out = new SpatialFeatures();
        if (spatial == null || !spatial.optBoolean("valid", false) || !finite(q95) || q95 <= 0.0) {
            return out;
        }
        try {
            JSONObject h = spatial.optJSONObject("displayHorizontalThirds");
            JSONObject v = spatial.optJSONObject("displayVerticalThirds");
            JSONObject tiles = spatial.optJSONObject("tiles");
            if (h == null || v == null || tiles == null) return out;

            double top = regionMedian(h, "top");
            double middle = regionMedian(h, "middle");
            double bottom = regionMedian(h, "bottom");
            double left = regionMedian(v, "left");
            double center = regionMedian(v, "center");
            double right = regionMedian(v, "right");
            if (!allFinite(top, middle, bottom, left, center, right)) return out;

            double horizontalRange = range3(top, middle, bottom);
            double verticalRange = range3(left, center, right);
            out.axisMedianSpreadY = Math.max(horizontalRange, verticalRange);
            out.normalizedAxisMedianSpread = out.axisMedianSpreadY / Math.max(1.0, q95);
            out.lowRegionMedianY = Math.min(Math.min(Math.min(top, middle), bottom),
                    Math.min(Math.min(left, center), right));
            out.lowRegionMedianOverQ95 = out.lowRegionMedianY / Math.max(1.0, q95);

            String[] names = new String[] {
                    "topLeft", "topCenter", "topRight",
                    "middleLeft", "middleCenter", "middleRight",
                    "bottomLeft", "bottomCenter", "bottomRight"
            };
            double totalBright = 0.0;
            double topBright = 0.0;
            for (int i = 0; i < names.length; i++) {
                JSONObject tile = tiles.optJSONObject(names[i]);
                if (tile == null) return new SpatialFeatures();
                double f = tile.optDouble("brightFractionGE192", Double.NaN);
                if (!finite(f)) return new SpatialFeatures();
                totalBright += Math.max(0.0, f);
                if (i < 3) topBright += Math.max(0.0, f);
            }
            out.topBrightShare = totalBright > 1e-12 ? clamp01(topBright / totalBright) : 0.0;

            double tl = regionMedian(tiles, "topLeft");
            double tc = regionMedian(tiles, "topCenter");
            double tr = regionMedian(tiles, "topRight");
            if (!allFinite(tl, tc, tr)) return new SpatialFeatures();
            out.topMedianHeterogeneity = range3(tl, tc, tr) / Math.max(1.0, q95);
            out.valid = true;
            return out;
        } catch (Exception ignored) {
            return new SpatialFeatures();
        }
    }

    private static double regionMedian(JSONObject parent, String key) {
        JSONObject o = parent != null ? parent.optJSONObject(key) : null;
        return o != null ? o.optDouble("median", Double.NaN) : Double.NaN;
    }

    private static double range3(double a, double b, double c) {
        double hi = Math.max(a, Math.max(b, c));
        double lo = Math.min(a, Math.min(b, c));
        return hi - lo;
    }

    private static boolean allFinite(double... values) {
        for (double v : values) if (!finite(v)) return false;
        return true;
    }

    private static final class SpatialFeatures {
        boolean valid = false;
        double axisMedianSpreadY = 0.0;
        double normalizedAxisMedianSpread = 0.0;
        double lowRegionMedianY = 0.0;
        double lowRegionMedianOverQ95 = 0.0;
        double topBrightShare = 0.0;
        double topMedianHeterogeneity = 0.0;
    }

    private static boolean finite(double v) {
        return !Double.isNaN(v) && !Double.isInfinite(v);
    }

    private static double smoothstep(double value, double low, double high) {
        if (high <= low) return value >= high ? 1.0 : 0.0;
        double t = clamp01((value - low) / (high - low));
        return t * t * (3.0 - 2.0 * t);
    }

    private static double clamp01(double v) {
        return Math.max(0.0, Math.min(1.0, v));
    }
}
