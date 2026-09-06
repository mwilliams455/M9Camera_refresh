#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-chromaexposure1a-greenaxis.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('CHROMAEXPOSURE1A missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
renderer = read(renderer_rel)
if 'BESTFIT2A_LIVE1' not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A requires EDGEPLACEMENTBESTFIT2A LIVE1')
if 'M9 DNGGAINMAPFIX1A' not in read('app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java'):
    raise SystemExit('CHROMAEXPOSURE1A requires promoted DNGGAINMAPFIX1A baseline')

# This experiment may alter only the JPEG renderer plus a new read-only detector/helper.
# Capture, DNG, TC20 implementation, native colour kernel and queue ownership remain frozen.
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

helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ChromaExposure1AController.java'
if (root / helper_rel).exists():
    raise SystemExit('CHROMAEXPOSURE1A helper already exists; refuse ambiguous reapply')

helper = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;

import org.json.JSONObject;

import java.util.Arrays;

/**
 * CHROMAEXPOSURE1A GREENAXIS1A.
 *
 * Read-only detector over the actual JPEG candidate after EDGEPLACEMENTBESTFIT2A has made its
 * exposure decision. It estimates a coherent green cast only from low-chroma, non-extreme-luma
 * samples, then recommends a bounded extra compression of the negative BT.601 Cr axis.
 *
 * The correction itself is not a post-render RGB tint. When accepted, M9R35Renderer re-renders
 * from the same RAW and applies the bounded multiplier at the existing source-horizontal BT.601
 * 4:2:2 TG1 seam. Y, capture exposure, TC20 baseline, DNG and the native scalar equations remain
 * structurally unchanged.
 */
public final class M9ChromaExposure1AController {
    public static final String SCHEMA = "m9cam.chromaexposure.v1a.greenaxis1a";
    public static final double MAX_EXTRA_NEG_CR_COMPRESSION = 0.10;

    private static final int SAMPLE_LONG_SIDE = 64;
    private static final int Y_MIN = 24;
    private static final int Y_MAX = 232;
    private static final int ABS_CB_MAX = 18;
    private static final int ABS_CR_MAX = 28;
    private static final int MIN_NEUTRAL_SAMPLES = 96;
    private static final double MIN_NEUTRAL_FRACTION = 0.05;
    private static final double GREEN_MEDIAN_CR_MAX = -3.0;
    private static final double GREEN_Q75_CR_MAX = 1.0;
    private static final double GREEN_NEGATIVE_FRACTION_MIN = 0.60;
    private static final double MIN_RECOMMENDED_COMPRESSION = 0.02;
    private static final double ACCEPT_MIN_MEDIAN_CR_IMPROVEMENT = 0.5;
    private static final double ACCEPT_MAX_MAGENTA_MEDIAN_CR = 1.5;
    private static final double ACCEPT_MAX_MEAN_Y_DELTA = 1.5;

    private M9ChromaExposure1AController() {}

    public static JSONObject evaluate(Bitmap bitmap, JSONObject renderer, JSONObject edgeDecision) {
        JSONObject measured = measure(bitmap);
        try {
            measured.put("schema", SCHEMA);
            measured.put("mode", "jpeg_post_exposure_detect_native_bt601_rerender_if_needed");
            measured.put("captureMutation", false);
            measured.put("tc20BaselineMutation", false);
            measured.put("dngMutation", false);
            measured.put("nativeKernelMutation", false);
            measured.put("maxExtraNegativeCrCompression", MAX_EXTRA_NEG_CR_COMPRESSION);
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
            double greenBias = finite(medianCr) ? Math.max(0.0, -medianCr) : 0.0;
            double recommended = clamp((greenBias - 2.0) * 0.020, 0.0, MAX_EXTRA_NEG_CR_COMPRESSION);

            boolean coherent = neutralCount >= MIN_NEUTRAL_SAMPLES
                    && neutralFraction >= MIN_NEUTRAL_FRACTION
                    && finite(medianCr) && medianCr <= GREEN_MEDIAN_CR_MAX
                    && finite(q75Cr) && q75Cr <= GREEN_Q75_CR_MAX
                    && negativeFraction >= GREEN_NEGATIVE_FRACTION_MIN
                    && recommended >= MIN_RECOMMENDED_COMPRESSION;

            measured.put("greenBiasCrCodes", greenBias);
            measured.put("recommendedNegativeCrCompression", coherent ? recommended : 0.0);
            measured.put("eligible", coherent);
            measured.put("reason", coherent
                    ? "coherent_low_chroma_green_axis_bias_after_exposure_placement"
                    : "neutral_chroma_evidence_below_gate_hold");
            measured.put("thresholdMedianCrMax", GREEN_MEDIAN_CR_MAX);
            measured.put("thresholdQ75CrMax", GREEN_Q75_CR_MAX);
            measured.put("thresholdGreenFractionMin", GREEN_NEGATIVE_FRACTION_MIN);
        } catch (Throwable t) {
            try {
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
            int[] crValues = new int[total];
            int neutralCount = 0;
            double neutralYSum = 0.0;
            int greenLeMinus3 = 0;

            for (int sy = 0; sy < sh; sy++) {
                int py = Math.min(h - 1, (int)(((2L * sy + 1L) * h) / (2L * sh)));
                for (int sx = 0; sx < sw; sx++) {
                    int px = Math.min(w - 1, (int)(((2L * sx + 1L) * w) / (2L * sw)));
                    int p = bitmap.getPixel(px, py);
                    int r = (p >>> 16) & 255;
                    int g = (p >>> 8) & 255;
                    int b = p & 255;
                    int y = (4899 * r + 9617 * g + 1868 * b) >> 14;
                    int cb = (-2765 * r - 5427 * g + 8192 * b) >> 14;
                    int cr = (8192 * r - 6860 * g - 1332 * b) >> 14;
                    if (y < Y_MIN || y > Y_MAX) continue;
                    if (Math.abs(cb) > ABS_CB_MAX || Math.abs(cr) > ABS_CR_MAX) continue;
                    crValues[neutralCount++] = cr;
                    neutralYSum += y;
                    if (cr <= -3) greenLeMinus3++;
                }
            }

            out.put("valid", total > 0);
            out.put("sampleCount", total);
            out.put("neutralSampleCount", neutralCount);
            out.put("neutralSampleFraction", total > 0 ? neutralCount / (double)total : 0.0);
            if (neutralCount > 0) {
                Arrays.sort(crValues, 0, neutralCount);
                double q25 = quantileSorted(crValues, neutralCount, 0.25);
                double median = quantileSorted(crValues, neutralCount, 0.50);
                double q75 = quantileSorted(crValues, neutralCount, 0.75);
                out.put("neutralQ25Cr", q25);
                out.put("neutralMedianCr", median);
                out.put("neutralQ75Cr", q75);
                out.put("neutralMeanY", neutralYSum / neutralCount);
                out.put("neutralGreenFractionCrLEMinus3", greenLeMinus3 / (double)neutralCount);
            }
        } catch (Throwable t) {
            try { out.put("valid", false); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    public static boolean acceptCandidate(JSONObject before, JSONObject after) {
        if (before == null || after == null || !before.optBoolean("valid", false) || !after.optBoolean("valid", false)) return false;
        double beforeCr = before.optDouble("neutralMedianCr", Double.NaN);
        double afterCr = after.optDouble("neutralMedianCr", Double.NaN);
        double beforeY = before.optDouble("neutralMeanY", Double.NaN);
        double afterY = after.optDouble("neutralMeanY", Double.NaN);
        if (!finite(beforeCr) || !finite(afterCr) || !finite(beforeY) || !finite(afterY)) return false;
        return afterCr >= beforeCr + ACCEPT_MIN_MEDIAN_CR_IMPROVEMENT
                && afterCr <= ACCEPT_MAX_MAGENTA_MEDIAN_CR
                && Math.abs(afterY - beforeY) <= ACCEPT_MAX_MEAN_Y_DELTA;
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

# Baseline and EDGE dark rerenders gain a third argument. Zero preserves the exact frozen path.
old = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
new = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0, 0.0);'''
if old not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A baseline renderCore call anchor missing')
renderer = renderer.replace(old, new, 1)

old = '''                        candidateCore = renderCore(frame.buffer, frame.width, frame.height,
                                encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, candidateEv);'''
new = '''                        candidateCore = renderCore(frame.buffer, frame.width, frame.height,
                                encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, candidateEv, 0.0);'''
if old not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A dark rerender anchor missing')
renderer = renderer.replace(old, new, 1)

sig_old = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation,
                                         double edgePlacementGainEv) throws Exception {'''
sig_new = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation,
                                         double edgePlacementGainEv,
                                         double chromaGreenCompression) throws Exception {'''
if sig_old not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A renderCore signature anchor missing')
renderer = renderer.replace(sig_old, sig_new, 1)

cr_anchor = '''            final double tgWeight = tungstenGuardWeight(ctx.cct);
            final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
            final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;
'''
cr_new = '''            final double tgWeight = tungstenGuardWeight(ctx.cct);
            final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
            final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;
            // CHROMAEXPOSURE1A: a second bounded frame-level multiplier on the existing
            // negative-Cr seam. chromaGreenCompression==0 is the exact frozen TG1 value.
            final double boundedGreenCompression = clamp(chromaGreenCompression, 0.0,
                    M9ChromaExposure1AController.MAX_EXTRA_NEG_CR_COMPRESSION);
            final double effectiveCrGain = tgCrGain * (1.0 - boundedGreenCompression);
'''
if cr_anchor not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A TG1 gain anchor missing')
renderer = renderer.replace(cr_anchor, cr_new, 1)

# All four promoted native colour call sites use the effective Cr gain. Native code is untouched.
count = renderer.count('effectiveRenderGain, tgCbGain, tgCrGain')
if count != 4:
    raise SystemExit(f'CHROMAEXPOSURE1A expected 4 native colour call sites, found {count}')
renderer = renderer.replace('effectiveRenderGain, tgCbGain, tgCrGain',
                            'effectiveRenderGain, tgCbGain, effectiveCrGain')

# Record the actual chroma multiplier in renderer diagnostics.
diag_anchor = '''            d.put("tungstenGuardNegativeCbCompression", TG_NEG_CB_COMPRESSION);
            d.put("tungstenGuardNegativeCrCompression", TG_NEG_CR_COMPRESSION);
'''
diag_new = '''            d.put("tungstenGuardNegativeCbCompression", TG_NEG_CB_COMPRESSION);
            d.put("tungstenGuardNegativeCrCompression", TG_NEG_CR_COMPRESSION);
            d.put("chromaExposure1ARequestedNegativeCrCompression", boundedGreenCompression);
            d.put("chromaExposure1AEffectiveNegativeCrGain", effectiveCrGain);
'''
if diag_anchor not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A diagnostics anchor missing')
renderer = renderer.replace(diag_anchor, diag_new, 1)

# Evaluate green bias only after EDGEPLACEMENTBESTFIT2A has settled the actual JPEG exposure.
# If correction is needed, re-render from the same RAW at the same EDGE render EV and then
# re-apply the BRIGHT pivot (if that was the exposure treatment). Any failure preserves the
# already accepted exposure-only bitmap.
anchor = '            out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);\n'
if anchor not in renderer:
    raise SystemExit('CHROMAEXPOSURE1A edge decision completion anchor missing')
block = r'''            out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);

            // CHROMAEXPOSURE1A_GREENAXIS1A: detect on the actual exposure-settled JPEG candidate.
            JSONObject chromaDecision = M9ChromaExposure1AController.evaluate(bitmap, out.diagnostics, edgeDecision);
            chromaDecision.put("applied", false);
            chromaDecision.put("treatment", "HOLD");
            if (chromaDecision.optBoolean("eligible", false)) {
                Bitmap chromaCandidate = null;
                Bitmap pivotedCandidate = null;
                try {
                    double compression = chromaDecision.optDouble("recommendedNegativeCrCompression", 0.0);
                    String edgeTreatment = edgeDecision.optString("treatment", "FROZEN");
                    double rerenderEv = edgeTreatment.startsWith("DARK_EXACT_RERENDER")
                            ? edgeDecision.optDouble("appliedEv", 0.0) : 0.0;
                    boolean reapplyBrightPivot = "BRIGHT_RGB_PIVOT".equals(edgeTreatment);
                    long chromaStartedNs = System.nanoTime();
                    RenderCore chromaCore = renderCore(frame.buffer, frame.width, frame.height,
                            encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation,
                            rerenderEv, compression);
                    chromaCandidate = chromaCore.bitmap;
                    if (reapplyBrightPivot) {
                        pivotedCandidate = M9EdgePlacementBestFit2AController.applyBrightPivot(
                                chromaCandidate, M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                        if (pivotedCandidate != null) {
                            if (chromaCandidate != null && chromaCandidate != pivotedCandidate && !chromaCandidate.isRecycled()) {
                                chromaCandidate.recycle();
                            }
                            chromaCandidate = pivotedCandidate;
                            pivotedCandidate = null;
                        }
                    }
                    JSONObject afterChroma = M9ChromaExposure1AController.measure(chromaCandidate);
                    boolean accepted = M9ChromaExposure1AController.acceptCandidate(chromaDecision, afterChroma);
                    chromaDecision.put("candidate", afterChroma);
                    chromaDecision.put("candidateAccepted", accepted);
                    chromaDecision.put("candidateRenderElapsedMs", (System.nanoTime() - chromaStartedNs) / 1_000_000.0);
                    chromaDecision.put("rerenderEdgeEv", rerenderEv);
                    chromaDecision.put("reappliedBrightPivot", reapplyBrightPivot);
                    if (accepted) {
                        if (bitmap != null && bitmap != chromaCandidate && !bitmap.isRecycled()) bitmap.recycle();
                        bitmap = chromaCandidate;
                        chromaCandidate = null;
                        chromaDecision.put("applied", true);
                        chromaDecision.put("treatment", "NATIVE_NEGATIVE_CR_RERENDER");
                        chromaDecision.put("appliedNegativeCrCompression", compression);
                        // Keep exported luma diagnostics tied to final JPEG pixels.
                        out.diagnostics.put("directRenderedLumaPreChroma", out.diagnostics.optJSONObject("directRenderedLuma"));
                        out.diagnostics.put("directRenderedLuma", M9RenderedLumaDiagnostic.measure(bitmap));
                    } else {
                        chromaDecision.put("rollbackReason", "candidate_failed_bias_or_luma_acceptance_budget");
                    }
                } catch (Throwable chromaError) {
                    chromaDecision.put("rollbackReason", "chroma_rerender_exception_exposure_candidate_preserved");
                    chromaDecision.put("error", chromaError.toString());
                } finally {
                    if (chromaCandidate != null && !chromaCandidate.isRecycled()) chromaCandidate.recycle();
                    if (pivotedCandidate != null && !pivotedCandidate.isRecycled()) pivotedCandidate.recycle();
                }
            }
            out.diagnostics.put("chromaExposure1A", chromaDecision);
'''
renderer = renderer.replace(anchor, block, 1)

write(renderer_rel, renderer)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit(f'CHROMAEXPOSURE1A frozen-source violation: {rel} changed')

print('Applied M9 CHROMAEXPOSURE1A GREENAXIS1A')
print(' - detector runs after EDGEPLACEMENTBESTFIT2A exposure placement')
print(' - low-chroma neutral evidence gates a bounded <=10% extra negative-Cr compression')
print(' - accepted correction re-renders through existing source-horizontal BT.601/TG1 seam')
print(' - capture, TC20 baseline, DNGGAINMAPFIX1A, native kernel and DNG async ownership frozen')
