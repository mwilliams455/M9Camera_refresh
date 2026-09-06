#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-chromaexposure1b-localneutral1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('CHROMAEXPOSURE1B missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ChromaExposure1AController.java'
renderer = read(renderer_rel)
helper_before = read(helper_rel)

if 'm9cam.chromaexposure.v1a.greenaxis1a' not in helper_before:
    raise SystemExit('CHROMAEXPOSURE1B requires applied GREENAXIS1A helper baseline')
if 'chromaExposure1A' not in renderer:
    raise SystemExit('CHROMAEXPOSURE1B requires GREENAXIS1A renderer integration')

# 1B is detector/decision refinement only. The established frame-level negative-Cr seam remains
# the sole pixel mutation. Capture, DNG, TC20, native ABI/kernel, queue and exposure policy freeze.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

helper = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;

/**
 * CHROMAEXPOSURE1B LOCALNEUTRAL1A.
 *
 * GREENAXIS1A's whole-frame neutral statistics remain available and retain their original gate.
 * LOCALNEUTRAL1A adds a stricter 4x6 regional neutral detector so a large/coherent white or grey
 * surface can expose a green-axis cast even when unrelated skin, clothing, foliage or other colour
 * content dilutes the global q75/median. It is intentionally not a white-balance replacement.
 *
 * Detection is read-only. If either the frozen global gate or the new local-neutral gate qualifies,
 * M9R35Renderer may re-render from the same RAW through the existing source-horizontal BT.601/TG1
 * negative-Cr seam. The local path is capped more conservatively at 8%; the absolute 1B ceiling
 * remains 10%. Capture, TC20, DNG, H25/HSM, SAT3, curve02 and native scalar equations stay frozen.
 */
public final class M9ChromaExposure1AController {
    public static final String SCHEMA = "m9cam.chromaexposure.v1b.localneutral1a";
    public static final double MAX_EXTRA_NEG_CR_COMPRESSION = 0.10;
    public static final double MAX_LOCAL_EXTRA_NEG_CR_COMPRESSION = 0.08;

    private static final int SAMPLE_LONG_SIDE = 64;

    // GREENAXIS1A global measurement/gate: frozen.
    private static final int Y_MIN = 24;
    private static final int Y_MAX = 232;
    private static final int ABS_CB_MAX = 18;
    private static final int ABS_CR_MAX = 28;
    private static final int MIN_NEUTRAL_SAMPLES = 96;
    private static final double MIN_NEUTRAL_FRACTION = 0.05;
    private static final double GREEN_MEDIAN_CR_MAX = -3.0;
    private static final double GREEN_Q75_CR_MAX = 1.0;
    private static final double GREEN_NEGATIVE_FRACTION_MIN = 0.60;

    // LOCALNEUTRAL1A uses a tighter neutral mask and requires either a broad single region or
    // supporting adjacent evidence. This is specifically to avoid treating ordinary green scene
    // content as a neutral cast.
    private static final int GRID_ROWS = 4;
    private static final int GRID_COLS = 6;
    private static final int LOCAL_Y_MIN = 40;
    private static final int LOCAL_Y_MAX = 224;
    private static final int LOCAL_ABS_CB_MAX = 10;
    private static final int LOCAL_ABS_CR_MAX = 22;
    private static final int LOCAL_MIN_NEUTRAL_SAMPLES = 18;
    private static final double LOCAL_MIN_NEUTRAL_FRACTION = 0.14;
    private static final double LOCAL_MEDIAN_CR_MAX = -4.0;
    private static final double LOCAL_Q75_CR_MAX = 0.0;
    private static final double LOCAL_GREEN_FRACTION_MIN = 0.65;
    private static final double LOCAL_ABS_MEDIAN_CB_MAX = 8.0;
    private static final double LOCAL_MEAN_Y_MIN = 50.0;

    private static final int SUPPORT_MIN_NEUTRAL_SAMPLES = 14;
    private static final double SUPPORT_MIN_NEUTRAL_FRACTION = 0.10;
    private static final double SUPPORT_MEDIAN_CR_MAX = -2.0;
    private static final double SUPPORT_Q75_CR_MAX = 2.0;
    private static final double SUPPORT_GREEN_FRACTION_MIN = 0.55;
    private static final double SUPPORT_ABS_MEDIAN_CB_MAX = 9.0;
    private static final double SUPPORT_MEAN_Y_MIN = 45.0;

    private static final int LARGE_REGION_MIN_NEUTRAL_SAMPLES = 32;
    private static final double LARGE_REGION_MIN_NEUTRAL_FRACTION = 0.28;
    private static final double MIN_RECOMMENDED_COMPRESSION = 0.02;
    private static final double MIN_LOCAL_RECOMMENDED_COMPRESSION = 0.025;

    private static final double ACCEPT_MIN_GLOBAL_MEDIAN_CR_IMPROVEMENT = 0.5;
    private static final double ACCEPT_MIN_LOCAL_MEAN_CR_IMPROVEMENT = 0.25;
    private static final double ACCEPT_MAX_MAGENTA_MEDIAN_CR = 1.5;
    private static final double ACCEPT_MAX_MEAN_Y_DELTA = 1.5;
    private static final double ACCEPT_MAX_LOCAL_GREEN_FRACTION_INCREASE = 0.02;

    private M9ChromaExposure1AController() {}

    public static JSONObject evaluate(Bitmap bitmap, JSONObject renderer, JSONObject edgeDecision) {
        JSONObject measured = measure(bitmap);
        try {
            measured.put("schema", SCHEMA);
            measured.put("mode", "jpeg_post_exposure_global_or_local_neutral_detect_native_bt601_rerender_if_needed");
            measured.put("captureMutation", false);
            measured.put("tc20BaselineMutation", false);
            measured.put("dngMutation", false);
            measured.put("nativeKernelMutation", false);
            measured.put("maxExtraNegativeCrCompression", MAX_EXTRA_NEG_CR_COMPRESSION);
            measured.put("maxLocalExtraNegativeCrCompression", MAX_LOCAL_EXTRA_NEG_CR_COMPRESSION);
            if (renderer != null) {
                measured.put("cct", renderer.optDouble("cct", Double.NaN));
                measured.put("tungstenGuardWeight", renderer.optDouble("tungstenGuardWeight", Double.NaN));
                measured.put("tc20AppliedGain", renderer.optDouble("gain", Double.NaN));
            }
            if (edgeDecision != null) {
                measured.put("edgeSelector", edgeDecision.optString("selector", "HOLD"));
                measured.put("edgeTreatment", edgeDecision.optString("treatment", "FROZEN"));
                measured.put("edgeAppliedEv", edgeDecision.optDouble("appliedEv", 0.0));
            }

            if (!measured.optBoolean("valid", false)) {
                measured.put("selector", "GREEN_HOLD");
                measured.put("eligible", false);
                measured.put("reason", "measurement_invalid_fail_safe_hold");
                measured.put("recommendedNegativeCrCompression", 0.0);
                return measured;
            }

            int neutralCount = measured.optInt("neutralSampleCount", 0);
            double neutralFraction = measured.optDouble("neutralSampleFraction", 0.0);
            double medianCr = measured.optDouble("neutralMedianCr", Double.NaN);
            double q75Cr = measured.optDouble("neutralQ75Cr", Double.NaN);
            double negativeFraction = measured.optDouble("neutralGreenFractionCrLEMinus3", 0.0);
            double globalGreenBias = finite(medianCr) ? Math.max(0.0, -medianCr) : 0.0;
            double globalRecommended = clamp((globalGreenBias - 2.0) * 0.020,
                    0.0, MAX_EXTRA_NEG_CR_COMPRESSION);

            boolean globalCoherent = neutralCount >= MIN_NEUTRAL_SAMPLES
                    && neutralFraction >= MIN_NEUTRAL_FRACTION
                    && finite(medianCr) && medianCr <= GREEN_MEDIAN_CR_MAX
                    && finite(q75Cr) && q75Cr <= GREEN_Q75_CR_MAX
                    && negativeFraction >= GREEN_NEGATIVE_FRACTION_MIN
                    && globalRecommended >= MIN_RECOMMENDED_COMPRESSION;

            boolean localCoherent = measured.optBoolean("localNeutralEligible", false);
            double localMedianCr = measured.optDouble("localBestMedianCr", Double.NaN);
            double localGreenBias = finite(localMedianCr) ? Math.max(0.0, -localMedianCr) : 0.0;
            double localRecommended = clamp((localGreenBias - 2.0) * 0.015,
                    0.0, MAX_LOCAL_EXTRA_NEG_CR_COMPRESSION);
            if (localRecommended < MIN_LOCAL_RECOMMENDED_COMPRESSION) localCoherent = false;

            measured.put("globalGreenBiasCrCodes", globalGreenBias);
            measured.put("globalGateEligible", globalCoherent);
            measured.put("localGreenBiasCrCodes", localGreenBias);
            measured.put("localGateEligible", localCoherent);
            measured.put("thresholdMedianCrMax", GREEN_MEDIAN_CR_MAX);
            measured.put("thresholdQ75CrMax", GREEN_Q75_CR_MAX);
            measured.put("thresholdGreenFractionMin", GREEN_NEGATIVE_FRACTION_MIN);

            if (globalCoherent) {
                measured.put("selector", "GREEN_GLOBAL_NEUTRAL");
                measured.put("eligible", true);
                measured.put("recommendedNegativeCrCompression", globalRecommended);
                measured.put("reason", "coherent_global_low_chroma_green_axis_bias_after_exposure_placement");
            } else if (localCoherent) {
                measured.put("selector", "GREEN_LOCAL_NEUTRAL");
                measured.put("eligible", true);
                measured.put("recommendedNegativeCrCompression", localRecommended);
                measured.put("reason", "coherent_local_neutral_green_axis_bias_global_statistics_diluted");
            } else {
                measured.put("selector", "GREEN_HOLD");
                measured.put("eligible", false);
                measured.put("recommendedNegativeCrCompression", 0.0);
                measured.put("reason", "global_and_local_neutral_chroma_evidence_below_gate_hold");
            }
        } catch (Throwable t) {
            try {
                measured.put("selector", "GREEN_HOLD");
                measured.put("eligible", false);
                measured.put("recommendedNegativeCrCompression", 0.0);
                measured.put("reason", "evaluation_exception_fail_safe_hold");
                measured.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return measured;
    }

    public static JSONObject measure(Bitmap bitmap) {
        JSONObject out = new JSONObject();
        try {
            if (bitmap == null || bitmap.isRecycled() || bitmap.getWidth() <= 0 || bitmap.getHeight() <= 0) {
                out.put("valid", false);
                return out;
            }
            final int w = bitmap.getWidth(), h = bitmap.getHeight();
            final int sw = w >= h ? SAMPLE_LONG_SIDE : Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * w / (double)h));
            final int sh = w >= h ? Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * h / (double)w)) : SAMPLE_LONG_SIDE;
            final int total = sw * sh;

            int[] globalCr = new int[total];
            int globalNeutralCount = 0;
            double globalYSum = 0.0;
            double globalCrSum = 0.0;
            int globalGreenLeMinus3 = 0;

            final int regionCount = GRID_ROWS * GRID_COLS;
            final int perRegionCapacity = Math.max(1,
                    ((sw + GRID_COLS - 1) / GRID_COLS) * ((sh + GRID_ROWS - 1) / GRID_ROWS));
            int[][] localCr = new int[regionCount][perRegionCapacity];
            int[][] localCb = new int[regionCount][perRegionCapacity];
            int[] localCount = new int[regionCount];
            int[] localCellSamples = new int[regionCount];
            double[] localYSum = new double[regionCount];
            double[] localCrSum = new double[regionCount];
            int[] localGreenLeMinus3 = new int[regionCount];

            for (int sy = 0; sy < sh; sy++) {
                int py = Math.min(h - 1, (int)(((2L * sy + 1L) * h) / (2L * sh)));
                int row = Math.min(GRID_ROWS - 1, (sy * GRID_ROWS) / sh);
                for (int sx = 0; sx < sw; sx++) {
                    int px = Math.min(w - 1, (int)(((2L * sx + 1L) * w) / (2L * sw)));
                    int col = Math.min(GRID_COLS - 1, (sx * GRID_COLS) / sw);
                    int idx = row * GRID_COLS + col;
                    localCellSamples[idx]++;

                    int p = bitmap.getPixel(px, py);
                    int r = (p >>> 16) & 255;
                    int g = (p >>> 8) & 255;
                    int b = p & 255;
                    int y = (4899 * r + 9617 * g + 1868 * b) >> 14;
                    int cb = (-2765 * r - 5427 * g + 8192 * b) >> 14;
                    int cr = (8192 * r - 6860 * g - 1332 * b) >> 14;

                    if (y >= Y_MIN && y <= Y_MAX && Math.abs(cb) <= ABS_CB_MAX && Math.abs(cr) <= ABS_CR_MAX) {
                        globalCr[globalNeutralCount++] = cr;
                        globalYSum += y;
                        globalCrSum += cr;
                        if (cr <= -3) globalGreenLeMinus3++;
                    }

                    if (y < LOCAL_Y_MIN || y > LOCAL_Y_MAX) continue;
                    if (Math.abs(cb) > LOCAL_ABS_CB_MAX || Math.abs(cr) > LOCAL_ABS_CR_MAX) continue;
                    int n = localCount[idx];
                    if (n >= perRegionCapacity) continue;
                    localCr[idx][n] = cr;
                    localCb[idx][n] = cb;
                    localCount[idx] = n + 1;
                    localYSum[idx] += y;
                    localCrSum[idx] += cr;
                    if (cr <= -3) localGreenLeMinus3[idx]++;
                }
            }

            out.put("valid", total > 0);
            out.put("sampleCount", total);
            out.put("neutralSampleCount", globalNeutralCount);
            out.put("neutralSampleFraction", total > 0 ? globalNeutralCount / (double)total : 0.0);
            if (globalNeutralCount > 0) {
                Arrays.sort(globalCr, 0, globalNeutralCount);
                out.put("neutralQ25Cr", quantileSorted(globalCr, globalNeutralCount, 0.25));
                out.put("neutralMedianCr", quantileSorted(globalCr, globalNeutralCount, 0.50));
                out.put("neutralQ75Cr", quantileSorted(globalCr, globalNeutralCount, 0.75));
                out.put("neutralMeanCr", globalCrSum / globalNeutralCount);
                out.put("neutralMeanY", globalYSum / globalNeutralCount);
                out.put("neutralGreenFractionCrLEMinus3", globalGreenLeMinus3 / (double)globalNeutralCount);
            }

            JSONArray regions = new JSONArray();
            boolean[] strong = new boolean[regionCount];
            boolean[] support = new boolean[regionCount];
            double[] score = new double[regionCount];
            double[] regionFraction = new double[regionCount];
            double[] regionMedianCr = new double[regionCount];
            double[] regionQ75Cr = new double[regionCount];
            double[] regionMeanCr = new double[regionCount];
            double[] regionMeanY = new double[regionCount];
            double[] regionGreenFraction = new double[regionCount];
            double[] regionMedianCb = new double[regionCount];
            Arrays.fill(regionMedianCr, Double.NaN);
            Arrays.fill(regionQ75Cr, Double.NaN);
            Arrays.fill(regionMeanCr, Double.NaN);
            Arrays.fill(regionMeanY, Double.NaN);
            Arrays.fill(regionGreenFraction, Double.NaN);
            Arrays.fill(regionMedianCb, Double.NaN);

            int strongCount = 0;
            int supportCount = 0;
            for (int idx = 0; idx < regionCount; idx++) {
                int n = localCount[idx];
                JSONObject region = new JSONObject();
                int row = idx / GRID_COLS;
                int col = idx % GRID_COLS;
                double fraction = localCellSamples[idx] > 0 ? n / (double)localCellSamples[idx] : 0.0;
                regionFraction[idx] = fraction;
                region.put("row", row);
                region.put("column", col);
                region.put("sampleCount", localCellSamples[idx]);
                region.put("neutralSampleCount", n);
                region.put("neutralSampleFraction", fraction);
                if (n > 0) {
                    Arrays.sort(localCr[idx], 0, n);
                    Arrays.sort(localCb[idx], 0, n);
                    double q25Cr = quantileSorted(localCr[idx], n, 0.25);
                    double medianCr = quantileSorted(localCr[idx], n, 0.50);
                    double q75Cr = quantileSorted(localCr[idx], n, 0.75);
                    double medianCb = quantileSorted(localCb[idx], n, 0.50);
                    double meanCr = localCrSum[idx] / n;
                    double meanY = localYSum[idx] / n;
                    double greenFraction = localGreenLeMinus3[idx] / (double)n;
                    regionMedianCr[idx] = medianCr;
                    regionQ75Cr[idx] = q75Cr;
                    regionMeanCr[idx] = meanCr;
                    regionMeanY[idx] = meanY;
                    regionGreenFraction[idx] = greenFraction;
                    regionMedianCb[idx] = medianCb;
                    region.put("neutralQ25Cr", q25Cr);
                    region.put("neutralMedianCr", medianCr);
                    region.put("neutralQ75Cr", q75Cr);
                    region.put("neutralMeanCr", meanCr);
                    region.put("neutralMedianCb", medianCb);
                    region.put("neutralMeanY", meanY);
                    region.put("neutralGreenFractionCrLEMinus3", greenFraction);

                    strong[idx] = n >= LOCAL_MIN_NEUTRAL_SAMPLES
                            && fraction >= LOCAL_MIN_NEUTRAL_FRACTION
                            && meanY >= LOCAL_MEAN_Y_MIN
                            && medianCr <= LOCAL_MEDIAN_CR_MAX
                            && q75Cr <= LOCAL_Q75_CR_MAX
                            && greenFraction >= LOCAL_GREEN_FRACTION_MIN
                            && Math.abs(medianCb) <= LOCAL_ABS_MEDIAN_CB_MAX;
                    support[idx] = n >= SUPPORT_MIN_NEUTRAL_SAMPLES
                            && fraction >= SUPPORT_MIN_NEUTRAL_FRACTION
                            && meanY >= SUPPORT_MEAN_Y_MIN
                            && medianCr <= SUPPORT_MEDIAN_CR_MAX
                            && q75Cr <= SUPPORT_Q75_CR_MAX
                            && greenFraction >= SUPPORT_GREEN_FRACTION_MIN
                            && Math.abs(medianCb) <= SUPPORT_ABS_MEDIAN_CB_MAX;
                    if (strong[idx]) strongCount++;
                    if (support[idx]) supportCount++;
                    double bias = Math.max(0.0, -medianCr);
                    score[idx] = fraction * fraction * greenFraction * clamp(bias / 8.0, 0.0, 1.0);
                    region.put("strongCandidate", strong[idx]);
                    region.put("supportCandidate", support[idx]);
                    region.put("selectionScore", score[idx]);
                } else {
                    region.put("strongCandidate", false);
                    region.put("supportCandidate", false);
                    region.put("selectionScore", 0.0);
                }
                regions.put(region);
            }

            int best = -1;
            boolean bestBroad = false;
            boolean bestAdjacent = false;
            double bestScore = -1.0;
            for (int idx = 0; idx < regionCount; idx++) {
                if (!strong[idx]) continue;
                boolean broad = localCount[idx] >= LARGE_REGION_MIN_NEUTRAL_SAMPLES
                        && regionFraction[idx] >= LARGE_REGION_MIN_NEUTRAL_FRACTION;
                boolean adjacent = hasAdjacentSupport(idx, support);
                if (!broad && !adjacent) continue;
                if (score[idx] > bestScore) {
                    best = idx;
                    bestScore = score[idx];
                    bestBroad = broad;
                    bestAdjacent = adjacent;
                }
            }

            out.put("localGridRows", GRID_ROWS);
            out.put("localGridColumns", GRID_COLS);
            out.put("localNeutralRegions", regions);
            out.put("localStrongRegionCount", strongCount);
            out.put("localSupportRegionCount", supportCount);
            out.put("localNeutralEligible", best >= 0);
            if (best >= 0) {
                out.put("localBestRow", best / GRID_COLS);
                out.put("localBestColumn", best % GRID_COLS);
                out.put("localBestSelectionScore", bestScore);
                out.put("localBestBroadSurface", bestBroad);
                out.put("localBestAdjacentSupport", bestAdjacent);
                out.put("localBestNeutralSampleCount", localCount[best]);
                out.put("localBestNeutralSampleFraction", regionFraction[best]);
                out.put("localBestMedianCr", regionMedianCr[best]);
                out.put("localBestQ75Cr", regionQ75Cr[best]);
                out.put("localBestMeanCr", regionMeanCr[best]);
                out.put("localBestMedianCb", regionMedianCb[best]);
                out.put("localBestMeanY", regionMeanY[best]);
                out.put("localBestGreenFractionCrLEMinus3", regionGreenFraction[best]);
            }
        } catch (Throwable t) {
            try { out.put("valid", false); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    public static boolean acceptCandidate(JSONObject before, JSONObject after) {
        if (before == null || after == null || !before.optBoolean("valid", false) || !after.optBoolean("valid", false)) return false;
        String selector = before.optString("selector", "GREEN_HOLD");
        double beforeY = before.optDouble("neutralMeanY", Double.NaN);
        double afterY = after.optDouble("neutralMeanY", Double.NaN);
        double afterGlobalCr = after.optDouble("neutralMedianCr", Double.NaN);
        if (!finite(beforeY) || !finite(afterY) || !finite(afterGlobalCr)) return false;
        if (Math.abs(afterY - beforeY) > ACCEPT_MAX_MEAN_Y_DELTA) return false;
        if (afterGlobalCr > ACCEPT_MAX_MAGENTA_MEDIAN_CR) return false;

        try {
            before.put("candidateAcceptanceSelector", selector);
            before.put("candidateGlobalMeanYDelta", afterY - beforeY);
            before.put("candidateGlobalMedianCr", afterGlobalCr);
        } catch (Exception ignored) {}

        if ("GREEN_GLOBAL_NEUTRAL".equals(selector)) {
            double beforeCr = before.optDouble("neutralMedianCr", Double.NaN);
            if (!finite(beforeCr)) return false;
            boolean accepted = afterGlobalCr >= beforeCr + ACCEPT_MIN_GLOBAL_MEDIAN_CR_IMPROVEMENT;
            try {
                before.put("candidateGlobalMedianCrImprovement", afterGlobalCr - beforeCr);
            } catch (Exception ignored) {}
            return accepted;
        }

        if ("GREEN_LOCAL_NEUTRAL".equals(selector)) {
            int row = before.optInt("localBestRow", -1);
            int col = before.optInt("localBestColumn", -1);
            JSONObject beforeRegion = findRegion(before, row, col);
            JSONObject afterRegion = findRegion(after, row, col);
            if (beforeRegion == null || afterRegion == null) return false;
            double beforeMeanCr = beforeRegion.optDouble("neutralMeanCr", Double.NaN);
            double afterMeanCr = afterRegion.optDouble("neutralMeanCr", Double.NaN);
            double beforeMedianCr = beforeRegion.optDouble("neutralMedianCr", Double.NaN);
            double afterMedianCr = afterRegion.optDouble("neutralMedianCr", Double.NaN);
            double beforeLocalY = beforeRegion.optDouble("neutralMeanY", Double.NaN);
            double afterLocalY = afterRegion.optDouble("neutralMeanY", Double.NaN);
            double beforeGreen = beforeRegion.optDouble("neutralGreenFractionCrLEMinus3", Double.NaN);
            double afterGreen = afterRegion.optDouble("neutralGreenFractionCrLEMinus3", Double.NaN);
            if (!finite(beforeMeanCr) || !finite(afterMeanCr)
                    || !finite(beforeMedianCr) || !finite(afterMedianCr)
                    || !finite(beforeLocalY) || !finite(afterLocalY)
                    || !finite(beforeGreen) || !finite(afterGreen)) return false;

            double meanCrImprovement = afterMeanCr - beforeMeanCr;
            boolean accepted = meanCrImprovement >= ACCEPT_MIN_LOCAL_MEAN_CR_IMPROVEMENT
                    && afterMedianCr >= beforeMedianCr
                    && afterMedianCr <= ACCEPT_MAX_MAGENTA_MEDIAN_CR
                    && Math.abs(afterLocalY - beforeLocalY) <= ACCEPT_MAX_MEAN_Y_DELTA
                    && afterGreen <= beforeGreen + ACCEPT_MAX_LOCAL_GREEN_FRACTION_INCREASE;
            try {
                before.put("candidateLocalRow", row);
                before.put("candidateLocalColumn", col);
                before.put("candidateLocalMeanCrBefore", beforeMeanCr);
                before.put("candidateLocalMeanCrAfter", afterMeanCr);
                before.put("candidateLocalMeanCrImprovement", meanCrImprovement);
                before.put("candidateLocalMedianCrBefore", beforeMedianCr);
                before.put("candidateLocalMedianCrAfter", afterMedianCr);
                before.put("candidateLocalMeanYDelta", afterLocalY - beforeLocalY);
                before.put("candidateLocalGreenFractionBefore", beforeGreen);
                before.put("candidateLocalGreenFractionAfter", afterGreen);
            } catch (Exception ignored) {}
            return accepted;
        }
        return false;
    }

    private static JSONObject findRegion(JSONObject measurement, int row, int col) {
        if (measurement == null || row < 0 || col < 0) return null;
        JSONArray regions = measurement.optJSONArray("localNeutralRegions");
        if (regions == null) return null;
        for (int i = 0; i < regions.length(); i++) {
            JSONObject r = regions.optJSONObject(i);
            if (r != null && r.optInt("row", -1) == row && r.optInt("column", -1) == col) return r;
        }
        return null;
    }

    private static boolean hasAdjacentSupport(int idx, boolean[] support) {
        int row = idx / GRID_COLS;
        int col = idx % GRID_COLS;
        if (row > 0 && support[(row - 1) * GRID_COLS + col]) return true;
        if (row + 1 < GRID_ROWS && support[(row + 1) * GRID_COLS + col]) return true;
        if (col > 0 && support[row * GRID_COLS + col - 1]) return true;
        return col + 1 < GRID_COLS && support[row * GRID_COLS + col + 1];
    }

    private static double quantileSorted(int[] values, int n, double q) {
        if (n <= 0) return Double.NaN;
        double p = (n - 1) * q;
        int lo = (int)Math.floor(p);
        int hi = (int)Math.ceil(p);
        double f = p - lo;
        return values[lo] + f * (values[hi] - values[lo]);
    }

    private static double clamp(double v, double lo, double hi) { return Math.max(lo, Math.min(hi, v)); }
    private static boolean finite(double v) { return !Double.isNaN(v) && !Double.isInfinite(v); }
}
'''
write(helper_rel, helper)

# Keep the 1A-established renderer seam and rerender flow, but promote diagnostics to 1B naming.
for old, new in [
    ('chromaExposure1ARequestedNegativeCrCompression', 'chromaExposure1BRequestedNegativeCrCompression'),
    ('chromaExposure1AEffectiveNegativeCrGain', 'chromaExposure1BEffectiveNegativeCrGain'),
    ('out.diagnostics.put("chromaExposure1A", chromaDecision);', 'out.diagnostics.put("chromaExposure1B", chromaDecision);'),
    ('CHROMAEXPOSURE1A_GREENAXIS1A: detect on the actual exposure-settled JPEG candidate.',
     'CHROMAEXPOSURE1B_LOCALNEUTRAL1A: global-or-local neutral detection on the exposure-settled JPEG candidate.'),
]:
    if old not in renderer:
        raise SystemExit('CHROMAEXPOSURE1B renderer anchor missing: ' + old)
    renderer = renderer.replace(old, new, 1)
write(renderer_rel, renderer)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit(f'CHROMAEXPOSURE1B frozen-source violation: {rel} changed')

print('Applied M9 CHROMAEXPOSURE1B LOCALNEUTRAL1A')
print(' - GREENAXIS1A global gate retained unchanged')
print(' - added strict 4x6 local-neutral detector with broad-surface/adjacent-support qualification')
print(' - local correction recommendation capped at <=8%; absolute negative-Cr ceiling remains <=10%')
print(' - local candidate acceptance follows the selected region and requires mean-Cr improvement + luma stability')
print(' - capture, TC20, DNG, native kernel/ABI, H25/HSM, SAT3, curve02 and EDGE exposure logic frozen')
