package com.particlesdevs.photoncamera.control.tracking;

/**
 * M9Cam 3.06 — opt-in local textured-patch tracking with limited scale search
 * and conservative, time-bounded occlusion hold.
 *
 * This is NOT an object detector. The original selection template is never
 * rewritten from the running preview, preventing gradual visual identity drift.
 * Only high-confidence, temporally consistent local matches can end a hold.
 * During hold the caller MUST NOT move the Camera2 AF region.
 * No AF/AE/AWB requests or camera APIs exist in this class.
 */
public final class PatchTracker {
    public static final String REVISION = "FOCUSTRACK3A";
    private static final int HALF = 10, SIDE = 2 * HALF + 1;
    private static final int SEARCH = 22;
    private static final int MAX_CANDIDATES = 6500;
    private static final long MAX_FRAME_GAP_MS = 600;
    private static final long MAX_OCCLUSION_MS = 850;
    private static final float MIN_SCALE = .62f, MAX_SCALE = 1.7f;
    private static final float[] RELATIVE_SCALE = {.82f, 1.0f, 1.22f};
    private static final double TRACK_MIN = .76, TRACK_GAP = .08;
    private static final double RECOVER_MIN = .86, RECOVER_GAP = .115;
    private final float[] template = new float[SIDE * SIDE];
    private final int[] locX = new int[MAX_CANDIDATES], locY = new int[MAX_CANDIDATES];
    private final float[] locScale = new float[MAX_CANDIDATES];
    private final double[] locScore = new double[MAX_CANDIDATES];
    private int count, width, height, x, y;
    // One patch tracker runs on one serial worker; reuse luma storage to avoid GC churn.
    private int[] grayscaleScratch;
    private float scale = 1f;
    private boolean active, holding;
    private long lastFrameMs, lastGoodMs;
    private int recoveryHits, recoveryX, recoveryY;
    private float recoveryScale;

    public static final class Result {
        public final boolean tracking;
        public final boolean holding;
        public final float x, y, halfWidth, halfHeight, scale;
        public final double confidence;
        private Result(boolean tracking, boolean holding, int cx, int cy,
                       int w, int h, float scale, double confidence) {
            this.tracking = tracking;
            this.holding = holding;
            this.x = (cx + .5f) / Math.max(1, w);
            this.y = (cy + .5f) / Math.max(1, h);
            this.halfWidth = (HALF * scale + .5f) / Math.max(1, w);
            this.halfHeight = (HALF * scale + .5f) / Math.max(1, h);
            this.scale = scale;
            this.confidence = confidence;
        }
    }

    /** One selection sets the immutable reference; a weak/repeated target is rejected. */
    public Result select(int[] pixels, int w, int h, float u, float v, long now) {
        active = holding = false;
        width = w; height = h; scale = 1f; recoveryHits = 0;
        if (w <= SIDE + 2 || h <= SIDE + 2 || pixels == null ||
                pixels.length != w * h || !Float.isFinite(u) || !Float.isFinite(v) ||
                u < 0 || u >= 1 || v < 0 || v >= 1 || now < 0)
            return result(false, false, 0);
        x = (int)(u * w); y = (int)(v * h);
        if (!inside(x, y, 1f)) return result(false, false, 0);
        int[] gray = grayscale(pixels);
        double sum = 0, square = 0;
        int n = 0;
        for (int j = -HALF; j <= HALF; j++) for (int i = -HALF; i <= HALF; i++) {
            int value = gray[(y + j) * w + x + i];
            template[n++] = value;
            sum += value;
            square += value * value;
        }
        double mean = sum / n, variance = square / n - mean * mean;
        if (variance < 64) return result(false, false, 0);
        double norm = Math.sqrt(variance * n);
        for (int i = 0; i < n; i++) template[i] = (float)((template[i] - mean) / norm);
        active = true;
        lastFrameMs = Long.MIN_VALUE;
        lastGoodMs = now;
        return match(gray, now, false);
    }

    /** Distinct newer frames only. No stale frame can change target identity. */
    public Result update(int[] pixels, int w, int h, long now) {
        if (!active || pixels == null || w != width || h != height ||
                pixels.length != w * h || now < 0) return retire();
        if (now <= lastFrameMs) return result(false, true, 0); // no stale AF movement
        if (lastFrameMs != Long.MIN_VALUE && now - lastFrameMs > MAX_FRAME_GAP_MS)
            return retire();
        if (holding && now - lastGoodMs > MAX_OCCLUSION_MS) return retire();
        return match(grayscale(pixels), now, true);
    }

    private Result match(int[] gray, long now, boolean allowHold) {
        lastFrameMs = now;
        count = 0;
        // Full-resolution search for the stable accepted scale.
        float original = scale;
        int[][] offs = offsets(original);
        for (int dy = -SEARCH; dy <= SEARCH; dy++) for (int dx = -SEARCH; dx <= SEARCH; dx++)
            examine(gray, x + dx, y + dy, original, offs);
        int stableEnd = count;
        // Correlation can collapse at even a 1-pixel offset on a finely
        // textured subject. Search every centre for each additional scale,
        // rather than relying on coarse-grid peaks that can miss true matches.
        for (float factor : RELATIVE_SCALE) {
            if (factor == 1f) continue;
            float trial = clamp(original * factor, MIN_SCALE, MAX_SCALE);
            if (Math.abs(trial - original) < .01f) continue;
            offs = offsets(trial);
            for (int dy = -SEARCH; dy <= SEARCH; dy++)
                for (int dx = -SEARCH; dx <= SEARCH; dx++)
                    examine(gray, x + dx, y + dy, trial, offs);
        }
        int bestIndex = bestFrom(0, count);
        if (bestIndex < 0) return missing(now, allowHold, -2);
        int stableIndex = bestFrom(0, stableEnd);
        // Avoid scale pumping on tiny correlation differences; only change size
        // when an alternative substantially outperforms the current scale.
        if (stableIndex >= 0 && locScore[bestIndex] - locScore[stableIndex] < .045)
            bestIndex = stableIndex;
        double score = locScore[bestIndex];
        int bestX = locX[bestIndex], bestY = locY[bestIndex];
        float bestScale = locScale[bestIndex];
        double runner = -2;
        for (int n = 0; n < count; n++)
            if (Math.abs(bestX - locX[n]) > 4 || Math.abs(bestY - locY[n]) > 4)
                runner = Math.max(runner, locScore[n]);
        boolean edge = Math.abs(bestX - x) >= SEARCH - 1 || Math.abs(bestY - y) >= SEARCH - 1;
        boolean credible = !edge && score >= (holding ? RECOVER_MIN : TRACK_MIN)
                && score - runner >= (holding ? RECOVER_GAP : TRACK_GAP);
        if (!credible) return missing(now, allowHold, score);
        if (holding) {
            // Never seize the first patch that reappears; require two separate
            // coherent frames with high identity confidence and local motion.
            if (recoveryHits > 0 && Math.abs(bestX - recoveryX) <= 8
                    && Math.abs(bestY - recoveryY) <= 8
                    && Math.abs(bestScale - recoveryScale) <= .30f) {
                recoveryHits++;
            } else {
                recoveryHits = 1;
            }
            recoveryX = bestX; recoveryY = bestY; recoveryScale = bestScale;
            if (recoveryHits < 2) return result(false, true, score);
        }
        x = bestX; y = bestY; scale = bestScale;
        holding = false; recoveryHits = 0;
        lastGoodMs = now;
        return result(true, false, score);
    }

    private Result missing(long now, boolean allowHold, double score) {
        if (!allowHold || now - lastGoodMs > MAX_OCCLUSION_MS) return retire();
        holding = true;
        recoveryHits = 0;
        return result(false, true, score);
    }
    private Result retire() {
        active = holding = false;
        recoveryHits = 0;
        return result(false, false, 0);
    }
    private Result result(boolean tracking, boolean holding, double score) {
        return new Result(tracking, holding, x, y, width, height, scale, score);
    }

    private int bestFrom(int start, int end) {
        int at = -1;
        double value = -2;
        for (int i = start; i < end; i++) if (locScore[i] > value) {
            value = locScore[i]; at = i;
        }
        return at;
    }
    private void examine(int[] gray, int cx, int cy, float trial, int[][] offsets) {
        if (!inside(cx, cy, trial) || count == locScore.length) return;
        int[] ox = offsets[0], oy = offsets[1];
        double sum = 0, square = 0, dot = 0; int n = 0;
        for (int j = 0; j < SIDE; j++) {
            int row = (cy + oy[j]) * width + cx;
            for (int i = 0; i < SIDE; i++) {
                int value = gray[row + ox[i]];
                sum += value; square += value * value;
                dot += template[n++] * value;
            }
        }
        double energy = square - sum * sum / n;
        double correlation = energy < 64 * n ? -2 : dot / Math.sqrt(energy);
        locX[count] = cx; locY[count] = cy;
        locScale[count] = trial;
        locScore[count++] = correlation;
    }
    private static int[][] offsets(float scale) {
        int[] ox = new int[SIDE], oy = new int[SIDE];
        for (int i = 0; i < SIDE; i++) {
            ox[i] = Math.round((i - HALF) * scale);
            oy[i] = Math.round((i - HALF) * scale);
        }
        return new int[][]{ox,oy};
    }
    private boolean inside(int cx, int cy, float scale) {
        int radius = Math.round(HALF * scale);
        return cx >= radius && cy >= radius && cx + radius < width && cy + radius < height;
    }
    private int[] grayscale(int[] pixels) {
        if (grayscaleScratch == null || grayscaleScratch.length != pixels.length)
            grayscaleScratch = new int[pixels.length];
        int[] gray = grayscaleScratch;
        for (int i = 0; i < pixels.length; i++) {
            int argb = pixels[i];
            gray[i] = (77 * ((argb >> 16) & 255) + 150 * ((argb >> 8) & 255)
                    + 29 * (argb & 255)) >> 8;
        }
        return gray;
    }
    private static float clamp(float x, float lo, float hi) {
        return Math.max(lo, Math.min(hi, x));
    }
}
