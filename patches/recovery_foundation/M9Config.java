package com.particlesdevs.photoncamera.m9;

/** Recovery bootstrap configuration for the accepted M9Modern route. */
public final class M9Config {
    private M9Config() {}

    public static final M9ProcessingRoute ROUTE = M9ProcessingRoute.M9_MODERN;

    public static boolean isCaptureTest() {
        return ROUTE == M9ProcessingRoute.M9_CAPTURE_TEST
                || ROUTE == M9ProcessingRoute.M9_EXACT
                || ROUTE == M9ProcessingRoute.M9_MODERN;
    }

    public static boolean isM9Modern() {
        return ROUTE == M9ProcessingRoute.M9_MODERN;
    }

    public static boolean usesM9Pipeline() {
        return ROUTE != M9ProcessingRoute.PHOTON;
    }
}
