package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * EXPOSUREAUDIT1A: capture-step-0 exposure ledger.
 *
 * Diagnostic only. It records the actual M9 primary frame allocation and
 * counterfactual Photon/FB1 allocations without changing exposure arithmetic.
 * Preflight GenerateExpoPair(-1, ...) calls and later burst steps are ignored so
 * they cannot overwrite the metadata for the primary frame.
 */
public final class M9ExposureAudit {
    public static final String SCHEMA = "m9cam.exposureaudit.v1";
    private static JSONObject capture = new JSONObject();

    private M9ExposureAudit() {}

    public static synchronized void beginStep0(int step,
                                                int sensorIsoLow,
                                                int previewIso,
                                                long previewShutterNs,
                                                int preFeedbackIsoNormalized,
                                                long preFeedbackShutterNs) {
        if (step != 0) return;
        JSONObject o = new JSONObject();
        try {
            o.put("schema", SCHEMA);
            o.put("captureStep", 0);
            o.put("primaryFramePolicy", "step0_only_preflight_immune");
            o.put("sensorIsoLow", sensorIsoLow);
            double normalizationFactor = 100.0 / Math.max(1, sensorIsoLow);
            o.put("normalizationFactor", normalizationFactor);

            JSONObject preview = new JSONObject();
            preview.put("iso", previewIso);
            preview.put("shutterNs", previewShutterNs);
            preview.put("energyIsoSeconds", energy(previewIso, previewShutterNs));
            preview.put("role", "camera2_preview_ae_result_not_final_capture");
            o.put("previewAe", preview);

            JSONObject target = normalizedPair(sensorIsoLow, preFeedbackIsoNormalized, preFeedbackShutterNs);
            target.put("role", "normalized_target_before_fb1_and_m9_motion_caps");
            o.put("preFeedbackTarget", target);
        } catch (Exception ignored) {}
        capture = o;
    }

    public static synchronized void recordPhotonReferenceStep0(int step,
                                                                int sensorIsoLow,
                                                                int normalizedIso,
                                                                long shutterNs,
                                                                long capStartNs,
                                                                long capEndNs) {
        if (step != 0) return;
        try {
            JSONObject p = normalizedPair(sensorIsoLow, normalizedIso, shutterNs);
            p.put("capStartNs", capStartNs);
            p.put("capEndNs", capEndNs);
            p.put("role", "photon_shutter_priority_without_fb1_or_m9_motion_cap");
            capture.put("photonOnly", p);
        } catch (Exception ignored) {}
    }

    public static synchronized void recordFeedbackStep0(int step,
                                                         int sensorIsoLow,
                                                         boolean eligible,
                                                         boolean wouldApply,
                                                         double recommendedEv,
                                                         double appliedEv,
                                                         String reason,
                                                         int postFeedbackIsoNormalized,
                                                         long postFeedbackShutterNs,
                                                         int feedbackOnlyIsoNormalized,
                                                         long feedbackOnlyShutterNs) {
        if (step != 0) return;
        try {
            JSONObject f = new JSONObject();
            f.put("eligible", eligible);
            f.put("wouldApply", wouldApply);
            f.put("recommendedEv", recommendedEv);
            f.put("appliedEv", appliedEv);
            f.put("reason", reason);
            f.put("requestedEnergyFactor", Math.pow(2.0, appliedEv));
            f.put("postFeedbackTarget", normalizedPair(sensorIsoLow, postFeedbackIsoNormalized, postFeedbackShutterNs));
            JSONObject only = normalizedPair(sensorIsoLow, feedbackOnlyIsoNormalized, feedbackOnlyShutterNs);
            only.put("role", "fb1_target_with_original_photon_caps_no_m9_motion_cap");
            f.put("feedbackOnly", only);
            capture.put("fb1", f);
        } catch (Exception ignored) {}
    }

    public static synchronized void recordMotionCapsStep0(int step,
                                                           boolean applied,
                                                           String reason,
                                                           double captureMotionScore,
                                                           long photonCapStartNs,
                                                           long photonCapEndNs,
                                                           long finalCapStartNs,
                                                           long finalCapEndNs) {
        if (step != 0) return;
        try {
            JSONObject m = new JSONObject();
            m.put("applied", applied);
            m.put("reason", reason);
            m.put("captureMotionScore", captureMotionScore);
            m.put("photonCapStartNs", photonCapStartNs);
            m.put("photonCapEndNs", photonCapEndNs);
            m.put("finalCapStartNs", finalCapStartNs);
            m.put("finalCapEndNs", finalCapEndNs);
            m.put("photonCapEndDenominator", denominator(photonCapEndNs));
            m.put("finalCapEndDenominator", denominator(finalCapEndNs));
            capture.put("m9MotionPolicy", m);
        } catch (Exception ignored) {}
    }

    public static synchronized void recordFinalNormalizedStep0(int step,
                                                                int sensorIsoLow,
                                                                int normalizedIso,
                                                                long shutterNs) {
        if (step != 0) return;
        try {
            JSONObject f = normalizedPair(sensorIsoLow, normalizedIso, shutterNs);
            f.put("role", "final_normalized_allocation_before_system_denormalize");
            capture.put("finalNormalized", f);
        } catch (Exception ignored) {}
    }

    public static synchronized void recordCaptureRequestStep0(int step,
                                                               int sensorIsoLow,
                                                               int actualIso,
                                                               long shutterNs) {
        if (step != 0) return;
        try {
            JSONObject r = new JSONObject();
            r.put("iso", actualIso);
            r.put("shutterNs", shutterNs);
            r.put("energyIsoSeconds", energy(actualIso, shutterNs));
            r.put("role", "denormalized_pair_written_to_capture_request_builder");
            capture.put("allocatorRequest", r);
            capture.put("sensorIsoLow", sensorIsoLow);
            addDerived(capture);
        } catch (Exception ignored) {}
    }

    public static synchronized JSONObject snapshotJson(JSONObject root) {
        try {
            JSONObject out = new JSONObject(capture.toString());
            JSONObject req = root != null ? root.optJSONObject("captureRequest") : null;
            JSONObject res = root != null ? root.optJSONObject("captureResult") : null;
            if (req != null) {
                JSONObject q = new JSONObject();
                int iso = req.optInt("iso", -1);
                long shutter = req.optLong("exposureTimeNs", -1L);
                q.put("iso", iso);
                q.put("shutterNs", shutter);
                if (iso > 0 && shutter > 0) q.put("energyIsoSeconds", energy(iso, shutter));
                out.put("camera2RequestObserved", q);
            }
            if (res != null) {
                JSONObject q = new JSONObject();
                int iso = res.optInt("iso", -1);
                long shutter = res.optLong("exposureTimeNs", -1L);
                q.put("iso", iso);
                q.put("shutterNs", shutter);
                if (iso > 0 && shutter > 0) q.put("energyIsoSeconds", energy(iso, shutter));
                out.put("camera2ResultObserved", q);
            }
            addObservedDerived(out);
            return out;
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private static JSONObject normalizedPair(int sensorIsoLow, int normalizedIso, long shutterNs) throws Exception {
        JSONObject p = new JSONObject();
        double systemIsoExact = normalizedIso * (Math.max(1, sensorIsoLow) / 100.0);
        p.put("normalizedIso", normalizedIso);
        p.put("systemIsoExact", systemIsoExact);
        p.put("systemIsoRounded", (int)Math.round(systemIsoExact));
        p.put("shutterNs", shutterNs);
        p.put("shutterDenominator", denominator(shutterNs));
        p.put("normalizedEnergyNsIso", (double)normalizedIso * (double)shutterNs);
        p.put("systemEnergyIsoSeconds", (systemIsoExact * (double)shutterNs) / 1.0e9);
        return p;
    }

    private static void addDerived(JSONObject o) throws Exception {
        JSONObject d = new JSONObject();
        JSONObject photon = o.optJSONObject("photonOnly");
        JSONObject fb = o.optJSONObject("fb1");
        JSONObject fbOnly = fb != null ? fb.optJSONObject("feedbackOnly") : null;
        JSONObject req = o.optJSONObject("allocatorRequest");
        JSONObject preview = o.optJSONObject("previewAe");

        if (preview != null && req != null) {
            d.put("previewIsoToCaptureIsoRatio", safeRatio(req.optDouble("iso", 0.0), preview.optDouble("iso", 0.0)));
            d.put("captureEnergyVsPreviewEv", evRatio(req.optDouble("energyIsoSeconds", 0.0), preview.optDouble("energyIsoSeconds", 0.0)));
        }
        if (photon != null && req != null) {
            d.put("captureIsoVsPhotonOnlyStops", evRatio(req.optDouble("iso", 0.0), photon.optDouble("systemIsoExact", 0.0)));
            d.put("captureEnergyVsPhotonOnlyEv", evRatio(req.optDouble("energyIsoSeconds", 0.0), photon.optDouble("systemEnergyIsoSeconds", 0.0)));
        }
        if (fbOnly != null && req != null) {
            d.put("motionIsoPenaltyStopsVsFeedbackOnly", evRatio(req.optDouble("iso", 0.0), fbOnly.optDouble("systemIsoExact", 0.0)));
            d.put("motionShutterDeltaEvVsFeedbackOnly", evRatio((double)fbOnly.optLong("shutterNs", 0L), (double)req.optLong("shutterNs", 0L)));
        }
        o.put("derived", d);
    }

    private static void addObservedDerived(JSONObject o) throws Exception {
        JSONObject d = o.optJSONObject("derived");
        if (d == null) d = new JSONObject();
        JSONObject alloc = o.optJSONObject("allocatorRequest");
        JSONObject req = o.optJSONObject("camera2RequestObserved");
        JSONObject res = o.optJSONObject("camera2ResultObserved");
        if (alloc != null && req != null) {
            d.put("camera2RequestVsAllocatorEnergyEv", evRatio(req.optDouble("energyIsoSeconds", 0.0), alloc.optDouble("energyIsoSeconds", 0.0)));
            d.put("camera2RequestIsoMatchesAllocator", req.optInt("iso", -1) == alloc.optInt("iso", -2));
            d.put("camera2RequestShutterMatchesAllocator", req.optLong("shutterNs", -1L) == alloc.optLong("shutterNs", -2L));
        }
        if (req != null && res != null) {
            d.put("camera2ResultVsRequestEnergyEv", evRatio(res.optDouble("energyIsoSeconds", 0.0), req.optDouble("energyIsoSeconds", 0.0)));
            d.put("camera2ResultIsoMatchesRequest", res.optInt("iso", -1) == req.optInt("iso", -2));
            d.put("camera2ResultShutterMatchesRequest", res.optLong("shutterNs", -1L) == req.optLong("shutterNs", -2L));
        }
        o.put("derived", d);
    }

    private static double energy(double iso, long shutterNs) {
        return (iso * (double)shutterNs) / 1.0e9;
    }

    private static double denominator(long shutterNs) {
        return shutterNs > 0 ? 1.0e9 / (double)shutterNs : 0.0;
    }

    private static double safeRatio(double a, double b) {
        return a > 0.0 && b > 0.0 ? a / b : 0.0;
    }

    private static double evRatio(double a, double b) {
        if (!(a > 0.0) || !(b > 0.0)) return 0.0;
        return Math.log(a / b) / Math.log(2.0);
    }
}
