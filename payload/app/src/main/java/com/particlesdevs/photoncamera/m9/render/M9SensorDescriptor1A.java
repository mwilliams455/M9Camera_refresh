package com.particlesdevs.photoncamera.m9.render;

import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraMetadata;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.BlackLevelPattern;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.hardware.camera2.params.LensShadingMap;
import android.media.Image;
import android.util.Rational;
import android.util.Size;

import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.processing.render.Parameters;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * M9SENSORPORT1A: metadata-derived description of the physical RAW source.
 *
 * This class is deliberately descriptive in 1A. It does not select photographic
 * behaviour and it does not mutate pixels. Camera IDs and device names are provenance
 * only; source adaptation is driven by the actual RAW/Camera2 contract.
 */
public final class M9SensorDescriptor1A {
    public static final String VERSION = "m9sensorport1a-anyraw-descriptor";

    private final JSONObject json;

    private M9SensorDescriptor1A(JSONObject json) {
        this.json = json;
    }

    public JSONObject toJson() {
        return json;
    }

    public static M9SensorDescriptor1A fromPreviewImage(
            Image raw,
            CameraCharacteristics characteristics,
            CaptureResult result,
            CaptureRequest request,
            int reducedWidth,
            int reducedHeight) throws Exception {
        if (raw == null) throw new IllegalArgumentException("M9SENSORPORT1A preview RAW missing");
        Image.Plane[] planes = raw.getPlanes();
        Image.Plane plane = planes != null && planes.length > 0 ? planes[0] : null;
        int rowStride = plane != null ? plane.getRowStride() : -1;
        int pixelStride = plane != null ? plane.getPixelStride() : -1;
        int capacity = plane != null && plane.getBuffer() != null ? plane.getBuffer().capacity() : -1;

        JSONObject out = base(characteristics, result, request);
        out.put("sourceKind", "camera2_preview_probe_original_RAW_SENSOR");
        out.put("cameraId", JSONObject.NULL);
        out.put("physicalCameraId", activePhysicalId(result));
        out.put("rawFormat", raw.getFormat());
        out.put("rawFormatName", raw.getFormat() == ImageFormat.RAW_SENSOR ? "RAW_SENSOR" : "OTHER");
        out.put("rawWidth", raw.getWidth());
        out.put("rawHeight", raw.getHeight());
        out.put("rawRowStrideBytes", rowStride);
        out.put("rawPixelStrideBytes", pixelStride);
        out.put("rawPlaneCapacityBytes", capacity);
        out.put("rawAcquisitionGeometryObserved", true);
        out.put("rawTightU16",
                raw.getFormat() == ImageFormat.RAW_SENSOR
                        && pixelStride == 2
                        && rowStride == raw.getWidth() * 2
                        && capacity >= rowStride * raw.getHeight());

        out.put("previewReducedWidth", reducedWidth);
        out.put("previewReducedHeight", reducedHeight);
        out.put("previewScaleX", reducedWidth > 0 ? raw.getWidth() / (double) reducedWidth : JSONObject.NULL);
        out.put("previewScaleY", reducedHeight > 0 ? raw.getHeight() / (double) reducedHeight : JSONObject.NULL);
        out.put("previewReduction",
                "CFA_parity_preserving_same-parity_2x2_source-neighbour_average");
        out.put("previewReductionKeepsOriginalSourceDescriptor", true);
        out.put("previewReducedFrameIsNotOriginalSensorGeometry", true);
        out.put("previewGeometryPolicy",
                "retain_original_RAW_descriptor_and_map_reduced_coordinates_to_normalized_source_domain");

        attachOriginEvidence(out, characteristics, raw.getWidth(), raw.getHeight());
        attachFalloffContract(out);
        return new M9SensorDescriptor1A(out);
    }

    public static M9SensorDescriptor1A fromImageFrame(
            ImageFrame frame,
            Parameters params,
            CameraCharacteristics characteristics,
            CaptureResult result,
            CaptureRequest request) throws Exception {
        if (frame == null) throw new IllegalArgumentException("M9SENSORPORT1A ImageFrame missing");
        JSONObject out = base(characteristics, result, request);
        out.put("sourceKind", "still_capture_owned_ImageFrame");
        out.put("cameraId",
                params != null && params.cameraID != null ? String.valueOf(params.cameraID) : JSONObject.NULL);
        out.put("logicalCameraIdInt", params != null ? params.logicalID : JSONObject.NULL);
        out.put("physicalCameraIdInt", params != null ? params.physicalID : JSONObject.NULL);
        out.put("physicalCameraId", activePhysicalId(result));

        out.put("rawFormat", frame.m9SourceImageFormat);
        out.put("rawFormatName",
                frame.m9SourceImageFormat == ImageFormat.RAW_SENSOR ? "RAW_SENSOR" : "UNKNOWN_OR_OTHER");
        out.put("rawWidth", frame.m9SourceImageWidth > 0 ? frame.m9SourceImageWidth : frame.width);
        out.put("rawHeight", frame.m9SourceImageHeight > 0 ? frame.m9SourceImageHeight : frame.height);
        out.put("rawRowStrideBytes", nullablePositive(frame.m9SourceRowStrideBytes));
        out.put("rawPixelStrideBytes", nullablePositive(frame.m9SourcePixelStrideBytes));
        out.put("rawCopyOffsetBytes", frame.m9SourceCopyOffsetBytes);
        out.put("rawCopyCapacityBytes", frame.m9SourceCopyCapacityBytes);
        out.put("rawPlaneCapacityBytes", frame.m9SourcePlaneCapacityBytes);
        out.put("ownedBufferCapacityBytes",
                frame.buffer != null ? frame.buffer.capacity() : JSONObject.NULL);
        out.put("rawAcquisitionGeometryObserved", frame.m9SourceImageWidth > 0 && frame.m9SourceImageHeight > 0);

        int w = frame.m9SourceImageWidth > 0 ? frame.m9SourceImageWidth : frame.width;
        int h = frame.m9SourceImageHeight > 0 ? frame.m9SourceImageHeight : frame.height;
        boolean tight = frame.m9SourceImageFormat == ImageFormat.RAW_SENSOR
                && frame.m9SourcePixelStrideBytes == 2
                && frame.m9SourceRowStrideBytes == w * 2
                && frame.m9SourceCopyOffsetBytes == 0
                && frame.m9SourceCopyCapacityBytes >= (long) w * h * 2L;
        out.put("rawTightU16", tight);
        out.put("aspect169RequestedAtAcquisition", frame.m9SourceAspect169Requested);
        out.put("binningRequestedAtAcquisition", frame.m9SourceBinningRequested);

        if (params != null) {
            out.put("photonEffectiveWhiteLevel", params.whiteLevel);
            out.put("photonEffectiveBlackLevel", floatArray(params.blackLevel));
            out.put("photonCfaPattern", params.cfaPattern & 0xff);
            out.put("focalLengthMmPhoton", params.focalLength);
            out.put("aperturePhoton", params.aperture);
        }

        attachOriginEvidence(out, characteristics, w, h);
        attachFalloffContract(out);
        return new M9SensorDescriptor1A(out);
    }

    private static JSONObject base(
            CameraCharacteristics characteristics,
            CaptureResult result,
            CaptureRequest request) throws Exception {
        JSONObject out = new JSONObject();
        out.put("schema", "m9cam.sensor_descriptor.v1a");
        out.put("revision", "M9SENSORPORT1A_ANYRAW_FALLOFFTGT1A");
        out.put("descriptorVersion", VERSION);
        out.put("photographicPixelMutation", false);
        out.put("cameraIdUsedForPhotographicPolicy", false);
        out.put("physicalCameraIdUsedForPhotographicPolicy", false);
        out.put("manufacturerUsedForPhotographicPolicy", false);
        out.put("focalLengthUsedForPhotographicPolicy", false);

        if (characteristics == null) {
            out.put("cameraCharacteristicsAvailable", false);
            return out;
        }
        out.put("cameraCharacteristicsAvailable", true);
        out.put("rawCapability", hasRawCapability(characteristics));
        out.put("pixelArray", size(characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)));
        out.put("preCorrectionActiveArray",
                rect(characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE)));
        out.put("activeArray",
                rect(characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)));
        out.put("sensorOrientation",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION)));
        out.put("cfaArrangement",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT)));
        out.put("staticWhiteLevel",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL)));
        out.put("staticBlackLevelPattern",
                blackLevel(characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN)));
        out.put("lensShadingAppliedToRaw",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED)));
        out.put("referenceIlluminant1",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1)));
        out.put("referenceIlluminant2",
                nullable(characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2)));
        out.put("cameraCalibration1",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1)));
        out.put("cameraCalibration2",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2)));
        out.put("colorMatrix1",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1)));
        out.put("colorMatrix2",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2)));
        out.put("forwardMatrix1",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1)));
        out.put("forwardMatrix2",
                matrix(characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2)));
        out.put("distortion",
                floatArray(characteristics.get(CameraCharacteristics.LENS_DISTORTION)));

        if (result != null) {
            out.put("dynamicBlackLevel",
                    floatArray(result.get(CaptureResult.SENSOR_DYNAMIC_BLACK_LEVEL)));
            out.put("dynamicWhiteLevel",
                    nullable(result.get(CaptureResult.SENSOR_DYNAMIC_WHITE_LEVEL)));
            out.put("asShotNeutral",
                    rationalArray(result.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT)));
            out.put("focalLengthMm",
                    nullable(result.get(CaptureResult.LENS_FOCAL_LENGTH)));
            out.put("aperture",
                    nullable(result.get(CaptureResult.LENS_APERTURE)));
            out.put("scalerCropRegion",
                    rect(result.get(CaptureResult.SCALER_CROP_REGION)));
            out.put("lensShadingMapModeResult",
                    nullable(result.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE)));
            LensShadingMap map =
                    result.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP);
            out.put("lensShadingMapAvailable", map != null);
            if (map != null) {
                out.put("lensShadingMapRows", map.getRowCount());
                out.put("lensShadingMapColumns", map.getColumnCount());
                out.put("lensShadingMapGainFactorCount", map.getGainFactorCount());
                out.put("lensShadingMapChannelOrder", "R,Geven,Godd,B");
            }
        }
        if (request != null) {
            out.put("lensShadingMapModeRequest",
                    nullable(request.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE)));
        }

        out.put("sourceNormalizationOrder",
                "RAW_GEOMETRY_CFA->BLACK_WHITE_NORMALIZE->SOURCE_SHADING_NORMALIZE->SENSOR_COLOR_NORMALIZE->COMMON_SCENE");
        out.put("commonSceneTargetInput",
                "active_physical_Camera2_DNG_to_XYZ_D50_then_recovered_M9_virtual_sensor");
        return out;
    }

    private static void attachOriginEvidence(
            JSONObject out,
            CameraCharacteristics characteristics,
            int width,
            int height) throws Exception {
        out.put("rawSensorOriginProven", false);
        out.put("rawSensorOriginX", JSONObject.NULL);
        out.put("rawSensorOriginY", JSONObject.NULL);
        String evidence = "unresolved";
        if (characteristics != null) {
            Size pixel = characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE);
            Rect pre = characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE);
            Rect active = characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);
            if (pixel != null && pixel.getWidth() == width && pixel.getHeight() == height) {
                evidence = "dimensions_match_full_pixel_array_candidate_origin_0_0";
            } else if (pre != null && pre.width() == width && pre.height() == height) {
                evidence = "dimensions_match_pre_correction_active_array_candidate_origin_left_top";
            } else if (active != null && active.width() == width && active.height() == height) {
                evidence = "dimensions_match_active_array_candidate_origin_left_top";
            } else {
                evidence = "dimensions_do_not_uniquely_map_to_known_sensor_rectangle";
            }
        }
        out.put("rawSensorOriginEvidence", evidence);
        out.put("rawSensorOriginPolicy",
                "candidate_evidence_only_until_acquisition_copy_and_coordinate_mapping_are_proven");
    }

    private static void attachFalloffContract(JSONObject out) throws Exception {
        out.put("sourceShadingRole", "source_normalization_only_not_M9_look");
        out.put("targetFalloffStage", "after_common_scene_source_normalization");
        out.put("targetFalloffCoordinateSpace", "normalized_image_coordinates_center_0_corner_radius_1");
        out.put("targetFalloffModel", "EV(r)=a2*r^2+a4*r^4+a6*r^6");
        out.put("targetFalloffCalibrationStatus", "PENDING_GENUINE_M9_EVIDENCE");
        out.put("targetFalloffPixelMutationEnabled", false);
        out.put("targetFalloffIdentityGainIn1A", true);
    }

    private static boolean hasRawCapability(CameraCharacteristics c) {
        int[] caps = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES);
        if (caps == null) return false;
        for (int cap : caps) if (cap == CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_RAW) return true;
        return false;
    }

    private static Object activePhysicalId(CaptureResult result) {
        if (result == null) return JSONObject.NULL;
        try {
            String id = result.get(CaptureResult.LOGICAL_MULTI_CAMERA_ACTIVE_PHYSICAL_ID);
            return id != null ? id : JSONObject.NULL;
        } catch (Throwable ignored) {
            return JSONObject.NULL;
        }
    }

    private static Object nullable(Object value) {
        return value != null ? value : JSONObject.NULL;
    }

    private static Object nullablePositive(int value) {
        return value >= 0 ? value : JSONObject.NULL;
    }

    private static Object size(Size s) throws Exception {
        if (s == null) return JSONObject.NULL;
        JSONObject j = new JSONObject();
        j.put("width", s.getWidth());
        j.put("height", s.getHeight());
        return j;
    }

    private static Object rect(Rect r) throws Exception {
        if (r == null) return JSONObject.NULL;
        JSONObject j = new JSONObject();
        j.put("left", r.left);
        j.put("top", r.top);
        j.put("right", r.right);
        j.put("bottom", r.bottom);
        j.put("width", r.width());
        j.put("height", r.height());
        return j;
    }

    private static Object blackLevel(BlackLevelPattern p) {
        if (p == null) return JSONObject.NULL;
        int[] v = new int[4];
        p.copyTo(v, 0);
        JSONArray a = new JSONArray();
        for (int x : v) a.put(x);
        return a;
    }

    private static Object floatArray(float[] v) throws Exception {
        if (v == null) return JSONObject.NULL;
        JSONArray a = new JSONArray();
        for (float x : v) a.put((double) x);
        return a;
    }

    private static Object rationalArray(Rational[] v) throws Exception {
        if (v == null) return JSONObject.NULL;
        JSONArray a = new JSONArray();
        for (Rational x : v) a.put(x != null ? x.doubleValue() : JSONObject.NULL);
        return a;
    }

    private static Object matrix(ColorSpaceTransform t) throws Exception {
        if (t == null) return JSONObject.NULL;
        Rational[] v = new Rational[9];
        t.copyElements(v, 0);
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) {
                Rational x = v[r * 3 + c];
                row.put(x != null ? x.doubleValue() : JSONObject.NULL);
            }
            rows.put(row);
        }
        return rows;
    }
}
