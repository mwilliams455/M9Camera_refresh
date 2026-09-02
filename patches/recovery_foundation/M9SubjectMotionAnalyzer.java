package com.particlesdevs.photoncamera.m9;

import android.media.Image;

import org.json.JSONObject;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Lightweight semantic-free preview subject-motion diagnostic.
 *
 * v0.5.3 refinements after the first real movement test:
 *  - 96x72 luma analysis instead of 64x48
 *  - +/-5-pixel block search instead of +/-3
 *  - block-match confidence and valid-motion-block diagnostics
 *  - explicit reliability flag for the image-motion estimate
 *  - captureMotionScore uses the recent short-window peak as well as smoothing
 *
 * v0.6 note: the analyzer itself still only measures motion. M9ModernExposurePolicy
 * may consume captureMotionScore to adjust shutter/ISO split.
 *
 * v0.7H LUMA1: diagnostics only. The same 96x72 Y plane is also summarized for
 * backlit-exposure forensics.
 *
 * v0.7L LUMA2.3-SPATIAL1: diagnostic-only spatial instrumentation. The latest
 * 96x72 luma frame is additionally summarized in a camera-rotation-aware 3x3
 * display-space grid plus display-space horizontal/vertical thirds. These values
 * are JSON-only and do not feed Photon, M9Modern, LUMA2.2 scoring, or rendering.
 */
public final class M9SubjectMotionAnalyzer {
    private static final int W = 96;
    private static final int H = 72;
    private static final int BLOCK = 8;
    private static final int SEARCH = 5;
    private static final float MOVING_THRESHOLD = 1.0f;
    private static final float TEXTURE_THRESHOLD = 5.0f;
    private static final double MATCH_CONFIDENCE_THRESHOLD = 0.025;

    private static byte[] previous;
    private static long previousTimestampNs;
    private static long firstTimestampNs;
    private static long lastTimestampNs;
    private static long inputFrames;
    private static long framesUsed;
    private static long skippedFrames;

    private static double globalMotionX;
    private static double globalMotionY;
    private static double globalMotionMagnitude;
    private static double residualMedian;
    private static double residualP90;
    private static double movingBlockFraction;
    private static double textureConfidence;
    private static double blockMatchConfidence;
    private static double validMotionBlockFraction;
    private static double validMatchFraction;
    private static boolean motionEstimateReliable;
    private static double instantaneousScore;
    private static double smoothedScore;
    private static double recentPeakScore;
    private static double captureMotionScore;

    // M9 v0.7H LUMA1 preview-scene diagnostics. Raw Y-plane code values only.
    private static long lumaFramesAnalyzed;
    private static double lumaMean;
    private static double lumaQ10;
    private static double lumaQ25;
    private static double lumaMedian;
    private static double lumaQ75;
    private static double lumaQ90;
    private static double lumaQ95;
    private static double lumaQ99;
    private static double lumaDark32;
    private static double lumaDark48;
    private static double lumaDark64;
    private static double lumaBright192;
    private static double lumaBright224;
    private static double lumaBright240;
    private static double centerMean;
    private static double centerMedian;
    private static double centerQ75;
    private static double centerQ90;
    private static double centerDark48;
    private static double centerBright224;
    private static double topThirdMean;
    private static double topThirdMedian;
    private static double middleThirdMean;
    private static double middleThirdMedian;
    private static double bottomThirdMean;
    private static double bottomThirdMedian;
    private static double emaMedian;
    private static double emaQ90;
    private static double emaQ95;
    private static double emaQ99;
    private static double emaCenterMedian;
    private static byte[] latestLumaFrame;

    private M9SubjectMotionAnalyzer() {}

    public static synchronized void reset() {
        previous = null;
        previousTimestampNs = 0;
        firstTimestampNs = 0;
        lastTimestampNs = 0;
        inputFrames = 0;
        framesUsed = 0;
        skippedFrames = 0;
        globalMotionX = 0;
        globalMotionY = 0;
        globalMotionMagnitude = 0;
        residualMedian = 0;
        residualP90 = 0;
        movingBlockFraction = 0;
        textureConfidence = 0;
        blockMatchConfidence = 0;
        validMotionBlockFraction = 0;
        validMatchFraction = 0;
        motionEstimateReliable = false;
        instantaneousScore = 0;
        smoothedScore = 0;
        recentPeakScore = 0;
        captureMotionScore = 0;

        lumaFramesAnalyzed = 0;
        lumaMean = lumaQ10 = lumaQ25 = lumaMedian = lumaQ75 = lumaQ90 = lumaQ95 = lumaQ99 = 0;
        lumaDark32 = lumaDark48 = lumaDark64 = 0;
        lumaBright192 = lumaBright224 = lumaBright240 = 0;
        centerMean = centerMedian = centerQ75 = centerQ90 = 0;
        centerDark48 = centerBright224 = 0;
        topThirdMean = topThirdMedian = middleThirdMean = middleThirdMedian = 0;
        bottomThirdMean = bottomThirdMedian = 0;
        emaMedian = emaQ90 = emaQ95 = emaQ99 = emaCenterMedian = 0;
        latestLumaFrame = null;
    }

    public static synchronized void onImage(Image image) {
        if (image == null || image.getPlanes() == null || image.getPlanes().length == 0) return;
        inputFrames++;

        // Still analyze every other delivered frame. The larger grid/search window
        // costs more CPU, so this keeps the diagnostic stream lightweight.
        if ((inputFrames & 1L) == 0L) {
            skippedFrames++;
            return;
        }

        byte[] current = downsampleY(image);
        if (current == null) {
            skippedFrames++;
            return;
        }

        // Diagnostic-only exposure scene summary. No feedback path in LUMA1.
        updatePreviewLuma(current);

        long ts = image.getTimestamp();
        if (firstTimestampNs == 0) firstTimestampNs = ts;
        lastTimestampNs = ts;

        if (previous == null) {
            previous = current;
            previousTimestampNs = ts;
            return;
        }

        List<BlockVector> texturedVectors = new ArrayList<>();
        List<BlockVector> validVectors = new ArrayList<>();
        int candidateBlocks = 0;
        double confidenceSum = 0.0;

        for (int by = BLOCK; by + BLOCK < H; by += BLOCK) {
            for (int bx = BLOCK; bx + BLOCK < W; bx += BLOCK) {
                candidateBlocks++;
                float texture = textureScore(current, bx, by);
                if (texture < TEXTURE_THRESHOLD) continue;
                BlockVector v = bestVector(previous, current, bx, by);
                texturedVectors.add(v);
                confidenceSum += v.confidence;
                if (v.confidence >= MATCH_CONFIDENCE_THRESHOLD) validVectors.add(v);
            }
        }

        textureConfidence = candidateBlocks > 0
                ? texturedVectors.size() / (double) candidateBlocks : 0.0;
        blockMatchConfidence = texturedVectors.isEmpty()
                ? 0.0 : confidenceSum / texturedVectors.size();
        validMotionBlockFraction = candidateBlocks > 0
                ? validVectors.size() / (double) candidateBlocks : 0.0;
        validMatchFraction = texturedVectors.isEmpty()
                ? 0.0 : validVectors.size() / (double) texturedVectors.size();

        // Prefer confident vectors. Fall back to all textured blocks for diagnostics
        // instead of pretending motion is zero, but mark that estimate unreliable.
        List<BlockVector> vectors = validVectors.size() >= 3 ? validVectors : texturedVectors;
        motionEstimateReliable = validVectors.size() >= 3
                && validMotionBlockFraction >= 0.08
                && blockMatchConfidence >= 0.025;

        if (vectors.size() >= 3) {
            List<Double> dxs = new ArrayList<>(vectors.size());
            List<Double> dys = new ArrayList<>(vectors.size());
            for (BlockVector v : vectors) {
                dxs.add((double) v.dx);
                dys.add((double) v.dy);
            }

            double gx = percentile(dxs, 0.50);
            double gy = percentile(dys, 0.50);

            List<Double> residuals = new ArrayList<>(vectors.size());
            int moving = 0;
            for (BlockVector v : vectors) {
                double r = Math.hypot(v.dx - gx, v.dy - gy);
                residuals.add(r);
                if (r >= MOVING_THRESHOLD) moving++;
            }

            globalMotionX = gx;
            globalMotionY = gy;
            globalMotionMagnitude = Math.hypot(gx, gy);
            residualMedian = percentile(residuals, 0.50);
            residualP90 = percentile(residuals, 0.90);
            movingBlockFraction = moving / (double) vectors.size();

            double p90Term = clamp01((residualP90 - 0.20) / 3.80);
            double movingTerm = clamp01(movingBlockFraction / 0.45);
            double textureWeight = 0.30 + 0.70 * clamp01(textureConfidence / 0.55);
            double matchWeight = 0.40 + 0.60 * clamp01(blockMatchConfidence / 0.12);
            instantaneousScore = clamp01((0.65 * p90Term + 0.35 * movingTerm)
                    * textureWeight * matchWeight);

            smoothedScore = framesUsed == 0
                    ? instantaneousScore
                    : (0.72 * smoothedScore + 0.28 * instantaneousScore);

            // A short-memory peak is intentionally retained so one quiet frame pair
            // at shutter time does not erase motion observed immediately beforehand.
            recentPeakScore = Math.max(instantaneousScore, recentPeakScore * 0.95);
            captureMotionScore = Math.max(smoothedScore, recentPeakScore * 0.90);
            framesUsed++;
        } else {
            globalMotionMagnitude = Math.hypot(globalMotionX, globalMotionY);
            residualMedian = 0.0;
            residualP90 = 0.0;
            movingBlockFraction = 0.0;
            instantaneousScore = 0.0;
            smoothedScore *= 0.90;
            recentPeakScore *= 0.95;
            captureMotionScore = Math.max(smoothedScore, recentPeakScore * 0.90);
            motionEstimateReliable = false;
            skippedFrames++;
        }

        previous = current;
        previousTimestampNs = ts;
    }

    public static synchronized double getCaptureMotionScore() { return captureMotionScore; }
    public static synchronized double getRecentPeakScore() { return recentPeakScore; }
    public static synchronized long getFramesUsed() { return framesUsed; }
    public static synchronized boolean isMotionEstimateReliable() { return motionEstimateReliable; }

    public static synchronized JSONObject snapshotJson() {
        return snapshotJson(0);
    }

    public static synchronized JSONObject snapshotJson(int cameraRotationDegrees) {
        JSONObject o = new JSONObject();
        try {
            o.put("schema", "m9cam.subjectmotion.v3.luma1");
            o.put("analysisWidth", W);
            o.put("analysisHeight", H);
            o.put("blockSize", BLOCK);
            o.put("searchRadius", SEARCH);
            o.put("inputFrames", inputFrames);
            o.put("framesUsed", framesUsed);
            o.put("droppedFrames", skippedFrames);
            o.put("skippedFrames", skippedFrames);
            double seconds = (lastTimestampNs > firstTimestampNs)
                    ? (lastTimestampNs - firstTimestampNs) / 1.0e9 : 0.0;
            o.put("analysisFPS", seconds > 0.0 ? framesUsed / seconds : 0.0);
            o.put("globalMotionX", globalMotionX);
            o.put("globalMotionY", globalMotionY);
            o.put("globalMotionMagnitude", globalMotionMagnitude);
            o.put("residualMedian", residualMedian);
            o.put("residualP90", residualP90);
            o.put("movingBlockFraction", movingBlockFraction);
            o.put("textureConfidence", textureConfidence);
            o.put("blockMatchConfidence", blockMatchConfidence);
            o.put("validMotionBlockFraction", validMotionBlockFraction);
            o.put("validMatchFraction", validMatchFraction);
            o.put("motionEstimateReliable", motionEstimateReliable);
            o.put("instantaneousScore", instantaneousScore);
            o.put("smoothedScore", smoothedScore);
            o.put("recentPeakScore", recentPeakScore);
            o.put("captureMotionScore", captureMotionScore);
            o.put("exposurePolicyModified", M9Config.isM9Modern());
            o.put("previewLuma", previewLumaSnapshotJson(cameraRotationDegrees));
        } catch (Exception ignored) {
        }
        return o;
    }

    private static byte[] downsampleY(Image image) {
        try {
            Image.Plane p = image.getPlanes()[0];
            ByteBuffer b = p.getBuffer();
            int rowStride = p.getRowStride();
            int pixelStride = p.getPixelStride();
            int srcW = image.getWidth();
            int srcH = image.getHeight();
            byte[] out = new byte[W * H];
            for (int y = 0; y < H; y++) {
                int sy = Math.min(srcH - 1, (int) (((long) y * srcH) / H));
                for (int x = 0; x < W; x++) {
                    int sx = Math.min(srcW - 1, (int) (((long) x * srcW) / W));
                    int index = sy * rowStride + sx * pixelStride;
                    out[y * W + x] = b.get(index);
                }
            }
            return out;
        } catch (Exception e) {
            return null;
        }
    }

    private static void updatePreviewLuma(byte[] img) {
        latestLumaFrame = img;
        int[] global = histogram(img, 0, 0, W, H);
        int cx0 = W / 4;
        int cx1 = W - cx0;
        int cy0 = H / 4;
        int cy1 = H - cy0;
        int[] center = histogram(img, cx0, cy0, cx1, cy1);
        int third = H / 3;
        int[] top = histogram(img, 0, 0, W, third);
        int[] middle = histogram(img, 0, third, W, 2 * third);
        int[] bottom = histogram(img, 0, 2 * third, W, H);

        int globalN = W * H;
        int centerN = (cx1 - cx0) * (cy1 - cy0);
        int topN = W * third;
        int middleN = W * third;
        int bottomN = W * (H - 2 * third);

        lumaMean = histogramMean(global, globalN);
        lumaQ10 = histogramPercentile(global, globalN, 0.10);
        lumaQ25 = histogramPercentile(global, globalN, 0.25);
        lumaMedian = histogramPercentile(global, globalN, 0.50);
        lumaQ75 = histogramPercentile(global, globalN, 0.75);
        lumaQ90 = histogramPercentile(global, globalN, 0.90);
        lumaQ95 = histogramPercentile(global, globalN, 0.95);
        lumaQ99 = histogramPercentile(global, globalN, 0.99);
        lumaDark32 = histogramFractionAtMost(global, globalN, 32);
        lumaDark48 = histogramFractionAtMost(global, globalN, 48);
        lumaDark64 = histogramFractionAtMost(global, globalN, 64);
        lumaBright192 = histogramFractionAtLeast(global, globalN, 192);
        lumaBright224 = histogramFractionAtLeast(global, globalN, 224);
        lumaBright240 = histogramFractionAtLeast(global, globalN, 240);

        centerMean = histogramMean(center, centerN);
        centerMedian = histogramPercentile(center, centerN, 0.50);
        centerQ75 = histogramPercentile(center, centerN, 0.75);
        centerQ90 = histogramPercentile(center, centerN, 0.90);
        centerDark48 = histogramFractionAtMost(center, centerN, 48);
        centerBright224 = histogramFractionAtLeast(center, centerN, 224);

        topThirdMean = histogramMean(top, topN);
        topThirdMedian = histogramPercentile(top, topN, 0.50);
        middleThirdMean = histogramMean(middle, middleN);
        middleThirdMedian = histogramPercentile(middle, middleN, 0.50);
        bottomThirdMean = histogramMean(bottom, bottomN);
        bottomThirdMedian = histogramPercentile(bottom, bottomN, 0.50);

        final double alpha = 0.25;
        if (lumaFramesAnalyzed == 0) {
            emaMedian = lumaMedian;
            emaQ90 = lumaQ90;
            emaQ95 = lumaQ95;
            emaQ99 = lumaQ99;
            emaCenterMedian = centerMedian;
        } else {
            emaMedian = ema(emaMedian, lumaMedian, alpha);
            emaQ90 = ema(emaQ90, lumaQ90, alpha);
            emaQ95 = ema(emaQ95, lumaQ95, alpha);
            emaQ99 = ema(emaQ99, lumaQ99, alpha);
            emaCenterMedian = ema(emaCenterMedian, centerMedian, alpha);
        }
        lumaFramesAnalyzed++;
    }

    private static JSONObject previewLumaSnapshotJson(int cameraRotationDegrees) {
        JSONObject o = new JSONObject();
        try {
            o.put("schema", "m9cam.previewluma.v2.spatial1");
            o.put("source", "same_96x72_yuv420_y_plane_as_motion_analyzer");
            o.put("rangeNote", "raw 8-bit Y-plane code values; no studio/full-range remap");
            o.put("framesAnalyzed", lumaFramesAnalyzed);

            JSONObject global = new JSONObject();
            global.put("mean", lumaMean);
            global.put("q10", lumaQ10);
            global.put("q25", lumaQ25);
            global.put("median", lumaMedian);
            global.put("q75", lumaQ75);
            global.put("q90", lumaQ90);
            global.put("q95", lumaQ95);
            global.put("q99", lumaQ99);
            global.put("darkFractionLE32", lumaDark32);
            global.put("darkFractionLE48", lumaDark48);
            global.put("darkFractionLE64", lumaDark64);
            global.put("brightFractionGE192", lumaBright192);
            global.put("brightFractionGE224", lumaBright224);
            global.put("brightFractionGE240", lumaBright240);
            global.put("q95MinusMedian", lumaQ95 - lumaMedian);
            global.put("q99MinusMedian", lumaQ99 - lumaMedian);
            o.put("global", global);

            JSONObject center = new JSONObject();
            center.put("region", "center_50_percent_width_height");
            center.put("mean", centerMean);
            center.put("median", centerMedian);
            center.put("q75", centerQ75);
            center.put("q90", centerQ90);
            center.put("darkFractionLE48", centerDark48);
            center.put("brightFractionGE224", centerBright224);
            center.put("medianMinusGlobalMedian", centerMedian - lumaMedian);
            o.put("center50", center);

            JSONObject vertical = new JSONObject();
            vertical.put("topMean", topThirdMean);
            vertical.put("topMedian", topThirdMedian);
            vertical.put("middleMean", middleThirdMean);
            vertical.put("middleMedian", middleThirdMedian);
            vertical.put("bottomMean", bottomThirdMean);
            vertical.put("bottomMedian", bottomThirdMedian);
            vertical.put("topMinusBottomMedian", topThirdMedian - bottomThirdMedian);
            o.put("verticalThirds", vertical);

            o.put("spatial3x3", spatial3x3SnapshotJson(latestLumaFrame, cameraRotationDegrees));

            JSONObject smoothed = new JSONObject();
            smoothed.put("alpha", 0.25);
            smoothed.put("median", emaMedian);
            smoothed.put("q90", emaQ90);
            smoothed.put("q95", emaQ95);
            smoothed.put("q99", emaQ99);
            smoothed.put("centerMedian", emaCenterMedian);
            smoothed.put("q95MinusMedian", emaQ95 - emaMedian);
            smoothed.put("q99MinusMedian", emaQ99 - emaMedian);
            o.put("ema", smoothed);
        } catch (Exception ignored) {
        }
        return o;
    }

    private static JSONObject spatial3x3SnapshotJson(byte[] sensorFrame, int cameraRotationDegrees) {
        JSONObject out = new JSONObject();
        try {
            int rotation = normalizeRotation(cameraRotationDegrees);
            OrientedLuma oriented = orientForDisplay(sensorFrame, rotation);
            out.put("schema", "m9cam.previewluma.spatial3x3.v1");
            out.put("orientationSpace", "display_after_cameraRotation");
            out.put("rotationAppliedDegrees", rotation);
            out.put("sourceWidth", W);
            out.put("sourceHeight", H);
            out.put("displayWidth", oriented.width);
            out.put("displayHeight", oriented.height);
            out.put("rows", 3);
            out.put("columns", 3);
            out.put("feedbackEnabled", true);
            out.put("decisionUse", "live_luma2p4_spatial2_feedback");
            if (oriented.data == null) {
                out.put("valid", false);
                return out;
            }
            out.put("valid", true);

            JSONObject tiles = new JSONObject();
            String[] rowNames = {"top", "middle", "bottom"};
            String[] colNames = {"left", "center", "right"};
            for (int row = 0; row < 3; row++) {
                int y0 = row * oriented.height / 3;
                int y1 = (row + 1) * oriented.height / 3;
                for (int col = 0; col < 3; col++) {
                    int x0 = col * oriented.width / 3;
                    int x1 = (col + 1) * oriented.width / 3;
                    tiles.put(rowNames[row] + capitalize(colNames[col]),
                            regionMetrics(oriented.data, oriented.width, oriented.height, x0, y0, x1, y1));
                }
            }
            out.put("tiles", tiles);

            JSONObject h = new JSONObject();
            JSONObject top = regionMetrics(oriented.data, oriented.width, oriented.height,
                    0, 0, oriented.width, oriented.height / 3);
            JSONObject middle = regionMetrics(oriented.data, oriented.width, oriented.height,
                    0, oriented.height / 3, oriented.width, 2 * oriented.height / 3);
            JSONObject bottom = regionMetrics(oriented.data, oriented.width, oriented.height,
                    0, 2 * oriented.height / 3, oriented.width, oriented.height);
            h.put("top", top);
            h.put("middle", middle);
            h.put("bottom", bottom);
            h.put("topMinusBottomMedian", top.optDouble("median", 0.0) - bottom.optDouble("median", 0.0));
            h.put("topMinusMiddleMedian", top.optDouble("median", 0.0) - middle.optDouble("median", 0.0));
            out.put("displayHorizontalThirds", h);

            JSONObject v = new JSONObject();
            JSONObject left = regionMetrics(oriented.data, oriented.width, oriented.height,
                    0, 0, oriented.width / 3, oriented.height);
            JSONObject center = regionMetrics(oriented.data, oriented.width, oriented.height,
                    oriented.width / 3, 0, 2 * oriented.width / 3, oriented.height);
            JSONObject right = regionMetrics(oriented.data, oriented.width, oriented.height,
                    2 * oriented.width / 3, 0, oriented.width, oriented.height);
            v.put("left", left);
            v.put("center", center);
            v.put("right", right);
            v.put("leftMinusRightMedian", left.optDouble("median", 0.0) - right.optDouble("median", 0.0));
            out.put("displayVerticalThirds", v);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static JSONObject regionMetrics(byte[] img, int width, int height,
                                            int x0, int y0, int x1, int y1) {
        JSONObject o = new JSONObject();
        try {
            int[] hist = histogram(img, width, height, x0, y0, x1, y1);
            int count = Math.max(0, Math.min(width, x1) - Math.max(0, x0))
                    * Math.max(0, Math.min(height, y1) - Math.max(0, y0));
            o.put("mean", histogramMean(hist, count));
            o.put("median", histogramPercentile(hist, count, 0.50));
            o.put("q75", histogramPercentile(hist, count, 0.75));
            o.put("q90", histogramPercentile(hist, count, 0.90));
            o.put("q95", histogramPercentile(hist, count, 0.95));
            o.put("darkFractionLE48", histogramFractionAtMost(hist, count, 48));
            o.put("darkFractionLE64", histogramFractionAtMost(hist, count, 64));
            o.put("brightFractionGE192", histogramFractionAtLeast(hist, count, 192));
            o.put("brightFractionGE224", histogramFractionAtLeast(hist, count, 224));
        } catch (Exception ignored) {
        }
        return o;
    }

    private static int[] histogram(byte[] img, int width, int height,
                                   int x0, int y0, int x1, int y1) {
        int[] hist = new int[256];
        if (img == null || width <= 0 || height <= 0) return hist;
        int xa = Math.max(0, x0);
        int xb = Math.min(width, x1);
        int ya = Math.max(0, y0);
        int yb = Math.min(height, y1);
        for (int y = ya; y < yb; y++) {
            int row = y * width;
            for (int x = xa; x < xb; x++) hist[u(img[row + x])]++;
        }
        return hist;
    }

    private static OrientedLuma orientForDisplay(byte[] src, int rotation) {
        if (src == null || src.length != W * H) return new OrientedLuma(null, W, H);
        if (rotation == 0) return new OrientedLuma(src.clone(), W, H);
        if (rotation == 180) {
            byte[] out = new byte[W * H];
            for (int y = 0; y < H; y++) {
                for (int x = 0; x < W; x++) {
                    out[(H - 1 - y) * W + (W - 1 - x)] = src[y * W + x];
                }
            }
            return new OrientedLuma(out, W, H);
        }
        int dw = H;
        int dh = W;
        byte[] out = new byte[dw * dh];
        if (rotation == 90) {
            for (int y = 0; y < H; y++) {
                for (int x = 0; x < W; x++) {
                    int dx = H - 1 - y;
                    int dy = x;
                    out[dy * dw + dx] = src[y * W + x];
                }
            }
        } else { // 270 degrees
            for (int y = 0; y < H; y++) {
                for (int x = 0; x < W; x++) {
                    int dx = y;
                    int dy = W - 1 - x;
                    out[dy * dw + dx] = src[y * W + x];
                }
            }
        }
        return new OrientedLuma(out, dw, dh);
    }

    private static int normalizeRotation(int cameraRotationDegrees) {
        int r = cameraRotationDegrees % 360;
        if (r < 0) r += 360;
        if (r < 45 || r >= 315) return 0;
        if (r < 135) return 90;
        if (r < 225) return 180;
        return 270;
    }

    private static String capitalize(String s) {
        if (s == null || s.isEmpty()) return "";
        return Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }

    private static final class OrientedLuma {
        final byte[] data;
        final int width;
        final int height;
        OrientedLuma(byte[] data, int width, int height) {
            this.data = data;
            this.width = width;
            this.height = height;
        }
    }

    private static int[] histogram(byte[] img, int x0, int y0, int x1, int y1) {
        int[] hist = new int[256];
        int xa = Math.max(0, x0);
        int xb = Math.min(W, x1);
        int ya = Math.max(0, y0);
        int yb = Math.min(H, y1);
        for (int y = ya; y < yb; y++) {
            int row = y * W;
            for (int x = xa; x < xb; x++) hist[u(img[row + x])]++;
        }
        return hist;
    }

    private static double histogramMean(int[] hist, int count) {
        if (count <= 0) return 0.0;
        long sum = 0;
        for (int i = 0; i < hist.length; i++) sum += (long) i * hist[i];
        return sum / (double) count;
    }

    private static double histogramPercentile(int[] hist, int count, double q) {
        if (count <= 0) return 0.0;
        int target = (int) Math.floor(Math.max(0.0, Math.min(1.0, q)) * (count - 1));
        int cumulative = 0;
        for (int i = 0; i < hist.length; i++) {
            cumulative += hist[i];
            if (cumulative > target) return i;
        }
        return 255.0;
    }

    private static double histogramFractionAtMost(int[] hist, int count, int threshold) {
        if (count <= 0) return 0.0;
        int n = 0;
        int end = Math.min(255, Math.max(0, threshold));
        for (int i = 0; i <= end; i++) n += hist[i];
        return n / (double) count;
    }

    private static double histogramFractionAtLeast(int[] hist, int count, int threshold) {
        if (count <= 0) return 0.0;
        int n = 0;
        int start = Math.min(255, Math.max(0, threshold));
        for (int i = start; i < hist.length; i++) n += hist[i];
        return n / (double) count;
    }

    private static double ema(double previousValue, double currentValue, double alpha) {
        return previousValue * (1.0 - alpha) + currentValue * alpha;
    }

    private static float textureScore(byte[] img, int bx, int by) {
        long sum = 0;
        int count = 0;
        for (int y = by; y < by + BLOCK - 1; y += 2) {
            for (int x = bx; x < bx + BLOCK - 1; x += 2) {
                int c = u(img[y * W + x]);
                sum += Math.abs(c - u(img[y * W + x + 1]));
                sum += Math.abs(c - u(img[(y + 1) * W + x]));
                count += 2;
            }
        }
        return count == 0 ? 0f : sum / (float) count;
    }

    private static BlockVector bestVector(byte[] prev, byte[] cur, int bx, int by) {
        long best = Long.MAX_VALUE;
        long second = Long.MAX_VALUE;
        int bestDx = 0;
        int bestDy = 0;

        for (int dy = -SEARCH; dy <= SEARCH; dy++) {
            for (int dx = -SEARCH; dx <= SEARCH; dx++) {
                long sad = 0;
                boolean invalid = false;
                for (int y = 1; y < BLOCK - 1 && !invalid; y++) {
                    int cy = by + y;
                    int py = cy + dy;
                    if (py < 0 || py >= H) {
                        invalid = true;
                        break;
                    }
                    for (int x = 1; x < BLOCK - 1; x++) {
                        int cx = bx + x;
                        int px = cx + dx;
                        if (px < 0 || px >= W) {
                            invalid = true;
                            break;
                        }
                        sad += Math.abs(u(cur[cy * W + cx]) - u(prev[py * W + px]));
                    }
                }
                if (invalid) continue;

                if (sad < best) {
                    second = best;
                    best = sad;
                    bestDx = dx;
                    bestDy = dy;
                } else if (sad < second) {
                    second = sad;
                }
            }
        }

        double confidence;
        if (best == Long.MAX_VALUE || second == Long.MAX_VALUE) {
            confidence = 0.0;
        } else {
            confidence = clamp01((second - best) / (double) (second + 1L));
        }
        return new BlockVector(bestDx, bestDy, confidence);
    }

    private static int u(byte b) { return b & 0xff; }

    private static double percentile(List<Double> values, double q) {
        if (values == null || values.isEmpty()) return 0.0;
        List<Double> c = new ArrayList<>(values);
        Collections.sort(c);
        double pos = q * (c.size() - 1);
        int lo = (int) Math.floor(pos);
        int hi = (int) Math.ceil(pos);
        if (lo == hi) return c.get(lo);
        double f = pos - lo;
        return c.get(lo) * (1.0 - f) + c.get(hi) * f;
    }

    private static double clamp01(double v) {
        return Math.max(0.0, Math.min(1.0, v));
    }

    private static final class BlockVector {
        final int dx;
        final int dy;
        final double confidence;

        BlockVector(int dx, int dy, double confidence) {
            this.dx = dx;
            this.dy = dy;
            this.confidence = confidence;
        }
    }
}
