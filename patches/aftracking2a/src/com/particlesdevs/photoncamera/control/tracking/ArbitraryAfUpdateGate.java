package com.particlesdevs.photoncamera.control.tracking;

/**
 * Limits redundant Camera2 AF-region submissions for an opt-in arbitrary
 * visual-patch tracker. The tracker, not this class, proves target identity.
 *
 * Each TrackingFocus handle owns one gate. A new tap, lens or camera session
 * must create a new handle; no camera state or image data is retained here.
 * This policy never submits AF triggers or changes AE/AWB regions.
 */
public final class ArbitraryAfUpdateGate {
    public static final long MIN_UPDATE_MS = 90L;
    public static final long NORMAL_UPDATE_MS = 180L;
    private static final float FAST_MOVE_FRACTION = .40f;
    private static final float DEADBAND_FRACTION = .09f;
    private boolean hasSubmitted;
    private long lastAtMs;
    private int lastX, lastY, lastW, lastH;

    /** Must be called on the owning camera handler; returns true only for an update worth submitting. */
    public boolean shouldSubmit(long nowMs, int x, int y, int width, int height) {
        if (nowMs < 0 || x < 0 || y < 0 || width <= 0 || height <= 0) return false;
        if (!hasSubmitted) {
            remember(nowMs, x, y, width, height);
            return true;
        }
        if (nowMs < lastAtMs) return false; // outdated callback from the same session
        long sinceMs = nowMs - lastAtMs;
        if (sinceMs < MIN_UPDATE_MS) return false;

        boolean resized = width != lastW || height != lastH;
        long dx = (long) x - lastX, dy = (long) y - lastY;
        double displacement = Math.hypot(dx, dy);
        float focusSize = Math.min(Math.min(width, height), Math.min(lastW, lastH));
        double deadband = Math.max(4.0, focusSize * DEADBAND_FRACTION);
        if (!resized && displacement < deadband) return false;
        if (!resized && sinceMs < NORMAL_UPDATE_MS
                && displacement < focusSize * FAST_MOVE_FRACTION) return false;

        remember(nowMs, x, y, width, height);
        return true;
    }

    private void remember(long nowMs, int x, int y, int width, int height) {
        hasSubmitted = true;
        lastAtMs = nowMs;
        lastX = x;
        lastY = y;
        lastW = width;
        lastH = height;
    }
}
