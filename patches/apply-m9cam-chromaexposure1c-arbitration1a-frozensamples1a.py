#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-chromaexposure1c-arbitration1a-frozensamples1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('CHROMAEXPOSURE1C missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ChromaExposure1AController.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
helper = read(helper_rel)
renderer = read(renderer_rel)

if 'm9cam.chromaexposure.v1b.localneutral1a' not in helper:
    raise SystemExit('CHROMAEXPOSURE1C requires CHROMAEXPOSURE1B LOCALNEUTRAL1A baseline')
if 'chromaExposure1B' not in renderer:
    raise SystemExit('CHROMAEXPOSURE1C requires CHROMAEXPOSURE1B renderer integration')

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

helper = helper.replace(
    'public static final String SCHEMA = "m9cam.chromaexposure.v1b.localneutral1a";',
    'public static final String SCHEMA = "m9cam.chromaexposure.v1c.arbitration1a.frozensamples1a";',
    1)

anchor = '    private static final double MIN_LOCAL_RECOMMENDED_COMPRESSION = 0.025;\n'
if anchor not in helper:
    raise SystemExit('CHROMAEXPOSURE1C arbitration constant anchor missing')
helper = helper.replace(anchor, anchor +
    '    private static final double LOCAL_OVERRIDE_MIN_COMPRESSION_ADVANTAGE = 0.01;\n', 1)

old_selector = '''            if (globalCoherent) {
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
'''
new_selector = '''            double recommendationAdvantage = localRecommended - globalRecommended;
            boolean localOverridesGlobal = globalCoherent && localCoherent
                    && recommendationAdvantage >= LOCAL_OVERRIDE_MIN_COMPRESSION_ADVANTAGE;
            measured.put("globalRecommendedNegativeCrCompression", globalCoherent ? globalRecommended : 0.0);
            measured.put("localRecommendedNegativeCrCompression", localCoherent ? localRecommended : 0.0);
            measured.put("localVsGlobalCompressionAdvantage", recommendationAdvantage);
            measured.put("localOverrideMinCompressionAdvantage", LOCAL_OVERRIDE_MIN_COMPRESSION_ADVANTAGE);
            measured.put("localOverridesGlobal", localOverridesGlobal);
            measured.put("arbitrationPolicy", "local_overrides_global_when_both_qualify_and_local_recommendation_is_at_least_0p01_stronger");

            if (localOverridesGlobal) {
                measured.put("selector", "GREEN_LOCAL_NEUTRAL");
                measured.put("eligible", true);
                measured.put("recommendedNegativeCrCompression", localRecommended);
                measured.put("reason", "coherent_local_neutral_green_axis_bias_stronger_than_marginal_global_gate");
            } else if (globalCoherent) {
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
'''
if old_selector not in helper:
    raise SystemExit('CHROMAEXPOSURE1C selector block anchor missing')
helper = helper.replace(old_selector, new_selector, 1)

start = helper.find('    public static boolean acceptCandidate(JSONObject before, JSONObject after) {')
end = helper.find('    private static JSONObject findRegion(JSONObject measurement, int row, int col) {')
if start < 0 or end < 0 or end <= start:
    raise SystemExit('CHROMAEXPOSURE1C acceptCandidate block anchors missing')

new_accept = r'''    public static boolean acceptCandidate(Bitmap beforeBitmap, Bitmap afterBitmap,
                                          JSONObject before, JSONObject after) {
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
            JSONObject frozen = measureFrozenLocalSampleSet(beforeBitmap, afterBitmap, row, col);
            if (frozen == null || !frozen.optBoolean("valid", false)) return false;

            double beforeMeanCr = frozen.optDouble("beforeMeanCr", Double.NaN);
            double afterMeanCr = frozen.optDouble("afterMeanCr", Double.NaN);
            double beforeMedianCr = frozen.optDouble("beforeMedianCr", Double.NaN);
            double afterMedianCr = frozen.optDouble("afterMedianCr", Double.NaN);
            double meanYDelta = frozen.optDouble("meanYDelta", Double.NaN);
            double beforeGreen = frozen.optDouble("beforeGreenFractionCrLEMinus3", Double.NaN);
            double afterGreen = frozen.optDouble("afterGreenFractionCrLEMinus3", Double.NaN);
            int frozenCount = frozen.optInt("sampleCount", 0);
            if (frozenCount < LOCAL_MIN_NEUTRAL_SAMPLES
                    || !finite(beforeMeanCr) || !finite(afterMeanCr)
                    || !finite(beforeMedianCr) || !finite(afterMedianCr)
                    || !finite(meanYDelta) || !finite(beforeGreen) || !finite(afterGreen)) return false;

            double meanCrImprovement = afterMeanCr - beforeMeanCr;
            boolean accepted = meanCrImprovement >= ACCEPT_MIN_LOCAL_MEAN_CR_IMPROVEMENT
                    && afterMedianCr >= beforeMedianCr
                    && afterMedianCr <= ACCEPT_MAX_MAGENTA_MEDIAN_CR
                    && Math.abs(meanYDelta) <= ACCEPT_MAX_MEAN_Y_DELTA
                    && afterGreen <= beforeGreen + ACCEPT_MAX_LOCAL_GREEN_FRACTION_INCREASE;
            try {
                before.put("candidateLocalRow", row);
                before.put("candidateLocalColumn", col);
                before.put("candidateLocalAcceptanceMode", "frozen_before_neutral_sample_coordinates");
                before.put("candidateLocalFrozenSampleCount", frozenCount);
                before.put("candidateLocalMeanCrBefore", beforeMeanCr);
                before.put("candidateLocalMeanCrAfter", afterMeanCr);
                before.put("candidateLocalMeanCrImprovement", meanCrImprovement);
                before.put("candidateLocalMedianCrBefore", beforeMedianCr);
                before.put("candidateLocalMedianCrAfter", afterMedianCr);
                before.put("candidateLocalMeanYDelta", meanYDelta);
                before.put("candidateLocalGreenFractionBefore", beforeGreen);
                before.put("candidateLocalGreenFractionAfter", afterGreen);
                before.put("candidateFrozenLocal", frozen);
            } catch (Exception ignored) {}
            return accepted;
        }
        return false;
    }

    private static JSONObject measureFrozenLocalSampleSet(Bitmap beforeBitmap, Bitmap afterBitmap,
                                                           int targetRow, int targetCol) {
        JSONObject out = new JSONObject();
        try {
            if (beforeBitmap == null || afterBitmap == null
                    || beforeBitmap.isRecycled() || afterBitmap.isRecycled()
                    || targetRow < 0 || targetRow >= GRID_ROWS
                    || targetCol < 0 || targetCol >= GRID_COLS
                    || beforeBitmap.getWidth() != afterBitmap.getWidth()
                    || beforeBitmap.getHeight() != afterBitmap.getHeight()) {
                out.put("valid", false);
                out.put("reason", "invalid_bitmap_or_region_geometry");
                return out;
            }

            final int w = beforeBitmap.getWidth(), h = beforeBitmap.getHeight();
            final int sw = w >= h ? SAMPLE_LONG_SIDE : Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * w / (double)h));
            final int sh = w >= h ? Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * h / (double)w)) : SAMPLE_LONG_SIDE;
            final int capacity = sw * sh;
            int[] beforeCrValues = new int[capacity];
            int[] afterCrValues = new int[capacity];
            int n = 0;
            double beforeCrSum = 0.0, afterCrSum = 0.0;
            double beforeYSum = 0.0, afterYSum = 0.0;
            int beforeGreen = 0, afterGreen = 0;

            for (int sy = 0; sy < sh; sy++) {
                int row = Math.min(GRID_ROWS - 1, (sy * GRID_ROWS) / sh);
                if (row != targetRow) continue;
                int py = Math.min(h - 1, (int)(((2L * sy + 1L) * h) / (2L * sh)));
                for (int sx = 0; sx < sw; sx++) {
                    int col = Math.min(GRID_COLS - 1, (sx * GRID_COLS) / sw);
                    if (col != targetCol) continue;
                    int px = Math.min(w - 1, (int)(((2L * sx + 1L) * w) / (2L * sw)));

                    int bp = beforeBitmap.getPixel(px, py);
                    int br = (bp >>> 16) & 255;
                    int bg = (bp >>> 8) & 255;
                    int bb = bp & 255;
                    int by = (4899 * br + 9617 * bg + 1868 * bb) >> 14;
                    int bcb = (-2765 * br - 5427 * bg + 8192 * bb) >> 14;
                    int bcr = (8192 * br - 6860 * bg - 1332 * bb) >> 14;
                    if (by < LOCAL_Y_MIN || by > LOCAL_Y_MAX) continue;
                    if (Math.abs(bcb) > LOCAL_ABS_CB_MAX || Math.abs(bcr) > LOCAL_ABS_CR_MAX) continue;

                    int ap = afterBitmap.getPixel(px, py);
                    int ar = (ap >>> 16) & 255;
                    int ag = (ap >>> 8) & 255;
                    int ab = ap & 255;
                    int ay = (4899 * ar + 9617 * ag + 1868 * ab) >> 14;
                    int acr = (8192 * ar - 6860 * ag - 1332 * ab) >> 14;

                    beforeCrValues[n] = bcr;
                    afterCrValues[n] = acr;
                    beforeCrSum += bcr;
                    afterCrSum += acr;
                    beforeYSum += by;
                    afterYSum += ay;
                    if (bcr <= -3) beforeGreen++;
                    if (acr <= -3) afterGreen++;
                    n++;
                }
            }

            out.put("valid", n > 0);
            out.put("sampleCount", n);
            out.put("row", targetRow);
            out.put("column", targetCol);
            out.put("samplePolicy", "coordinates_selected_once_from_before_bitmap_local_neutral_mask_then_reused_after_rerender");
            if (n <= 0) return out;

            Arrays.sort(beforeCrValues, 0, n);
            Arrays.sort(afterCrValues, 0, n);
            double beforeMeanCr = beforeCrSum / n;
            double afterMeanCr = afterCrSum / n;
            double beforeMeanY = beforeYSum / n;
            double afterMeanY = afterYSum / n;
            out.put("beforeMeanCr", beforeMeanCr);
            out.put("afterMeanCr", afterMeanCr);
            out.put("meanCrImprovement", afterMeanCr - beforeMeanCr);
            out.put("beforeMedianCr", quantileSorted(beforeCrValues, n, 0.50));
            out.put("afterMedianCr", quantileSorted(afterCrValues, n, 0.50));
            out.put("beforeMeanY", beforeMeanY);
            out.put("afterMeanY", afterMeanY);
            out.put("meanYDelta", afterMeanY - beforeMeanY);
            out.put("beforeGreenFractionCrLEMinus3", beforeGreen / (double)n);
            out.put("afterGreenFractionCrLEMinus3", afterGreen / (double)n);
        } catch (Throwable t) {
            try { out.put("valid", false); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

'''
helper = helper[:start] + new_accept + helper[end:]
write(helper_rel, helper)

call_old = 'boolean accepted = M9ChromaExposure1AController.acceptCandidate(chromaDecision, afterChroma);'
call_new = 'boolean accepted = M9ChromaExposure1AController.acceptCandidate(bitmap, chromaCandidate, chromaDecision, afterChroma);'
if call_old not in renderer:
    raise SystemExit('CHROMAEXPOSURE1C renderer acceptCandidate call anchor missing')
renderer = renderer.replace(call_old, call_new, 1)

for old, new in [
    ('chromaExposure1BRequestedNegativeCrCompression', 'chromaExposure1CRequestedNegativeCrCompression'),
    ('chromaExposure1BEffectiveNegativeCrGain', 'chromaExposure1CEffectiveNegativeCrGain'),
    ('out.diagnostics.put("chromaExposure1B", chromaDecision);', 'out.diagnostics.put("chromaExposure1C", chromaDecision);'),
    ('CHROMAEXPOSURE1B_LOCALNEUTRAL1A: global-or-local neutral detection on the exposure-settled JPEG candidate.',
     'CHROMAEXPOSURE1C_ARBITRATION1A_FROZENSAMPLES1A: stronger-local arbitration and fixed-sample candidate validation.'),
]:
    if old not in renderer:
        raise SystemExit('CHROMAEXPOSURE1C renderer diagnostics anchor missing: ' + old)
    renderer = renderer.replace(old, new, 1)
write(renderer_rel, renderer)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit(f'CHROMAEXPOSURE1C frozen-source violation: {rel} changed')

print('Applied M9 CHROMAEXPOSURE1C ARBITRATION1A FROZENSAMPLES1A')
print(' - LOCAL overrides a marginal GLOBAL gate when its recommended correction is >=0.01 stronger')
print(' - equal-strength/global-dominant cases retain GREEN_GLOBAL_NEUTRAL')
print(' - LOCAL acceptance freezes neutral sample coordinates on the before bitmap and reuses them after rerender')
print(' - local Y/Cr/green-fraction acceptance therefore compares identical pixels instead of a reclassified sample set')
print(' - correction caps, capture, TC20, EDGE, DNG, native kernel/ABI, H25/HSM, SAT3 and curve02 remain frozen')
