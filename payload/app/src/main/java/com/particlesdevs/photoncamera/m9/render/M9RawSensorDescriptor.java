package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.BlackLevelPattern;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.hardware.camera2.params.LensShadingMap;
import android.util.Rational;
import android.util.Size;

import com.particlesdevs.photoncamera.processing.render.Parameters;

import org.json.JSONArray;
import org.json.JSONObject;

/** DEVICEPORT1A source-RAW descriptor. Descriptive only in this build. */
public final class M9RawSensorDescriptor {
    public static final String VERSION = "deviceport1a-cfaabstract1a";

    public final int rawWidth;
    public final int rawHeight;
    public final int rawRowStrideBytes;
    public final int rawPixelStrideBytes;
    public final int rawBufferCapacityBytes;
    public final int camera2Cfa;
    public final M9CfaResolver.Pattern cfaPattern;
    public final int rawOriginX;
    public final int rawOriginY;
    public final boolean rawOriginProven;
    public final int[] blackLevel;
    public final int whiteLevel;
    public final int characteristicsWhiteLevel;
    public final boolean lensShadingAppliedToRaw;
    public final boolean lensShadingMapAvailable;
    public final int lensShadingMapRows;
    public final int lensShadingMapColumns;

    private final Parameters params;
    private final CameraCharacteristics characteristics;
    private final CaptureResult captureResult;
    private final CaptureRequest captureRequest;

    private M9RawSensorDescriptor(int rawWidth, int rawHeight, int rawBufferCapacityBytes,
                                  int camera2Cfa, M9CfaResolver.Pattern cfaPattern,
                                  int[] blackLevel, int whiteLevel, int characteristicsWhiteLevel,
                                  boolean lensShadingAppliedToRaw, boolean lensShadingMapAvailable,
                                  int lensShadingMapRows, int lensShadingMapColumns,
                                  Parameters params, CameraCharacteristics characteristics,
                                  CaptureResult captureResult, CaptureRequest captureRequest) {
        this.rawWidth = rawWidth;
        this.rawHeight = rawHeight;
        this.rawPixelStrideBytes = 2;
        this.rawRowStrideBytes = rawWidth > 0 ? rawWidth * 2 : -1;
        this.rawBufferCapacityBytes = rawBufferCapacityBytes;
        this.camera2Cfa = camera2Cfa;
        this.cfaPattern = cfaPattern;
        this.rawOriginX = 0;
        this.rawOriginY = 0;
        this.rawOriginProven = false;
        this.blackLevel = blackLevel;
        this.whiteLevel = whiteLevel;
        this.characteristicsWhiteLevel = characteristicsWhiteLevel;
        this.lensShadingAppliedToRaw = lensShadingAppliedToRaw;
        this.lensShadingMapAvailable = lensShadingMapAvailable;
        this.lensShadingMapRows = lensShadingMapRows;
        this.lensShadingMapColumns = lensShadingMapColumns;
        this.params = params;
        this.characteristics = characteristics;
        this.captureResult = captureResult;
        this.captureRequest = captureRequest;
    }

    public static M9RawSensorDescriptor fromActive(int rawWidth, int rawHeight,
                                                   int rawBufferCapacityBytes,
                                                   Parameters params,
                                                   CameraCharacteristics characteristics,
                                                   CaptureResult captureResult,
                                                   CaptureRequest captureRequest) {
        int cfa = params != null ? params.cfaPattern & 0xff : -1;
        Integer nativeCfa = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT) : null;
        if (nativeCfa != null) cfa = nativeCfa;

        int[] black = activeBlack(params, characteristics);
        int wl = params != null ? params.whiteLevel : -1;
        Integer charWl = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        Boolean shadingApplied = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED) : null;
        LensShadingMap shadingMap = captureResult != null
                ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP) : null;
        int mapRows = shadingMap != null ? shadingMap.getRowCount() : -1;
        int mapColumns = shadingMap != null ? shadingMap.getColumnCount() : -1;

        return new M9RawSensorDescriptor(rawWidth, rawHeight, rawBufferCapacityBytes,
                cfa, M9CfaResolver.fromCamera2(cfa), black, wl,
                charWl != null ? charWl : -1, Boolean.TRUE.equals(shadingApplied),
                shadingMap != null, mapRows, mapColumns,
                params, characteristics, captureResult, captureRequest);
    }

    private static int[] activeBlack(Parameters params, CameraCharacteristics characteristics) {
        if (params != null && params.blackLevel != null && params.blackLevel.length >= 4) {
            int[] out = new int[4];
            for (int i = 0; i < 4; i++) out[i] = Math.round(params.blackLevel[i]);
            return out;
        }
        BlackLevelPattern p = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        if (p == null) return null;
        int[] out = new int[4];
        p.copyTo(out, 0);
        return out;
    }

    public JSONObject toJson() throws Exception {
        JSONObject out = new JSONObject();
        out.put("descriptorVersion", VERSION);
        out.put("scope", "source_raw_description_only_no_pixel_change");

        if (params != null) {
            out.put("cameraID", params.cameraID != null ? String.valueOf(params.cameraID) : JSONObject.NULL);
            out.put("logicalCameraId", String.valueOf(params.logicalID));
            out.put("physicalCameraId", String.valueOf(params.physicalID));
            out.put("focalLengthMm", params.focalLength);
            out.put("aperture", params.aperture);
        }

        out.put("rawWidth", rawWidth);
        out.put("rawHeight", rawHeight);
        out.put("rawRowStrideBytes", rawRowStrideBytes);
        out.put("rawPixelStrideBytes", rawPixelStrideBytes);
        out.put("rawBufferCapacityBytes", rawBufferCapacityBytes);
        out.put("rawPacking", "Photon_tightly_packed_uint16_after_capture_handoff");

        out.put("colorFilterArrangement", camera2Cfa);
        out.put("resolvedCfaPattern", cfaPattern.name());
        out.put("supportedConventionalBayer", cfaPattern != M9CfaResolver.Pattern.UNSUPPORTED);
        out.put("rawOriginX", rawOriginX);
        out.put("rawOriginY", rawOriginY);
        out.put("rawOriginProven", rawOriginProven);
        out.put("rawOriginEvidence", "UNPROVEN_DEVICEPORT1A_do_not_shift_by_active_array_without_buffer_coordinate_proof");
        out.put("resolvedCfaPhase", cfaPattern != M9CfaResolver.Pattern.UNSUPPORTED
                ? M9CfaResolver.localPhaseName(cfaPattern, rawOriginX, rawOriginY) : "UNSUPPORTED");

        out.put("blackLevelPattern", ints(blackLevel));
        out.put("blackLevelPlaneOrder", "local_raw_2x2_order_only_phase_not_yet_proven");
        out.put("whiteLevel", whiteLevel);
        out.put("characteristicsWhiteLevel", characteristicsWhiteLevel);
        if (whiteLevel > 0 && characteristicsWhiteLevel > 0) {
            out.put("whiteLevelAgreement", whiteLevel == characteristicsWhiteLevel);
        } else {
            out.put("whiteLevelAgreement", JSONObject.NULL);
        }

        if (characteristics != null) {
            out.put("pixelArraySize", size(characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)));
            out.put("preCorrectionActiveArray",
                    rect(characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE)));
            out.put("activeArray",
                    rect(characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)));
            Integer orientation = characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION);
            out.put("sensorOrientation", orientation != null ? orientation : JSONObject.NULL);
            out.put("lensShadingAppliedToRaw", lensShadingAppliedToRaw);

            out.put("referenceIlluminant1",
                    nullableNumber(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1)));
            out.put("referenceIlluminant2",
                    nullableNumber(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2)));
            out.put("calibrationTransform1",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1)));
            out.put("calibrationTransform2",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2)));
            out.put("colorTransform1",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1)));
            out.put("colorTransform2",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2)));
            out.put("forwardMatrix1",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1)));
            out.put("forwardMatrix2",
                    matrix(characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2)));
            out.put("matrixSerialization", "Camera2_ColorSpaceTransform_copyElements_row_major");
        }

        out.put("lensShadingMapAvailable", lensShadingMapAvailable);
        out.put("lensShadingMapRows", lensShadingMapRows >= 0 ? lensShadingMapRows : JSONObject.NULL);
        out.put("lensShadingMapColumns", lensShadingMapColumns >= 0 ? lensShadingMapColumns : JSONObject.NULL);
        if (captureResult != null) {
            Integer mapMode = captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE);
            out.put("lensShadingMapModeResult", mapMode != null ? mapMode : JSONObject.NULL);
            Rational[] neutral = captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
            out.put("captureNeutral", rationals(neutral));
        }
        if (captureRequest != null) {
            Integer mapMode = captureRequest.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE);
            out.put("lensShadingMapModeRequest", mapMode != null ? mapMode : JSONObject.NULL);
        }

        out.put("renderUseInThisBuild", false);
        out.put("photographicPipelineFrozen", true);
        return out;
    }

    private static Object nullableNumber(Number n) {
        return n != null ? n : JSONObject.NULL;
    }

    private static JSONArray ints(int[] values) {
        if (values == null) return null;
        JSONArray a = new JSONArray();
        for (int v : values) a.put(v);
        return a;
    }

    private static JSONArray rationals(Rational[] values) throws Exception {
        if (values == null) return null;
        JSONArray a = new JSONArray();
        for (Rational v : values) a.put(v != null ? v.doubleValue() : JSONObject.NULL);
        return a;
    }

    private static JSONObject size(Size s) throws Exception {
        if (s == null) return null;
        JSONObject o = new JSONObject();
        o.put("width", s.getWidth());
        o.put("height", s.getHeight());
        return o;
    }

    private static JSONObject rect(Rect r) throws Exception {
        if (r == null) return null;
        JSONObject o = new JSONObject();
        o.put("left", r.left);
        o.put("top", r.top);
        o.put("right", r.right);
        o.put("bottom", r.bottom);
        o.put("width", r.width());
        o.put("height", r.height());
        return o;
    }

    private static JSONArray matrix(ColorSpaceTransform t) throws Exception {
        if (t == null) return null;
        Rational[] elements = new Rational[9];
        t.copyElements(elements, 0);
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) {
                Rational v = elements[r * 3 + c];
                row.put(v != null ? v.doubleValue() : JSONObject.NULL);
            }
            rows.put(row);
        }
        return rows;
    }
}
