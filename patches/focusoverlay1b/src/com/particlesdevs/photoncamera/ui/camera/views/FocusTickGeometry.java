package com.particlesdevs.photoncamera.ui.camera.views;

/**
 * Presentation-only corner coordinates in the existing overlay-view pixel domain.
 * The AF target/region is never moved or resized by this class.
 *
 * Writes eight unconnected line segments (four right-angle corners) into the
 * caller-owned 32-float buffer. Does not allocate on the viewfinder draw path.
 */
public final class FocusTickGeometry {
    private FocusTickGeometry() { }

    private static boolean finite(float v) {
        return !Float.isNaN(v) && !Float.isInfinite(v);
    }

    private static void line(float[] out, int offset,
                             float x0, float y0, float x1, float y1) {
        out[offset] = x0; out[offset + 1] = y0;
        out[offset + 2] = x1; out[offset + 3] = y1;
    }

    public static boolean populate(float x, float y, float halfX, float halfY,
                                   float width, float height, float density,
                                   float[] out) {
        if (out == null || out.length < 32) throw new IllegalArgumentException("32-float buffer required");
        if (!finite(x) || !finite(y) || !finite(halfX) || !finite(halfY)
                || !finite(width) || !finite(height) || !finite(density)
                || halfX < 0f || halfY < 0f || density <= 0f
                || width <= 0f || height <= 0f) return false;

        // 20 dp visible minimum only; Camera2 AF region remains caller-owned.
        float radiusX = Math.max(halfX, 10f * density);
        float radiusY = Math.max(halfY, 10f * density);
        float margin = 1.75f * density;
        float left = Math.max(margin, x - radiusX);
        float top = Math.max(margin, y - radiusY);
        float right = Math.min(width - margin, x + radiusX);
        float bottom = Math.min(height - margin, y + radiusY);
        float shortSide = Math.min(right - left, bottom - top);
        if (shortSide < 4f * density) return false;

        // Balanced Extended: 22% nominal, 6–11 dp, safely below half-side.
        float leg = Math.min(11f * density, Math.max(6f * density, .22f * shortSide));
        leg = Math.min(leg, .43f * shortSide);

        // TOP LEFT: horizontal and vertical.
        line(out,  0, left, top, left + leg, top);
        line(out,  4, left, top, left, top + leg);
        // TOP RIGHT.
        line(out,  8, right - leg, top, right, top);
        line(out, 12, right, top, right, top + leg);
        // BOTTOM LEFT.
        line(out, 16, left, bottom, left + leg, bottom);
        line(out, 20, left, bottom - leg, left, bottom);
        // BOTTOM RIGHT.
        line(out, 24, right - leg, bottom, right, bottom);
        line(out, 28, right, bottom - leg, right, bottom);
        return true;
    }

    /**
     * Eye AF is visually compact even when the Camera2 AF region is broad.
     * These are DISPLAY half-extents, not Camera2 metering-region dimensions.
     * The shared tick renderer still applies its 10dp visibility minimum.
     */
    public static float eyeDisplayHalfWidth(float afHalfWidthPx, float density) {
        if (!finite(afHalfWidthPx) || afHalfWidthPx < 0f
                || !finite(density) || density <= 0f) return 0f;
        return Math.min(afHalfWidthPx, 17f * density);
    }

    public static float eyeDisplayHalfHeight(float afHalfHeightPx, float density) {
        if (!finite(afHalfHeightPx) || afHalfHeightPx < 0f
                || !finite(density) || density <= 0f) return 0f;
        return Math.min(afHalfHeightPx, 13f * density);
    }
}
