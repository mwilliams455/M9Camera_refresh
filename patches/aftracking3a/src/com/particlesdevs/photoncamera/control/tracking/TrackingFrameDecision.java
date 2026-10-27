package com.particlesdevs.photoncamera.control.tracking;

/**
 * Safely translates a visual-patch observation into a camera-owner decision.
 * HOLD NEVER submits an AF target. RETIRE releases the tracking focus handle.
 * This class is camera-independent and deliberately has no 3A side effects.
 */
public final class TrackingFrameDecision {
    public enum Action { APPLY, HOLD, RETIRE }
    public static final long MAX_ACTION_AGE_MS = 500;
    private TrackingFrameDecision() { }

    public static Action classify(PatchTracker.Result observed, long ageMs) {
        if (observed == null || ageMs < 0 || ageMs > MAX_ACTION_AGE_MS)
            return Action.RETIRE;
        if (!Float.isFinite(observed.x) || !Float.isFinite(observed.y)
                || observed.x < 0 || observed.x > 1 || observed.y < 0 || observed.y > 1)
            return Action.RETIRE;
        if (observed.holding) return Action.HOLD;
        return observed.tracking ? Action.APPLY : Action.RETIRE;
    }
}
