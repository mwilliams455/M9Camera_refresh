package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * v0.6 first M9Modern exposure controller.
 * PhotonCurrent remains the baseline; this policy can only shorten Photon shutter caps.
 */
public final class M9ModernExposurePolicy {
    public static final double MOTION_ACTIVATE = 0.60;
    public static final double ANALOG_HEADROOM_FRACTION = 0.95;

    private static JSONObject lastDecision = new JSONObject();
    private M9ModernExposurePolicy() {}

    public static final class Decision {
        public final long capStartNs;
        public final long capEndNs;
        public final boolean applied;
        Decision(long capStartNs, long capEndNs, boolean applied) {
            this.capStartNs = capStartNs; this.capEndNs = capEndNs; this.applied = applied;
        }
    }

    public static synchronized Decision adjustCaps(long targetShutterNs,
                                                    int targetIsoNormalized,
                                                    int maxAnalogIsoNormalized,
                                                    long photonCapStartNs,
                                                    long photonCapEndNs) {
        final double score = M9SubjectMotionAnalyzer.getCaptureMotionScore();
        final long framesUsed = M9SubjectMotionAnalyzer.getFramesUsed();
        final double totalEnergyNsIso = (double) targetShutterNs * Math.max(1, targetIsoNormalized);
        long requestedMotionCapNs = photonCapEndNs;
        long analogHeadroomFloorNs = 0L;
        long achievableMotionCapNs = photonCapEndNs;
        long outStart = photonCapStartNs;
        long outEnd = photonCapEndNs;
        boolean applied = false;
        String reason;

        if (framesUsed < 3) {
            reason = "insufficient_motion_history";
        } else if (score < MOTION_ACTIVATE) {
            reason = "motion_below_activation";
        } else {
            double denominator = targetDenominator(score);
            requestedMotionCapNs = Math.max(1L, Math.round(1.0e9 / denominator));
            double analogBudget = Math.max(100.0,
                    Math.max(1, maxAnalogIsoNormalized) * ANALOG_HEADROOM_FRACTION);
            analogHeadroomFloorNs = Math.max(1L,
                    (long) Math.ceil(totalEnergyNsIso / analogBudget));
            achievableMotionCapNs = Math.max(requestedMotionCapNs, analogHeadroomFloorNs);
            outEnd = Math.min(photonCapEndNs, achievableMotionCapNs);
            outStart = Math.min(photonCapStartNs, outEnd);
            applied = outEnd < photonCapEndNs - Math.max(50_000L, photonCapEndNs / 200L);
            if (!applied) {
                if (photonCapEndNs <= requestedMotionCapNs) reason = "photon_already_as_fast_or_faster";
                else if (analogHeadroomFloorNs >= photonCapEndNs) reason = "analog_headroom_blocks_shortening";
                else reason = "no_material_cap_change";
            } else if (analogHeadroomFloorNs > requestedMotionCapNs) {
                reason = "motion_applied_analog_headroom_limited";
            } else reason = "motion_applied";
        }

        JSONObject o = new JSONObject();
        try {
            o.put("schema", "m9cam.modern.exposure.v1");
            o.put("enabled", true);
            o.put("motionActivationThreshold", MOTION_ACTIVATE);
            o.put("captureMotionScore", score);
            o.put("motionFramesUsed", framesUsed);
            o.put("targetExposureNs", targetShutterNs);
            o.put("targetIsoNormalized", targetIsoNormalized);
            o.put("targetEnergyNsIso", totalEnergyNsIso);
            o.put("maxAnalogIsoNormalized", maxAnalogIsoNormalized);
            o.put("analogHeadroomFraction", ANALOG_HEADROOM_FRACTION);
            o.put("photonCapStartNs", photonCapStartNs);
            o.put("photonCapEndNs", photonCapEndNs);
            o.put("requestedMotionCapNs", requestedMotionCapNs);
            o.put("requestedMotionDenominator", requestedMotionCapNs > 0 ? 1.0e9 / requestedMotionCapNs : 0.0);
            o.put("analogHeadroomFloorNs", analogHeadroomFloorNs);
            o.put("achievableMotionCapNs", achievableMotionCapNs);
            o.put("finalCapStartNs", outStart);
            o.put("finalCapEndNs", outEnd);
            o.put("finalCapDenominator", outEnd > 0 ? 1.0e9 / outEnd : 0.0);
            o.put("applied", applied);
            o.put("reason", reason);
            o.put("staticControlThresholdsFinal", false);
        } catch (Exception ignored) {}
        lastDecision = o;
        return new Decision(outStart, outEnd, applied);
    }

    public static synchronized JSONObject snapshotJson() {
        try { return new JSONObject(lastDecision.toString()); }
        catch (Exception e) { return new JSONObject(); }
    }

    private static double targetDenominator(double score) {
        double s = clamp01(score);
        if (s <= 0.60) return 30.0;
        if (s <= 0.70) return lerp(30.0, 40.0, (s - 0.60) / 0.10);
        if (s <= 0.85) return lerp(40.0, 60.0, (s - 0.70) / 0.15);
        return lerp(60.0, 75.0, (s - 0.85) / 0.15);
    }
    private static double lerp(double a, double b, double t) { return a + (b-a)*Math.max(0.0,Math.min(1.0,t)); }
    private static double clamp01(double x) { return Math.max(0.0, Math.min(1.0, x)); }
}
