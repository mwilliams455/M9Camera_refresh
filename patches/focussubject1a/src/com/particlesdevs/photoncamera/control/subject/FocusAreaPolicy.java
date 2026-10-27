package com.particlesdevs.photoncamera.control.subject;

/**
 * Preview-space focus-area policy. This is NOT the Camera2 region mapper: the
 * controller must map normalized display coordinates through its exact
 * rotation/mirror/viewport/crop/zoom/physical-camera geometry before use.
 */
public final class FocusAreaPolicy {
    public enum Mode { SPOT, EXPAND_SPOT, CUSTOM, WIDE }

    public static final class Rect {
        public final float left, top, right, bottom;
        private Rect(float left, float top, float right, float bottom) {
            this.left=left; this.top=top; this.right=right; this.bottom=bottom;
        }
        public float centerX() { return (left+right)*.5f; }
        public float centerY() { return (top+bottom)*.5f; }
        public float width() { return right-left; }
        public float height() { return bottom-top; }
    }
    private FocusAreaPolicy() {}

    /** Returns null for WIDE without a detected subject, leaving HAL default AF. */
    public static Rect region(Mode mode, float x, float y,
                              SubjectFocusPolicy.Target target,
                              float customW, float customH) {
        if (mode == null) return null;
        float cx = target != null ? target.x : x;
        float cy = target != null ? target.y : y;
        if (!finite(cx) || !finite(cy)) return null;
        float w, h;
        switch(mode) {
            case SPOT: w=.07f; h=.07f; break;
            case EXPAND_SPOT: w=.18f; h=.18f; break;
            case CUSTOM:
                if (!finite(customW) || !finite(customH)) return null;
                w=limit(customW,.05f,.5f);
                h=limit(customH,.05f,.5f);
                break;
            case WIDE:
                if (target == null) return null;
                w=limit(target.regionWidth,.05f,.22f);
                h=limit(target.regionHeight,.05f,.22f);
                break;
            default: return null;
        }
        cx=limit(cx,0f,1f);cy=limit(cy,0f,1f);
        float l=limit(cx-w*.5f,0f,1f-w);
        float t=limit(cy-h*.5f,0f,1f-h);
        return new Rect(l,t,l+w,t+h);
    }
    private static float limit(float x,float lo,float hi) {
        return Math.max(lo,Math.min(hi,x));
    }
    private static boolean finite(float x) {
        return !Float.isNaN(x) && !Float.isInfinite(x);
    }
}
