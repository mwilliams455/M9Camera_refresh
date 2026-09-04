#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m10r-mfmtest1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('M10RMFMTEST1A missing expected file: ' + rel)
    return p.read_text()

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

analyzer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java'
iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'

expected = "versionName '1.60-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a'"
if expected not in read(gradle_rel):
    raise SystemExit('M10RMFMTEST1A expected CURRENTFRAMECEILING1A 1.60 baseline missing')

frozen_rels = [
    renderer_rel,
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintTie1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CurrentFrameCeiling1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

a = read(analyzer_rel)
if 'm10rAeGrid16x22' not in a:
    if 'import org.json.JSONObject;\n' not in a:
        raise SystemExit('M10RMFMTEST1A analyzer JSONObject import anchor missing')
    a = a.replace('import org.json.JSONObject;\n',
                  'import org.json.JSONObject;\nimport org.json.JSONArray;\n', 1)
    snap_anchor = '            o.put("spatial3x3", spatial3x3SnapshotJson(latestLumaFrame, cameraRotationDegrees));\n'
    snap_repl = snap_anchor + '            o.put("m10rAeGrid16x22", m10rAeGrid16x22SnapshotJson(latestLumaFrame, cameraRotationDegrees));\n'
    if snap_anchor not in a:
        raise SystemExit('M10RMFMTEST1A analyzer snapshot anchor missing')
    a = a.replace(snap_anchor, snap_repl, 1)

    method_anchor = '    private static JSONObject spatial3x3SnapshotJson(byte[] sensorFrame, int cameraRotationDegrees) {\n'
    grid_method = r'''    private static JSONObject m10rAeGrid16x22SnapshotJson(byte[] sensorFrame, int cameraRotationDegrees) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", "m9cam.previewluma.m10rgrid.v1a");
            out.put("source", "xiaomi_preview_y_downsample_not_leica_prepro_statistics");
            out.put("rowsCount", 16);
            out.put("columnsCount", 22);
            if (sensorFrame == null || sensorFrame.length != W * H) {
                out.put("valid", false);
                out.put("reason", "latest_luma_frame_missing");
                return out;
            }
            int rotation = normalizeRotation(cameraRotationDegrees);
            OrientedLuma oriented = orientForDisplay(sensorFrame, rotation);
            JSONArray rows = new JSONArray();
            for (int gy = 0; gy < 16; gy++) {
                int y0 = (gy * oriented.height) / 16;
                int y1 = ((gy + 1) * oriented.height) / 16;
                if (y1 <= y0) y1 = Math.min(oriented.height, y0 + 1);
                JSONArray row = new JSONArray();
                for (int gx = 0; gx < 22; gx++) {
                    int x0 = (gx * oriented.width) / 22;
                    int x1 = ((gx + 1) * oriented.width) / 22;
                    if (x1 <= x0) x1 = Math.min(oriented.width, x0 + 1);
                    long sum = 0L;
                    int n = 0;
                    for (int y = y0; y < y1; y++) {
                        int base = y * oriented.width;
                        for (int x = x0; x < x1; x++) {
                            sum += oriented.data[base + x] & 0xff;
                            n++;
                        }
                    }
                    row.put(n > 0 ? (sum / (double)n) : 0.0);
                }
                rows.put(row);
            }
            out.put("valid", true);
            out.put("rotationAppliedDegrees", rotation);
            out.put("displayWidth", oriented.width);
            out.put("displayHeight", oriented.height);
            out.put("cellValue", "arithmetic_mean_preview_y_0_255");
            out.put("rows", rows);
            out.put("reason", "m10r_geometry_proxy_ready");
        } catch (Throwable t) {
            try {
                out.put("valid", false);
                out.put("reason", "m10r_grid_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

'''
    if method_anchor not in a:
        raise SystemExit('M10RMFMTEST1A spatial3x3 method anchor missing')
    a = a.replace(method_anchor, grid_method + method_anchor, 1)
    write(analyzer_rel, a)

mfm_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9M10rMfmTest1A.java'
mfm_p = root / mfm_rel
if mfm_p.exists():
    raise SystemExit('M10RMFMTEST1A target class already exists; refuse ambiguous reapply')

mfm = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;

public final class M9M10rMfmTest1A {
    public static final String SCHEMA = "m9cam.m10r.mfmtest.v1a";
    private static final int GRID_R = 16;
    private static final int GRID_C = 22;
    private static final int REG_R = 4;
    private static final int REG_C = 6;
    private static final double DEAD_BAND_EV = 0.08;
    private static final double MAX_POSITIVE_EV = 0.75;
    private static final double MAX_NEGATIVE_EV = 0.50;

    // Exact recovered M10-R Integral quantity mask at 0x4001349c.
    // This spatial mask is reused against Xiaomi preview Y only as a cross-generation
    // geometry experiment. It does not make the Xiaomi statistics numerically Leica CA9 Y.
    private static final int[] INTEGRAL_MASK = new int[] {
         0, 0, 0, 0,10,10,10,10,10,10,10,10,10,10,10,10,10,10, 0, 0, 0, 0,
         0, 0, 0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10, 0, 0, 0,
         0, 0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10, 0, 0,
         0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10, 0,
        10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10,
        10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10,
        10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10,
         0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10, 0,
         0, 0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10, 0, 0,
         0, 0, 0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10, 0, 0, 0,
         0, 0, 0, 0,10,10,10,10,10,10,10,10,10,10,10,10,10,10, 0, 0, 0, 0
    };

    private static JSONObject lastLive = new JSONObject();

    private M9M10rMfmTest1A() {}

    public static synchronized M9BacklightDiagnostic.LiveFeedbackDecision evaluateLiveFeedback(
            double previewEnergyIsoSeconds, int cameraRotationDegrees, boolean eligible,
            String eligibilityReason) {
        JSONObject out = contract();
        boolean valid = false;
        boolean wouldApply = false;
        double recommendedEv = 0.0;
        double appliedEv = 0.0;
        String reason = "m10r_grid_missing";
        try {
            JSONObject subject = M9SubjectMotionAnalyzer.snapshotJson(cameraRotationDegrees);
            JSONObject luma = subject.optJSONObject("previewLuma");
            long frames = luma != null ? luma.optLong("framesAnalyzed", 0L) : 0L;
            JSONObject grid = luma != null ? luma.optJSONObject("m10rAeGrid16x22") : null;

            M9BacklightDiagnostic.LiveFeedbackDecision legacy =
                    M9BacklightDiagnostic.evaluateLiveFeedback(
                            previewEnergyIsoSeconds, cameraRotationDegrees, false,
                            "m10r_mfmtest_counterfactual_only");

            out.put("previewExposureEnergyIsoSeconds", previewEnergyIsoSeconds);
            out.put("cameraRotationDegrees", cameraRotationDegrees);
            out.put("previewLumaFrames", frames);
            out.put("legacyLuma24Valid", legacy.valid);
            out.put("legacyLuma24WouldApply", legacy.wouldApply);
            out.put("legacyLuma24RecommendedEv", legacy.recommendedEv);

            if (frames < 3L || grid == null || !grid.optBoolean("valid", false)) {
                reason = "insufficient_m10r_grid_history";
            } else {
                double[] cell = readGrid(grid);
                if (cell == null) {
                    reason = "m10r_grid_shape_invalid";
                } else {
                    double integralY = weightedMean(cell, INTEGRAL_MASK);
                    double[] regions = regions4x6(cell);
                    double[] sorted = regions.clone();
                    Arrays.sort(sorted);
                    double regionalMedianY = 0.5 * (sorted[11] + sorted[12]);
                    double regionalTrimmedMeanY = meanRange(sorted, 4, 20);
                    double regionalLowY = meanRange(sorted, 0, 6);
                    double regionalHighY = meanRange(sorted, 18, 24);
                    double sceneSpreadEv = log2(safe(regionalHighY) / safe(regionalLowY));

                    double center8Y = regionRectMean(regions, 1, 3, 1, 5);
                    double lower12Y = regionRectMean(regions, 2, 4, 0, 6);
                    double upper6Y = regionRectMean(regions, 0, 1, 0, 6);
                    double edge16Y = regionEdgeMean(regions, true);
                    double inner8Y = regionEdgeMean(regions, false);

                    double integralVsMedianEv = log2(safe(integralY) / safe(regionalMedianY));
                    double integralVsCenterEv = log2(safe(integralY) / safe(center8Y));
                    double integralVsLowerEv = log2(safe(integralY) / safe(lower12Y));
                    double brightTailEv = log2(safe(regionalHighY) / safe(regionalMedianY));
                    double edgeVsInnerEv = log2(safe(edge16Y) / safe(inner8Y));
                    double upperVsLowerEv = log2(safe(upper6Y) / safe(lower12Y));
                    double centerOverIntegralEv = log2(safe(center8Y) / safe(integralY));
                    double innerVsEdgeEv = log2(safe(inner8Y) / safe(edge16Y));

                    int brightRegions = 0;
                    int darkRegions = 0;
                    double brightThreshold = regionalMedianY * Math.pow(2.0, 0.50);
                    double darkThreshold = regionalMedianY / Math.pow(2.0, 0.50);
                    for (double v : regions) {
                        if (v >= brightThreshold) brightRegions++;
                        if (v <= darkThreshold) darkRegions++;
                    }
                    double brightRegionFraction = brightRegions / 24.0;
                    double darkRegionFraction = darkRegions / 24.0;

                    // M10-R-style research proxy: derive signed scene pressure from the exact
                    // Integral weighting plus the proven 4x6 regional topology. We intentionally
                    // do NOT claim numerical parity with the unresolved CA9 13-feature generator.
                    double rawPositiveEv = Math.max(0.0,
                            0.55 * integralVsMedianEv
                            + 0.25 * integralVsCenterEv
                            + 0.20 * integralVsLowerEv);
                    double edgeBacklightGeometry = smoothstep(edgeVsInnerEv, 0.05, 0.65);
                    double upperBacklightGeometry = smoothstep(upperVsLowerEv, 0.15, 1.00);
                    double positiveGeometryConfidence = Math.max(
                            edgeBacklightGeometry, upperBacklightGeometry);
                    double positiveConfidence = smoothstep(sceneSpreadEv, 0.70, 2.20)
                            * smoothstep(brightRegionFraction, 0.08, 0.30)
                            * positiveGeometryConfidence;
                    double positiveCandidateEv = rawPositiveEv * positiveConfidence;

                    // Negative pressure is intentionally stricter and requires a broad bright
                    // inner/center relationship; this avoids interpreting one legitimate black/
                    // dark foreground object as a reason to darken the whole scene.
                    double negativeGeometryConfidence = Math.max(
                            smoothstep(innerVsEdgeEv, 0.05, 0.65),
                            smoothstep(centerOverIntegralEv, 0.15, 0.65));
                    double negativeConfidence = smoothstep(sceneSpreadEv, 0.45, 1.60)
                            * negativeGeometryConfidence;
                    double negativeCandidateEv = -0.70
                            * Math.max(0.0, centerOverIntegralEv - 0.10)
                            * negativeConfidence;

                    double rawBlendEv = positiveCandidateEv + negativeCandidateEv;
                    double candidateEv = clamp(rawBlendEv, -MAX_NEGATIVE_EV, MAX_POSITIVE_EV);
                    if (Math.abs(candidateEv) < DEAD_BAND_EV) candidateEv = 0.0;

                    valid = finite(candidateEv) && finite(integralY) && finite(regionalMedianY);
                    recommendedEv = valid ? candidateEv : 0.0;
                    wouldApply = valid && Math.abs(recommendedEv) >= DEAD_BAND_EV;

                    if (!eligible) {
                        appliedEv = 0.0;
                        reason = eligibilityReason != null && !eligibilityReason.isEmpty()
                                ? eligibilityReason : "m10r_mfmtest_not_eligible";
                    } else if (!valid) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_invalid";
                    } else if (!wouldApply) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_neutral_deadband";
                    } else {
                        appliedEv = recommendedEv;
                        reason = recommendedEv > 0.0
                                ? "m10r_multifield_positive_capture_assist"
                                : "m10r_multifield_negative_capture_moderation";
                    }

                    out.put("valid", valid);
                    out.put("wouldApply", wouldApply);
                    out.put("recommendedExposureCorrectionEv", recommendedEv);
                    out.put("appliedExposureCorrectionEv", appliedEv);
                    out.put("reason", reason);
                    out.put("integralY", integralY);
                    out.put("regionalMedianY", regionalMedianY);
                    out.put("regionalTrimmedMeanY", regionalTrimmedMeanY);
                    out.put("regionalLowQuarterY", regionalLowY);
                    out.put("regionalHighQuarterY", regionalHighY);
                    out.put("sceneSpreadEv", sceneSpreadEv);
                    out.put("center8Y", center8Y);
                    out.put("lower12Y", lower12Y);
                    out.put("upper6Y", upper6Y);
                    out.put("edge16Y", edge16Y);
                    out.put("inner8Y", inner8Y);
                    out.put("integralVsMedianEv", integralVsMedianEv);
                    out.put("integralVsCenterEv", integralVsCenterEv);
                    out.put("integralVsLowerEv", integralVsLowerEv);
                    out.put("brightTailEv", brightTailEv);
                    out.put("edgeVsInnerEv", edgeVsInnerEv);
                    out.put("upperVsLowerEv", upperVsLowerEv);
                    out.put("centerOverIntegralEv", centerOverIntegralEv);
                    out.put("innerVsEdgeEv", innerVsEdgeEv);
                    out.put("positiveCandidateEv", positiveCandidateEv);
                    out.put("negativeCandidateEv", negativeCandidateEv);
                    out.put("rawBlendEv", rawBlendEv);
                    out.put("brightRegionCount", brightRegions);
                    out.put("darkRegionCount", darkRegions);
                    out.put("brightRegionFraction", brightRegionFraction);
                    out.put("darkRegionFraction", darkRegionFraction);
                    out.put("positiveGeometryConfidence", positiveGeometryConfidence);
                    out.put("positiveConfidence", positiveConfidence);
                    out.put("negativeGeometryConfidence", negativeGeometryConfidence);
                    out.put("negativeConfidence", negativeConfidence);
                    out.put("regions4x6", toJson(regions));
                }
            }

            if (!out.has("valid")) out.put("valid", valid);
            if (!out.has("wouldApply")) out.put("wouldApply", wouldApply);
            if (!out.has("recommendedExposureCorrectionEv"))
                out.put("recommendedExposureCorrectionEv", recommendedEv);
            if (!out.has("appliedExposureCorrectionEv"))
                out.put("appliedExposureCorrectionEv", appliedEv);
            if (!out.has("reason")) out.put("reason", reason);
        } catch (Throwable t) {
            valid = false;
            wouldApply = false;
            recommendedEv = 0.0;
            appliedEv = 0.0;
            reason = "m10r_mfmtest_exception";
            try {
                out.put("valid", false);
                out.put("wouldApply", false);
                out.put("recommendedExposureCorrectionEv", 0.0);
                out.put("appliedExposureCorrectionEv", 0.0);
                out.put("reason", reason);
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }

        lastLive = cloneJson(out);
        return new M9BacklightDiagnostic.LiveFeedbackDecision(
                valid, wouldApply, recommendedEv, appliedEv, reason, cloneJson(out));
    }

    public static synchronized JSONObject snapshotJson() {
        return cloneJson(lastLive);
    }

    private static JSONObject contract() {
        JSONObject o = new JSONObject();
        try {
            o.put("schema", SCHEMA);
            o.put("mode", "live_bounded_m10r_architecture_proxy");
            o.put("sourceDomain", "xiaomi_preview_y_not_leica_prepro_aeawb_uint32");
            o.put("m10rNumericalParity", false);
            o.put("m10rArchitectureBorrowed", true);
            o.put("recoveredIntegralMask", "exact_0x4001349c_sum14160");
            o.put("recoveredMfmRegionalStructure", "4x6_24_regions");
            o.put("recoveredMfmBaseMask", "all_100_not_needed_for_region_proxy");
            o.put("exact13FeatureGeneratorApplied", false);
            o.put("leicaReference524UsedForLiveCorrection", false);
            o.put("leicaBvOffset011AUsedForLiveCorrection", false);
            o.put("reasonForNoNumericParity",
                    "prepro_aeawb_plane_layout_and_exact_ca9_feature_semantics_not_yet_closed");
            o.put("positiveLimitEv", MAX_POSITIVE_EV);
            o.put("negativeLimitEv", -MAX_NEGATIVE_EV);
            o.put("deadBandEv", DEAD_BAND_EV);
            o.put("boundsOrigin", "m9cam_research_safety_not_m10r_firmware_constant");
            o.put("legacyLuma24Role", "counterfactual_only_not_live_decision_source");
            o.put("tc20IntentNormalization", "unchanged_in_this_test_build");
        } catch (Exception ignored) {}
        return o;
    }

    private static double[] readGrid(JSONObject grid) {
        JSONArray rows = grid.optJSONArray("rows");
        if (rows == null || rows.length() != GRID_R) return null;
        double[] out = new double[GRID_R * GRID_C];
        for (int r = 0; r < GRID_R; r++) {
            JSONArray row = rows.optJSONArray(r);
            if (row == null || row.length() != GRID_C) return null;
            for (int c = 0; c < GRID_C; c++) {
                double v = row.optDouble(c, Double.NaN);
                if (!finite(v)) return null;
                out[r * GRID_C + c] = Math.max(0.0, v);
            }
        }
        return out;
    }

    private static double weightedMean(double[] v, int[] w) {
        double s = 0.0, sw = 0.0;
        for (int i = 0; i < v.length && i < w.length; i++) {
            if (w[i] <= 0) continue;
            s += v[i] * w[i];
            sw += w[i];
        }
        return sw > 0.0 ? s / sw : 0.0;
    }

    private static double[] regions4x6(double[] cell) {
        double[] out = new double[24];
        for (int rr = 0; rr < REG_R; rr++) {
            int r0 = rr * GRID_R / REG_R;
            int r1 = (rr + 1) * GRID_R / REG_R;
            for (int cc = 0; cc < REG_C; cc++) {
                int c0 = cc * GRID_C / REG_C;
                int c1 = (cc + 1) * GRID_C / REG_C;
                double s = 0.0;
                int n = 0;
                for (int r = r0; r < r1; r++) {
                    for (int c = c0; c < c1; c++) {
                        s += cell[r * GRID_C + c];
                        n++;
                    }
                }
                out[rr * REG_C + cc] = n > 0 ? s / n : 0.0;
            }
        }
        return out;
    }

    private static double regionRectMean(double[] r, int r0, int r1, int c0, int c1) {
        double s = 0.0;
        int n = 0;
        for (int y = r0; y < r1; y++) {
            for (int x = c0; x < c1; x++) {
                s += r[y * REG_C + x];
                n++;
            }
        }
        return n > 0 ? s / n : 0.0;
    }

    private static double regionEdgeMean(double[] r, boolean edge) {
        double s = 0.0;
        int n = 0;
        for (int y = 0; y < REG_R; y++) {
            for (int x = 0; x < REG_C; x++) {
                boolean isEdge = y == 0 || y == REG_R - 1 || x == 0 || x == REG_C - 1;
                if (isEdge == edge) {
                    s += r[y * REG_C + x];
                    n++;
                }
            }
        }
        return n > 0 ? s / n : 0.0;
    }

    private static double meanRange(double[] v, int from, int to) {
        double s = 0.0;
        int n = 0;
        for (int i = Math.max(0, from); i < Math.min(v.length, to); i++) {
            s += v[i];
            n++;
        }
        return n > 0 ? s / n : 0.0;
    }

    private static JSONArray toJson(double[] v) {
        JSONArray a = new JSONArray();
        for (double x : v) a.put(x);
        return a;
    }

    private static JSONObject cloneJson(JSONObject o) {
        try { return new JSONObject(o.toString()); }
        catch (Exception e) { return o; }
    }

    private static double smoothstep(double x, double lo, double hi) {
        if (!finite(x)) return 0.0;
        if (hi <= lo) return x >= hi ? 1.0 : 0.0;
        double t = clamp((x - lo) / (hi - lo), 0.0, 1.0);
        return t * t * (3.0 - 2.0 * t);
    }

    private static double safe(double v) { return Math.max(v, 1.0e-6); }
    private static double log2(double v) { return Math.log(Math.max(v, 1.0e-12)) / Math.log(2.0); }
    private static double clamp(double v, double lo, double hi) { return Math.max(lo, Math.min(hi, v)); }
    private static boolean finite(double v) { return !Double.isNaN(v) && !Double.isInfinite(v); }
}
'''
write(mfm_rel, mfm)

i = read(iso_rel)
import_anchor = 'import com.particlesdevs.photoncamera.m9.M9BacklightDiagnostic;\n'
if 'import com.particlesdevs.photoncamera.m9.M9M10rMfmTest1A;\n' not in i:
    if import_anchor not in i:
        raise SystemExit('M10RMFMTEST1A IsoExpoSelector import anchor missing')
    i = i.replace(import_anchor,
                  import_anchor + 'import com.particlesdevs.photoncamera.m9.M9M10rMfmTest1A;\n', 1)

old_call = '''            M9BacklightDiagnostic.LiveFeedbackDecision m9Feedback =
                    M9BacklightDiagnostic.evaluateLiveFeedback(
                            m9PreviewEnergyIsoSeconds,
                            m9FeedbackRotationDegrees,
                            m9FeedbackEligible,
                            m9FeedbackEligibilityReason);
'''
new_call = '''            M9BacklightDiagnostic.LiveFeedbackDecision m9Feedback =
                    M9M10rMfmTest1A.evaluateLiveFeedback(
                            m9PreviewEnergyIsoSeconds,
                            m9FeedbackRotationDegrees,
                            m9FeedbackEligible,
                            m9FeedbackEligibilityReason);
'''
if old_call not in i:
    raise SystemExit('M10RMFMTEST1A live FB1 decision anchor missing')
i = i.replace(old_call, new_call, 1)

# M10RMFMTEST1A is deliberately signed: unlike legacy FB1, a bounded negative
# recommendation is allowed to reduce the Photon target. ExpoCompensateLower already
# implements signed compensation through k=1/2^EV, so only the legacy positive-only
# gate needs widening. Manual EV/ISO/shutter and tripod bypass remain authoritative.
old_apply = '            if (m9Feedback.appliedEv > 0.0) {\n'
new_apply = '            if (Math.abs(m9Feedback.appliedEv) > 1.0e-9) {\n'
if old_apply not in i:
    raise SystemExit('M10RMFMTEST1A signed live-apply gate anchor missing')
i = i.replace(old_apply, new_apply, 1)
write(iso_rel, i)

m = read(meta_rel)
anchor = '''            root.put("m9CurrentFrameCeiling", M9CurrentFrameCeiling1A.evaluate(root));
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
repl = '''            root.put("m9CurrentFrameCeiling", M9CurrentFrameCeiling1A.evaluate(root));
            root.put("m9M10rMfmTest", M9M10rMfmTest1A.snapshotJson());
            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));
'''
if anchor not in m:
    raise SystemExit('M10RMFMTEST1A metadata anchor missing')
write(meta_rel, m.replace(anchor, repl, 1))

back = read(back_rel)
marker = 'constraintnearest1aconstrainttie1acurrentframeceiling1ascenefingerprint1b'
marker2 = 'constraintnearest1aconstrainttie1acurrentframeceiling1am10rmfmtest1ascenefingerprint1b'
if marker not in back:
    raise SystemExit('M10RMFMTEST1A backlight marker anchor missing')
back = back.replace(marker, marker2, 1)
if '1.60-' not in back:
    raise SystemExit('M10RMFMTEST1A backlight version anchor missing')
write(back_rel, back.replace('1.60-', '1.61-', 1))

g = read(gradle_rel)
new_version = "versionName '1.61-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a-m10rmfm1a'"
write(gradle_rel, g.replace(expected, new_version, 1))

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit('M10RMFMTEST1A frozen photographic seam changed unexpectedly: ' + rel)

print('M9Cam M10RMFMTEST1A live bounded test meter applied')
print(' - Xiaomi preview-Y now exposes display-oriented 16x22 grid diagnostics')
print(' - exact recovered M10-R Integral 16x22 mask and 4x6/24-region architecture used')
print(' - exact M10-R 13-feature numerical parity is NOT claimed or imported')
print(' - replaces only FB1 live decision source; manual EV/ISO/shutter/tripod bypass remains')
print(' - bounded research correction: -0.50 .. +0.75 EV with 0.08 EV deadband')
print(' - TC20, renderer, Cobalt, curve02, SAT3, BT601, JPEG95 and DNG path unchanged')
