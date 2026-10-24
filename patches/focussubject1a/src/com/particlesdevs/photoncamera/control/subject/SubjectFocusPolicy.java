package com.particlesdevs.photoncamera.control.subject;

import java.util.ArrayList;
import java.util.List;

/**
 * Camera-neutral target selection, intentionally independent of the image renderer,
 * AF request builder, and the ML inference library. Coordinates are normalized
 * in the currently displayed, upright preview [0, 1].
 *
 * Not itself an autofocus implementation: the camera owner must validate the
 * session and translate targets to a supported AF-region coordinate space.
 */
public final class SubjectFocusPolicy {
    public enum Kind { HUMAN_FACE, HUMAN_EYE }

    public static final class Face {
        public final int id;
        public final float left, top, right, bottom;
        public final float leftEyeX, leftEyeY, rightEyeX, rightEyeY;

        public Face(int id, float left, float top, float right, float bottom,
                    float leftEyeX, float leftEyeY, float rightEyeX, float rightEyeY) {
            this.id = id;
            this.left = left;
            this.top = top;
            this.right = right;
            this.bottom = bottom;
            this.leftEyeX = leftEyeX;
            this.leftEyeY = leftEyeY;
            this.rightEyeX = rightEyeX;
            this.rightEyeY = rightEyeY;
        }
        public boolean valid() {
            return finite(left) && finite(top) && finite(right) && finite(bottom)
                    && left >= 0f && top >= 0f && right <= 1f && bottom <= 1f
                    && right > left && bottom > top;
        }
        public boolean contains(float x, float y) {
            return x >= left && x <= right && y >= top && y <= bottom;
        }
        public float cx() { return (left + right) * .5f; }
        public float cy() { return (top + bottom) * .5f; }
    }

    public static final class Target {
        public final int id;
        public final Kind kind;
        public final float x, y;
        public final float regionWidth, regionHeight;
        public final long frameNs, sessionEpoch;
        public final boolean eyeLandmarkFound;
        private Target(int id, Kind kind, float x, float y, float rw, float rh,
                       long frameNs, long sessionEpoch, boolean found) {
            this.id=id; this.kind=kind; this.x=x; this.y=y;
            this.regionWidth=rw; this.regionHeight=rh;
            this.frameNs=frameNs; this.sessionEpoch=sessionEpoch;
            this.eyeLandmarkFound=found;
        }
    }

    // Frame age is a safety bound, not the cadence of the inference worker.
    public static final long MAX_FRAME_AGE_NS = 250_000_000L;
    public static final long LOST_GRACE_NS = 650_000_000L;

    private long epoch = Long.MIN_VALUE;
    private long latestFrameNs = Long.MIN_VALUE;
    private long missingSinceNs = Long.MIN_VALUE;
    private Integer selectedId;
    private boolean tapPinned = false;
    private float previousX = .5f, previousY = .5f;

    /** Resets on any lens, capture session, profile, orientation or mode change. */
    public synchronized void beginSession(long sessionEpoch) {
        epoch = sessionEpoch;
        latestFrameNs = Long.MIN_VALUE;
        missingSinceNs = Long.MIN_VALUE;
        selectedId = null;
        tapPinned = false;
        previousX = previousY = .5f;
    }

    public synchronized void clear() {
        selectedId = null;
        tapPinned = false;
        missingSinceNs = Long.MIN_VALUE;
    }

    /**
     * A user tap can pin a particular detected face; the caller handles the
     * ordinary tap-to-focus fallback when no face is in the tapped position.
     */
    public synchronized boolean tapSelect(List<Face> faces, float x, float y) {
        if (!finite(x) || !finite(y) || x < 0 || x > 1 || y < 0 || y > 1) return false;
        Face smallest = null;
        for (Face face : faces == null ? new ArrayList<Face>() : faces) {
            if (face == null || !face.valid() || !face.contains(x,y)) continue;
            if (smallest == null || area(face) < area(smallest)) smallest=face;
        }
        if (smallest == null) return false;
        selectedId = smallest.id;
        tapPinned = true;
        missingSinceNs = Long.MIN_VALUE;
        previousX = x;
        previousY = y;
        return true;
    }

    /**
     * Rejects wrong-generation, nonmonotonic and stale inference results.
     * In a pinned selection, never switches to another face implicitly.
     */
    public synchronized Target update(long sessionEpoch, long frameNs, long nowNs,
                                      List<Face> faces, Kind preference) {
        if (sessionEpoch != epoch || frameNs <= latestFrameNs || nowNs < frameNs
                || nowNs - frameNs > MAX_FRAME_AGE_NS || preference == null) return null;
        latestFrameNs = frameNs;
        Face active = null;
        if (faces != null) for (Face f : faces) {
            if (f != null && f.valid() && selectedId != null && f.id == selectedId) {
                active = f; break;
            }
        }
        if (active == null && selectedId != null) {
            if (missingSinceNs == Long.MIN_VALUE) missingSinceNs = nowNs;
            if (tapPinned || nowNs - missingSinceNs < LOST_GRACE_NS) return null;
            selectedId = null;
        }
        if (active == null && faces != null) {
            // In wide AF, favour prominent faces while penalising extreme edges.
            float best = -Float.MAX_VALUE;
            for (Face f : faces) {
                if (f == null || !f.valid()) continue;
                float centreDistance = (float)Math.hypot(f.cx() - .5f, f.cy() - .5f);
                float score = (float)Math.sqrt(area(f)) - .15f*centreDistance;
                if (score > best) { best=score; active=f; }
            }
            if (active != null) selectedId=active.id;
        }
        if (active == null) return null;
        missingSinceNs = Long.MIN_VALUE;
        float x=active.cx(), y=active.top + .42f*(active.bottom-active.top);
        boolean eyeFound = false;
        if (preference == Kind.HUMAN_EYE) {
            boolean l=within(active,active.leftEyeX,active.leftEyeY);
            boolean r=within(active,active.rightEyeX,active.rightEyeY);
            if (l || r) {
                // Preserve eye choice by proximity to the previous target.
                float dl=l ? distanceSquared(active.leftEyeX, active.leftEyeY,
                        previousX,previousY) : Float.POSITIVE_INFINITY;
                float dr=r ? distanceSquared(active.rightEyeX, active.rightEyeY,
                        previousX,previousY) : Float.POSITIVE_INFINITY;
                if (dl <= dr) {x=active.leftEyeX;y=active.leftEyeY;}
                else {x=active.rightEyeX;y=active.rightEyeY;}
                eyeFound=true;
            }
        }
        previousX=x; previousY=y;
        float w=Math.min(.18f,Math.max(.055f,(active.right-active.left)*(eyeFound?.32f:.68f)));
        float h=Math.min(.18f,Math.max(.055f,(active.bottom-active.top)*(eyeFound?.32f:.68f)));
        return new Target(active.id, preference, clamp01(x), clamp01(y), w, h,
                frameNs,sessionEpoch,eyeFound);
    }
    private static float area(Face face) {
        return (face.right-face.left)*(face.bottom-face.top);
    }
    private static float distanceSquared(float x,float y,float px,float py) {
        return (x-px)*(x-px)+(y-py)*(y-py);
    }
    private static boolean within(Face f,float x,float y) {
        return finite(x) && finite(y) && x>=f.left && x<=f.right
                && y>=f.top && y<=f.bottom;
    }
    private static boolean finite(float f) {
        return !Float.isNaN(f) && !Float.isInfinite(f);
    }
    private static float clamp01(float v) {
        return Math.max(0f,Math.min(1f,v));
    }
}
