package com.particlesdevs.photoncamera.m9.render;

import org.json.JSONObject;

/**
 * FALLOFFTGT1A coordinate/model contract only.
 *
 * The radial model is defined now so still and live paths can share one target-domain
 * coordinate system. Coefficients are intentionally not guessed; 1A is identity until
 * genuine Leica M9 evidence calibrates a2/a4/a6.
 */
public final class M9TargetFalloff1A {
    public static final String VERSION = "fallofftgt1a-contract";
    public static final boolean PIXEL_MUTATION_ENABLED = false;

    private M9TargetFalloff1A() {}

    /** Center is radius 0; every image corner is radius 1 regardless of raster size. */
    public static double normalizedRadius(int x, int y, int width, int height) {
        if (width <= 0 || height <= 0) return 0.0;
        double nx = (2.0 * ((x + 0.5) / (double) width)) - 1.0;
        double ny = (2.0 * ((y + 0.5) / (double) height)) - 1.0;
        return Math.min(1.0, Math.sqrt(nx * nx + ny * ny) / Math.sqrt(2.0));
    }

    /** Identity until coefficients are calibrated from genuine M9 evidence. */
    public static double gainForRadius(double r) {
        return 1.0;
    }

    public static JSONObject describe() throws Exception {
        JSONObject j = new JSONObject();
        j.put("revision", "FALLOFFTGT1A");
        j.put("coordinateSpace", "normalized_image_coordinates_center_0_corner_radius_1");
        j.put("model", "EV(r)=a2*r^2+a4*r^4+a6*r^6");
        j.put("applicationDomain", "linear_RGB_after_source_normalization_before_M9_target_tone");
        j.put("calibrationStatus", "PENDING_GENUINE_M9_EVIDENCE");
        j.put("pixelMutationEnabled", PIXEL_MUTATION_ENABLED);
        j.put("gainIn1A", 1.0);
        j.put("sourceLensShadingIsTargetFalloff", false);
        return j;
    }
}
