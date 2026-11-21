package com.particlesdevs.photoncamera.control.tracking;

/**
 * Camera-independent eligibility for deliberately tapped subjects.
 * Does not request Camera2 focus, identify a scene, or modify rendering.
 */
public final class TrackingDefaultPolicy {
    private TrackingDefaultPolicy() { }

    /** No automatic arbitrary selection; an eligible tap starts tracking. */
    public static boolean eligible(boolean m9Profile, boolean stillMode,
                                   boolean trackingEnabled, boolean afContinuousPicture,
                                   boolean wideArea, boolean petAfEnabled) {
        return m9Profile && stillMode && trackingEnabled
                && afContinuousPicture && wideArea && !petAfEnabled;
    }

    /** Avoid model initialisation/inference before a deliberate selection. */
    public static boolean warmSemantic(boolean explicitTargetSelected,
                                       boolean subjectRecognitionEnabled) {
        return explicitTargetSelected && subjectRecognitionEnabled;
    }
}
