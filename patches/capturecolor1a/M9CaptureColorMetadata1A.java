package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.hardware.camera2.params.RggbChannelVector;
import android.util.Rational;

import org.json.JSONArray;
import org.json.JSONObject;

/** Still-result observation only; never supplies values to the renderer. */
public final class M9CaptureColorMetadata1A {
    private M9CaptureColorMetadata1A() {}

    public static JSONObject capture(CaptureResult result, String requestedCameraId) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", "m9.capturecolormetadata.v1a");
            out.put("scope", "diagnostic_only_no_pixel_change");
            out.put("provenance", "one_resolved_CaptureResult_passed_to_source_calibration_audit");
            out.put("captureResultAvailable", result != null);
            out.put("requestedCameraId", value(requestedCameraId));
            out.put("captureResultCameraId", value(M9PhysicalCaptureResult1A.resultCameraId(result)));
            out.put("gainOrder", "R,GreenEven,GreenOdd,B");
            out.put("matrixOrder", "row_major");
            out.put("missingValuePolicy", "null_no_inverse_neutral_or_history_substitution");
            out.put("captureMetadataReadComplete", false);

            // Long identity values remain JSON integers, without conversion to double.
            out.put("sensorTimestampNs", read(result, CaptureResult.SENSOR_TIMESTAMP));
            out.put("frameNumber", result != null ? Long.valueOf(result.getFrameNumber()) : JSONObject.NULL);
            out.put("colorCorrectionMode", read(result, CaptureResult.COLOR_CORRECTION_MODE));
            out.put("awbMode", read(result, CaptureResult.CONTROL_AWB_MODE));
            out.put("awbState", read(result, CaptureResult.CONTROL_AWB_STATE));
            out.put("awbLock", read(result, CaptureResult.CONTROL_AWB_LOCK));
            out.put("sensorSensitivityIso", read(result, CaptureResult.SENSOR_SENSITIVITY));
            out.put("sensorExposureTimeNs", read(result, CaptureResult.SENSOR_EXPOSURE_TIME));

            RggbChannelVector gains = result != null
                    ? result.get(CaptureResult.COLOR_CORRECTION_GAINS) : null;
            out.put("reportedColorCorrectionGainsRGeGoB", gains == null ? JSONObject.NULL
                    : new JSONArray().put((double) gains.getRed())
                            .put((double) gains.getGreenEven()).put((double) gains.getGreenOdd())
                            .put((double) gains.getBlue()));
            Rational[] neutral = result != null
                    ? result.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT) : null;
            out.put("sensorNeutralColorPoint", rationals(neutral));
            ColorSpaceTransform transform = result != null
                    ? result.get(CaptureResult.COLOR_CORRECTION_TRANSFORM) : null;
            Rational[] elements = null;
            if (transform != null) {
                elements = new Rational[9];
                transform.copyElements(elements, 0);
            }
            out.put("colorCorrectionTransform", rationals(elements));
            // Complete means the read finished, not that the HAL supplied every key.
            out.put("captureMetadataReadComplete", true);
        } catch (Throwable error) {
            // A diagnostic failure must not abort the existing source audit or capture.
            try { out.put("error", error.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    private static Object value(Object value) {
        return value != null ? value : JSONObject.NULL;
    }

    private static <T> Object read(CaptureResult result, CaptureResult.Key<T> key) {
        return value(result != null ? result.get(key) : null);
    }

    private static Object rationals(Rational[] values) throws org.json.JSONException {
        if (values == null) return JSONObject.NULL;
        JSONArray exact = new JSONArray();
        JSONArray decimal = new JSONArray();
        for (Rational item : values) {
            if (item == null) {
                exact.put(JSONObject.NULL);
                decimal.put(JSONObject.NULL);
            } else {
                exact.put(new JSONArray().put(item.getNumerator()).put(item.getDenominator()));
                double d = item.doubleValue();
                if (Double.isNaN(d) || Double.isInfinite(d)) decimal.put(JSONObject.NULL);
                else decimal.put(d);
            }
        }
        return new JSONObject().put("numeratorDenominator", exact).put("values", decimal);
    }
}
