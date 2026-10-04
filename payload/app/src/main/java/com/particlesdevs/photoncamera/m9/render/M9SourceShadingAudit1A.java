package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * SOURCESHADING1A portable source-domain shading descriptor.
 *
 * Diagnostic only. It records the Camera2 lens-shading state needed to design an
 * exactly-once, physical-sensor-generic source normalization stage. No value from
 * this class is consumed by the photographic renderer in this build.
 */
public final class M9SourceShadingAudit1A {
    public static final String VERSION = "sourceshading1a-portable";
    public static final String API_CHANNEL_ORDER = "R,Geven,Godd,B";

    private M9SourceShadingAudit1A() {}

    public static JSONObject describe(int rawWidth,
                                      int rawHeight,
                                      CameraCharacteristics characteristics,
                                      CaptureResult captureResult,
                                      CaptureRequest captureRequest) throws Exception {
        JSONObject out = new JSONObject();
        out.put("version", VERSION);
        out.put("scope", "source_domain_diagnostic_only_no_pixel_change");
        out.put("physicalSensorGeneric", true);
        out.put("cameraIdUsedForBehavior", false);
        out.put("focalLengthUsedForBehavior", false);
        out.put("zoomLabelUsedForBehavior", false);
        out.put("sourceAdapterStageOrder",
                "RAW_GEOMETRY_CFA->BLACK_WHITE_NORMALIZE->SOURCE_SHADING_NORMALIZE->SENSOR_COLOR_NORMALIZE->COMMON_SCENE");
        out.put("sourceShadingCorrectionAppliedInThisBuild", false);
        out.put("m9TargetRendererChanged", false);

        Rect active = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE) : null;
        Rect preCorrection = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE) : null;
        Rect crop = captureResult != null
                ? captureResult.get(CaptureResult.SCALER_CROP_REGION) : null;
        if (crop == null && captureRequest != null) {
            crop = captureRequest.get(CaptureRequest.SCALER_CROP_REGION);
        }

        out.put("rawWidth", rawWidth);
        out.put("rawHeight", rawHeight);
        out.put("activeArray", rect(active));
        out.put("preCorrectionActiveArray", rect(preCorrection));
        out.put("scalerCropRegion", rect(crop));
        out.put("rawDimensionsMatchActiveArray",
                active != null && rawWidth == active.width() && rawHeight == active.height());
        out.put("rawDimensionsMatchPreCorrectionActiveArray",
                preCorrection != null
                        && rawWidth == preCorrection.width()
                        && rawHeight == preCorrection.height());
        out.put("rawToActiveArrayGeometryProven", false);
        out.put("rawToActiveArrayGeometryReason",
                "dimension_agreement_is_evidence_only; RAW_buffer_origin_and_coordinate_mapping_must_be_proven_before_photographic_mutation");

        Boolean applied = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED) : null;
        out.put("sensorInfoLensShadingApplied",
                applied != null ? applied : JSONObject.NULL);
        out.put("camera2RemainingCorrectionRule",
                "result_map_is_complete_correction_when_RAW_shading_applied_false_and_remaining_correction_when_true");
        out.put("doubleCorrectionGuard",
                "never_apply_assumed_complete_map_on_top_of_RAW_without_respecting_SENSOR_INFO_LENS_SHADING_APPLIED_and_live_remaining_map");

        Integer resultShadingMode = captureResult != null
                ? captureResult.get(CaptureResult.SHADING_MODE) : null;
        Integer requestShadingMode = captureRequest != null
                ? captureRequest.get(CaptureRequest.SHADING_MODE) : null;
        Integer resultMapMode = captureResult != null
                ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE) : null;
        Integer requestMapMode = captureRequest != null
                ? captureRequest.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE) : null;
        out.put("shadingModeResult", nullable(resultShadingMode));
        out.put("shadingModeRequest", nullable(requestShadingMode));
        out.put("lensShadingMapModeResult", nullable(resultMapMode));
        out.put("lensShadingMapModeRequest", nullable(requestMapMode));

        LensShadingMap map = captureResult != null
                ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP) : null;
        out.put("liveRemainingMapAvailable", map != null);
        out.put("mapGeometrySource",
                map != null
                        ? "live_CaptureResult_LensShadingMap_getColumnCount_getRowCount"
                        : "unavailable");
        out.put("mapDomain", "entire_active_pixel_array_independent_of_scaler_crop");
        out.put("mapInterpolation", "bilinear_between_grid_samples");
        out.put("mapChannelOrder", API_CHANNEL_ORDER);
        out.put("mapChannelOrderSource", "Android_Camera2_LensShadingMap_API");

        if (map != null) {
            int columns = map.getColumnCount();
            int rows = map.getRowCount();
            float[] factors = new float[map.getGainFactorCount()];
            map.copyGainFactors(factors, 0);
            int expected = columns > 0 && rows > 0 ? columns * rows * 4 : 0;
            boolean valid = expected > 0 && factors.length == expected;

            out.put("mapColumns", columns);
            out.put("mapRows", rows);
            out.put("mapFactorCount", factors.length);
            out.put("mapExpectedFactorCount", expected);
            out.put("mapFactorCountValid", valid);
            out.put("mapFullyInterleaved", true);

            if (valid) {
                out.put("mapStatsPerChannel", channelStats(factors));
                out.put("mapIdentityWithin1e5", identityWithin(factors, 1.0e-5));
                out.put("mapMaxAbsFromUnity", maxAbsFromUnity(factors));
                out.put("mapSpatialSamples", spatialSamples(factors, columns, rows));
                out.put("mapCenterToCornerEv", centerToCornerEv(factors, columns, rows));
            }
        } else {
            out.put("mapColumns", 0);
            out.put("mapRows", 0);
            out.put("mapFactorCount", 0);
            out.put("mapExpectedFactorCount", 0);
            out.put("mapFactorCountValid", false);
        }

        out.put("sourceShadingCorrectionEligible", false);
        out.put("eligibilityBlockers", new JSONArray()
                .put("RAW_buffer_origin_to_active_array_mapping_not_yet_proven")
                .put("exactly_once_application_must_be_validated_against_live_remaining_map_semantics")
                .put("diagnostic_cross_sensor_correlation_required_before_enabling_mutation"));
        return out;
    }

    private static JSONArray channelStats(float[] factors) throws Exception {
        JSONArray out = new JSONArray();
        String[] names = {"R", "Geven", "Godd", "B"};
        for (int c = 0; c < 4; c++) {
            double min = Double.POSITIVE_INFINITY;
            double max = Double.NEGATIVE_INFINITY;
            double sum = 0.0;
            int n = 0;
            for (int i = c; i < factors.length; i += 4) {
                double v = factors[i];
                if (!Double.isFinite(v)) continue;
                min = Math.min(min, v);
                max = Math.max(max, v);
                sum += v;
                n++;
            }
            JSONObject s = new JSONObject();
            s.put("channelIndex", c);
            s.put("channelName", names[c]);
            s.put("count", n);
            s.put("valid", n > 0);
            if (n > 0) {
                s.put("min", min);
                s.put("max", max);
                s.put("mean", sum / n);
            }
            out.put(s);
        }
        return out;
    }

    private static JSONObject spatialSamples(float[] factors,
                                             int columns,
                                             int rows) throws Exception {
        JSONObject out = new JSONObject();
        out.put("topLeft", sample(factors, columns, rows, 0.0, 0.0));
        out.put("topMid", sample(factors, columns, rows, 0.5, 0.0));
        out.put("topRight", sample(factors, columns, rows, 1.0, 0.0));
        out.put("leftMid", sample(factors, columns, rows, 0.0, 0.5));
        out.put("center", sample(factors, columns, rows, 0.5, 0.5));
        out.put("rightMid", sample(factors, columns, rows, 1.0, 0.5));
        out.put("bottomLeft", sample(factors, columns, rows, 0.0, 1.0));
        out.put("bottomMid", sample(factors, columns, rows, 0.5, 1.0));
        out.put("bottomRight", sample(factors, columns, rows, 1.0, 1.0));
        return out;
    }

    private static JSONObject sample(float[] factors,
                                     int columns,
                                     int rows,
                                     double nx,
                                     double ny) throws Exception {
        JSONObject out = new JSONObject();
        JSONArray channels = new JSONArray();
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
        double sum = 0.0;
        for (int c = 0; c < 4; c++) {
            double v = bilinear(factors, columns, rows, nx, ny, c);
            channels.put(v);
            min = Math.min(min, v);
            max = Math.max(max, v);
            sum += v;
        }
        out.put("channelsRGevenGoddB", channels);
        out.put("meanGain", sum / 4.0);
        out.put("channelSpread", max - min);
        out.put("greenEvenOddDelta", channels.getDouble(1) - channels.getDouble(2));
        out.put("redBlueVsGreenAxis",
                0.5 * (channels.getDouble(0) + channels.getDouble(3))
                        - 0.5 * (channels.getDouble(1) + channels.getDouble(2)));
        return out;
    }

    private static double bilinear(float[] factors,
                                   int columns,
                                   int rows,
                                   double nx,
                                   double ny,
                                   int channel) {
        if (columns <= 0 || rows <= 0 || factors == null
                || factors.length < columns * rows * 4) return Double.NaN;
        double x = clamp01(nx) * Math.max(0, columns - 1);
        double y = clamp01(ny) * Math.max(0, rows - 1);
        int x0 = (int) Math.floor(x);
        int y0 = (int) Math.floor(y);
        int x1 = Math.min(columns - 1, x0 + 1);
        int y1 = Math.min(rows - 1, y0 + 1);
        double tx = x - x0;
        double ty = y - y0;
        double v00 = factors[((y0 * columns + x0) * 4) + channel];
        double v10 = factors[((y0 * columns + x1) * 4) + channel];
        double v01 = factors[((y1 * columns + x0) * 4) + channel];
        double v11 = factors[((y1 * columns + x1) * 4) + channel];
        double top = v00 + (v10 - v00) * tx;
        double bottom = v01 + (v11 - v01) * tx;
        return top + (bottom - top) * ty;
    }

    private static JSONArray centerToCornerEv(float[] factors,
                                              int columns,
                                              int rows) throws Exception {
        JSONArray out = new JSONArray();
        double[][] corners = {{0.0, 0.0}, {1.0, 0.0}, {0.0, 1.0}, {1.0, 1.0}};
        for (int c = 0; c < 4; c++) {
            double center = bilinear(factors, columns, rows, 0.5, 0.5, c);
            double cornerMean = 0.0;
            for (double[] p : corners) {
                cornerMean += bilinear(factors, columns, rows, p[0], p[1], c);
            }
            cornerMean /= corners.length;
            double ev = center > 0.0 && cornerMean > 0.0
                    ? Math.log(cornerMean / center) / Math.log(2.0)
                    : Double.NaN;
            out.put(ev);
        }
        return out;
    }

    private static boolean identityWithin(float[] factors, double epsilon) {
        for (float factor : factors) {
            if (!Float.isFinite(factor) || Math.abs(factor - 1.0f) > epsilon) return false;
        }
        return true;
    }

    private static double maxAbsFromUnity(float[] factors) {
        double max = 0.0;
        for (float factor : factors) {
            if (!Float.isFinite(factor)) continue;
            max = Math.max(max, Math.abs((double) factor - 1.0));
        }
        return max;
    }

    private static double clamp01(double v) {
        return Math.max(0.0, Math.min(1.0, v));
    }

    private static Object nullable(Object value) {
        return value != null ? value : JSONObject.NULL;
    }

    private static Object rect(Rect r) throws Exception {
        if (r == null) return JSONObject.NULL;
        JSONObject out = new JSONObject();
        out.put("left", r.left);
        out.put("top", r.top);
        out.put("right", r.right);
        out.put("bottom", r.bottom);
        out.put("width", r.width());
        out.put("height", r.height());
        return out;
    }
}
