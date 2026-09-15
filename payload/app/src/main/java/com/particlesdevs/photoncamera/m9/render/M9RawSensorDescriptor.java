package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Point;
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
    public final long rawExpectedTightBytes;
    public final boolean rawBufferMatchesTightU16;

    /** Static Camera2 CFA, or -1 if absent. */
    public final int camera2Cfa;
    /** Photon Parameters CFA after settings/config processing, or -1 if unavailable. */
    public final int photonEffectiveCfa;
    /** Camera2 CFA is authoritative when present; Photon is diagnostic fallback only. */
    public final int resolvedCfa;
    public final M9CfaResolver.Pattern cfaPattern;

    public final int rawOriginX;
    public final int rawOriginY;
    public final boolean rawOriginProven;

    /** What the existing Photon/M9 path will currently subtract. */
    public final float[] photonEffectiveBlackLevel;
    /** Static black pattern from the characteristics object passed to this render. */
    public final int[] characteristicsBlackLevelPattern;
    /** Per-capture dynamic black metadata, whether or not Photon is configured to use it. */
    public final float[] captureDynamicBlackLevel;

    /** What Photon will currently normalize against. */
    public final int whiteLevel;
    public final int characteristicsWhiteLevel;
    public final int captureDynamicWhiteLevel;

    public final boolean lensShadingAppliedToRaw;
    public final boolean lensShadingMapAvailable;
    public final int lensShadingMapRows;
    public final int lensShadingMapColumns;

    private final Parameters params;
    private final CameraCharacteristics characteristics;
    private final CaptureResult captureResult;
    private final CaptureRequest captureRequest;

    private M9RawSensorDescriptor(int rawWidth, int rawHeight, int rawBufferCapacityBytes,
                                  int camera2Cfa, int photonEffectiveCfa, int resolvedCfa,
                                  M9CfaResolver.Pattern cfaPattern,
                                  float[] photonEffectiveBlackLevel,
                                  int[] characteristicsBlackLevelPattern,
                                  float[] captureDynamicBlackLevel,
                                  int whiteLevel, int characteristicsWhiteLevel,
                                  int captureDynamicWhiteLevel,
                                  boolean lensShadingAppliedToRaw, boolean lensShadingMapAvailable,
                                  int lensShadingMapRows, int lensShadingMapColumns,
                                  Parameters params, CameraCharacteristics characteristics,
                                  CaptureResult captureResult, CaptureRequest captureRequest) {
        this.rawWidth = rawWidth;
        this.rawHeight = rawHeight;
        this.rawBufferCapacityBytes = rawBufferCapacityBytes;
        this.rawExpectedTightBytes = rawWidth > 0 && rawHeight > 0
                ? (long) rawWidth * (long) rawHeight * 2L : -1L;
        this.rawBufferMatchesTightU16 = rawExpectedTightBytes >= 0
                && rawBufferCapacityBytes >= 0
                && rawExpectedTightBytes == (long) rawBufferCapacityBytes;
        this.rawPixelStrideBytes = rawBufferMatchesTightU16 ? 2 : -1;
        this.rawRowStrideBytes = rawBufferMatchesTightU16 ? rawWidth * 2 : -1;

        this.camera2Cfa = camera2Cfa;
        this.photonEffectiveCfa = photonEffectiveCfa;
        this.resolvedCfa = resolvedCfa;
        this.cfaPattern = cfaPattern;
        this.rawOriginX = 0;
        this.rawOriginY = 0;
        this.rawOriginProven = false;

        this.photonEffectiveBlackLevel = photonEffectiveBlackLevel;
        this.characteristicsBlackLevelPattern = characteristicsBlackLevelPattern;
        this.captureDynamicBlackLevel = captureDynamicBlackLevel;
        this.whiteLevel = whiteLevel;
        this.characteristicsWhiteLevel = characteristicsWhiteLevel;
        this.captureDynamicWhiteLevel = captureDynamicWhiteLevel;

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
        int photonCfa = params != null ? params.cfaPattern & 0xff : -1;
        Integer nativeCfa = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT) : null;
        int camera2Cfa = nativeCfa != null ? nativeCfa : -1;
        int resolvedCfa = camera2Cfa >= 0 ? camera2Cfa : photonCfa;

        float[] photonBlack = photonBlack(params);
        int[] characteristicsBlack = characteristicsBlack(characteristics);
        float[] dynamicBlack = captureResult != null
                ? captureResult.get(CaptureResult.SENSOR_DYNAMIC_BLACK_LEVEL) : null;
        int photonWhite = params != null ? params.whiteLevel : -1;
        Integer charWhite = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        Integer dynamicWhite = captureResult != null
                ? captureResult.get(CaptureResult.SENSOR_DYNAMIC_WHITE_LEVEL) : null;

        Boolean shadingApplied = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED) : null;
        LensShadingMap shadingMap = captureResult != null
                ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP) : null;
        int mapRows = shadingMap != null ? shadingMap.getRowCount() : -1;
        int mapColumns = shadingMap != null ? shadingMap.getColumnCount() : -1;

        return new M9RawSensorDescriptor(rawWidth, rawHeight, rawBufferCapacityBytes,
                camera2Cfa, photonCfa, resolvedCfa, M9CfaResolver.fromCamera2(resolvedCfa),
                photonBlack, characteristicsBlack, copy(dynamicBlack), photonWhite,
                charWhite != null ? charWhite : -1,
                dynamicWhite != null ? dynamicWhite : -1,
                Boolean.TRUE.equals(shadingApplied), shadingMap != null, mapRows, mapColumns,
                params, characteristics, captureResult, captureRequest);
    }

    private static float[] photonBlack(Parameters params) {
        if (params == null || params.blackLevel == null || params.blackLevel.length < 4) return null;
        float[] out = new float[4];
        System.arraycopy(params.blackLevel, 0, out, 0, 4);
        return out;
    }

    private static int[] characteristicsBlack(CameraCharacteristics characteristics) {
        BlackLevelPattern p = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        if (p == null) return null;
        int[] out = new int[4];
        p.copyTo(out, 0);
        return out;
    }

    private static float[] copy(float[] values) {
        if (values == null) return null;
        float[] out = new float[values.length];
        System.arraycopy(values, 0, out, 0, values.length);
        return out;
    }

    public JSONObject toJson() throws Exception {
        JSONObject out = new JSONObject();
        out.put("descriptorVersion", VERSION);
        out.put("scope", "source_raw_description_only_no_pixel_change");

        if (params != null) {
            out.put("photonSettingsCameraId", params.cameraID != null
                    ? String.valueOf(params.cameraID) : JSONObject.NULL);
            out.put("photonLogicalIdInt", params.logicalID);
            out.put("photonPhysicalIdInt", params.physicalID);
            out.put("physicalCameraIdSource",
                    "Photon_Parameters_integer_parser_not_yet_portable_sensor_key");
            out.put("focalLengthMm", params.focalLength);
            out.put("aperture", params.aperture);
            out.put("photonUsedDynamicBlackLevel", params.usedDynamic);
            out.put("photonRawSize", point(params.rawSize));
            if (params.rawSize != null) {
                out.put("photonRawSizeAgreement",
                        params.rawSize.x == rawWidth && params.rawSize.y == rawHeight);
            } else {
                out.put("photonRawSizeAgreement", JSONObject.NULL);
            }
        }

        out.put("rawWidth", rawWidth);
        out.put("rawHeight", rawHeight);
        out.put("rawRowStrideBytes", rawRowStrideBytes >= 0 ? rawRowStrideBytes : JSONObject.NULL);
        out.put("rawPixelStrideBytes", rawPixelStrideBytes >= 0 ? rawPixelStrideBytes : JSONObject.NULL);
        out.put("rawBufferCapacityBytes", rawBufferCapacityBytes);
        out.put("rawExpectedTightU16Bytes", rawExpectedTightBytes);
        out.put("rawBufferMatchesTightU16", rawBufferMatchesTightU16);
        out.put("rawPacking", rawBufferMatchesTightU16
                ? "Photon_renderer_buffer_tightly_packed_uint16"
                : "UNPROVEN_NON_TIGHT_OR_CAPACITY_MISMATCH");

        out.put("camera2ColorFilterArrangement", camera2Cfa >= 0 ? camera2Cfa : JSONObject.NULL);
        out.put("photonEffectiveCfa", photonEffectiveCfa >= 0 ? photonEffectiveCfa : JSONObject.NULL);
        out.put("colorFilterArrangement", resolvedCfa >= 0 ? resolvedCfa : JSONObject.NULL);
        out.put("resolvedCfaSource", camera2Cfa >= 0
                ? "CameraCharacteristics"
                : (photonEffectiveCfa >= 0 ? "Photon_effective_fallback" : "missing"));
        if (camera2Cfa >= 0 && photonEffectiveCfa >= 0) {
            out.put("camera2PhotonCfaAgreement", camera2Cfa == photonEffectiveCfa);
        } else {
            out.put("camera2PhotonCfaAgreement", JSONObject.NULL);
        }
        out.put("resolvedCfaPattern", cfaPattern.name());
        out.put("supportedConventionalBayer", cfaPattern != M9CfaResolver.Pattern.UNSUPPORTED);
        out.put("rawOriginX", rawOriginX);
        out.put("rawOriginY", rawOriginY);
        out.put("rawOriginProven", rawOriginProven);
        out.put("rawOriginEvidence",
                "UNPROVEN_DEVICEPORT1A_do_not_shift_by_active_array_without_buffer_coordinate_proof");
        out.put("resolvedCfaPhase", cfaPattern != M9CfaResolver.Pattern.UNSUPPORTED
                ? M9CfaResolver.localPhaseName(cfaPattern, rawOriginX, rawOriginY) : "UNSUPPORTED");

        out.put("photonEffectiveBlackLevel", jsonOrNull(floats(photonEffectiveBlackLevel)));
        out.put("characteristicsBlackLevelPattern", jsonOrNull(ints(characteristicsBlackLevelPattern)));
        out.put("captureDynamicBlackLevel", jsonOrNull(floats(captureDynamicBlackLevel)));
        out.put("photonCharacteristicsBlackAgreement",
                blackAgreement(photonEffectiveBlackLevel, characteristicsBlackLevelPattern));
        out.put("blackLevelDiagnosticReason",
                "Photon_FillDynamicParameters_reads_static_black_from_global_CaptureController_characteristics; compare_before_source_port");
        out.put("blackLevelPlaneOrder", "2x2_order_phase_not_yet_proven");

        out.put("photonEffectiveWhiteLevel", whiteLevel);
        out.put("characteristicsWhiteLevel",
                characteristicsWhiteLevel >= 0 ? characteristicsWhiteLevel : JSONObject.NULL);
        out.put("captureDynamicWhiteLevel",
                captureDynamicWhiteLevel >= 0 ? captureDynamicWhiteLevel : JSONObject.NULL);
        if (whiteLevel > 0 && characteristicsWhiteLevel > 0) {
            out.put("whiteLevelAgreement", whiteLevel == characteristicsWhiteLevel);
        } else {
            out.put("whiteLevelAgreement", JSONObject.NULL);
        }

        if (characteristics != null) {
            out.put("pixelArraySize", jsonOrNull(size(
                    characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE))));
            out.put("preCorrectionActiveArray", jsonOrNull(rect(
                    characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE))));
            out.put("activeArray", jsonOrNull(rect(
                    characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE))));
            Integer orientation = characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION);
            out.put("sensorOrientation", orientation != null ? orientation : JSONObject.NULL);
            out.put("lensShadingAppliedToRaw", lensShadingAppliedToRaw);

            out.put("referenceIlluminant1",
                    nullableNumber(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1)));
            out.put("referenceIlluminant2",
                    nullableNumber(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2)));
            out.put("calibrationTransform1", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1))));
            out.put("calibrationTransform2", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2))));
            out.put("colorTransform1", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1))));
            out.put("colorTransform2", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2))));
            out.put("forwardMatrix1", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1))));
            out.put("forwardMatrix2", jsonOrNull(matrix(
                    characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2))));
            out.put("matrixSerialization", "Camera2_ColorSpaceTransform_copyElements_row_major");
        }

        out.put("lensShadingMapAvailable", lensShadingMapAvailable);
        out.put("lensShadingMapRows", lensShadingMapRows >= 0 ? lensShadingMapRows : JSONObject.NULL);
        out.put("lensShadingMapColumns", lensShadingMapColumns >= 0 ? lensShadingMapColumns : JSONObject.NULL);
        if (captureResult != null) {
            Integer mapMode = captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE);
            out.put("lensShadingMapModeResult", mapMode != null ? mapMode : JSONObject.NULL);
            Rational[] neutral = captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
            out.put("captureNeutral", jsonOrNull(rationals(neutral)));
        }
        if (captureRequest != null) {
            Integer mapMode = captureRequest.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE);
            out.put("lensShadingMapModeRequest", mapMode != null ? mapMode : JSONObject.NULL);
        }

        out.put("renderUseInThisBuild", false);
        out.put("photographicPipelineFrozen", true);
        return out;
    }

    private static Object jsonOrNull(Object value) {
        return value != null ? value : JSONObject.NULL;
    }

    private static Object blackAgreement(float[] effective, int[] characteristicsBlack) {
        if (effective == null || characteristicsBlack == null
                || effective.length < 4 || characteristicsBlack.length < 4) {
            return JSONObject.NULL;
        }
        for (int i = 0; i < 4; i++) {
            if (Math.abs(effective[i] - characteristicsBlack[i]) > 0.001f) return false;
        }
        return true;
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

    private static JSONArray floats(float[] values) {
        if (values == null) return null;
        JSONArray a = new JSONArray();
        for (float v : values) a.put((double) v);
        return a;
    }

    private static JSONArray rationals(Rational[] values) {
        if (values == null) return null;
        JSONArray a = new JSONArray();
        for (Rational v : values) a.put(v != null ? v.doubleValue() : JSONObject.NULL);
        return a;
    }

    private static JSONObject point(Point p) throws Exception {
        if (p == null) return null;
        JSONObject o = new JSONObject();
        o.put("x", p.x);
        o.put("y", p.y);
        return o;
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

    private static JSONArray matrix(ColorSpaceTransform t) {
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
