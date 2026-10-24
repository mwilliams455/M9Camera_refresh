package com.particlesdevs.photoncamera.m9.provenance;

import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureResult;
import com.particlesdevs.photoncamera.processing.render.Parameters;
import org.json.JSONObject;

/**
 * Read-only per-still physical RAW source provenance, shared M9 and Monochrom.
 *
 * This is the missing joined receipt, NOT a second calibration process.
 * Reuses the two existing output audit objects and their exact Camera2 source.
 * Never changes any RAW, DNG, colour matrix, LensShadingMap or JPEG pixel.
 */
public final class M9SourceProvenance1A {
    public static final String SCHEMA="m9cam.sourceprovenance.v1a.exact_capture";
    private M9SourceProvenance1A(){}

    public static JSONObject describe(Parameters p,
                                     CameraCharacteristics characteristics,
                                     CaptureResult physicalResult,
                                     JSONObject calibration,
                                     JSONObject shading) {
        JSONObject out=new JSONObject();
        try {
            out.put("schema",SCHEMA);
            out.put("photoPixelsChanged",false);
            out.put("dngMetadataChanged",false);
            out.put("sourceLookSelectedByLensId",false);
            out.put("comparisonPolicy",
                    "physical_source_metadata_vs_prior_captures_read_only");
            String selected=p==null||p.cameraID==null?"":p.cameraID;
            out.put("sourceCameraSelector",selected);
            out.put("logicalId",p==null?JSONObject.NULL:p.logicalID);
            out.put("physicalId",p==null?JSONObject.NULL:p.physicalID);
            out.put("rawCfaPattern",p==null?JSONObject.NULL:(p.cfaPattern & 255));
            out.put("rawBlackLevels",p==null?JSONObject.NULL:array(p.blackLevel));
            out.put("rawWhiteLevel",p==null?JSONObject.NULL:p.whiteLevel);
            out.put("rawNeutralInActiveParameters",p==null?JSONObject.NULL:array(p.whitePoint));
            out.put("sourceCalibrationAuditPresent",calibration!=null);
            out.put("sourceShadingAuditPresent",shading!=null);
            if(calibration!=null) {
                out.put("sourceCalibrationRevision",
                        calibration.optString("sourceCalibrationRevision","unknown"));
                out.put("nativeMetadataComplete",
                        calibration.optBoolean("nativeDualIlluminantMetadataComplete",false));
                out.put("activeMetadataDiffersFromNative",
                        calibration.opt("activeMetadataDiffersFromNative")!=null?
                                calibration.opt("activeMetadataDiffersFromNative"):JSONObject.NULL);
                out.put("sourceCalibrationError",
                        calibration.has("error")?calibration.opt("error"):JSONObject.NULL);
                out.put("sourceCalibrationPhysicalId",calibration.has("physicalID")?
                        calibration.opt("physicalID"):JSONObject.NULL);
                out.put("nativeSceneSpaceCandidate",
                        calibration.optString("nativeSceneSpaceCandidate","unknown"));
                out.put("hasNativeSensorToXYZD50",
                        calibration.opt("nativeSensorToXYZD50") instanceof org.json.JSONArray);
            }
            if(shading!=null) {
                out.put("sourceShadingRevision",shading.optString("schema","unknown"));
                out.put("lensShadingApplied",shading.has("lensShadingAppliedCharacteristic")
                        ?shading.opt("lensShadingAppliedCharacteristic"):JSONObject.NULL);
                out.put("sourceShadingError",shading.has("error")?
                        shading.opt("error"):JSONObject.NULL);
                out.put("lensShadingMapPlanes",
                        shading.optString("gainMapChannelOrder",
                                "R,Geven,Godd,B"));
                out.put("sourceShadingPhysicalId",shading.has("physicalID")?
                        shading.opt("physicalID"):JSONObject.NULL);
                out.put("captureShadingMode",shading.has("captureShadingMode")?
                        shading.opt("captureShadingMode"):JSONObject.NULL);
            }
            if(physicalResult!=null){
                out.put("physicalResultPresent",true);
                out.put("physicalFrameNumber",physicalResult.getFrameNumber());
                Long stamp=physicalResult.get(CaptureResult.SENSOR_TIMESTAMP);
                out.put("physicalSensorTimestampNs",stamp==null?JSONObject.NULL:stamp);
                android.util.Rational[] neutral=physicalResult.get(
                        CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
                out.put("physicalResultNeutralPresent",neutral!=null && neutral.length==3);
                out.put("physicalResultHasLensShadingMap",
                        physicalResult.get(CaptureResult.STATISTICS_LENS_SHADING_MAP)!=null);
            } else {
                out.put("physicalResultPresent",false);
                out.put("physicalFrameNumber",JSONObject.NULL);
                out.put("physicalSensorTimestampNs",JSONObject.NULL);
                out.put("physicalResultNeutralPresent",false);
                out.put("physicalResultHasLensShadingMap",false);
            }
            android.graphics.Rect active=characteristics==null?null:
                    characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);
            android.graphics.Rect precorrected=characteristics==null?null:
                    characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE);
            out.put("physicalCharacteristicsPresent",characteristics!=null);
            out.put("activeArray",rect(active));
            out.put("preCorrectionActiveArray",rect(precorrected));
            // Unknown/missing source must not be silently interpreted as
            // successful cross-lens colour calibration or shading application.
            boolean core=characteristics!=null && physicalResult!=null
                    && p!=null && calibration!=null && shading!=null
                    && !calibration.has("error") && !shading.has("error")
                    && p.whiteLevel>0 && p.blackLevel!=null
                    && p.blackLevel.length==4 && active!=null;
            boolean same=true;
            if(p!=null&&calibration!=null&&calibration.has("physicalID"))
                same &= p.physicalID==calibration.optInt("physicalID",Integer.MIN_VALUE);
            if(p!=null&&shading!=null&&shading.has("physicalID"))
                same &= p.physicalID==shading.optInt("physicalID",Integer.MIN_VALUE);
            out.put("perCapturePhysicalIdCrossAuditAgrees",same);
            out.put("status",!same?"PHYSICAL_ID_MISMATCH":core?
                    "CAPTURE_SOURCE_PRESENT":"INCOMPLETE_SOURCE_EVIDENCE");
            out.put("actualCrossLensColorEquivalenceProven",false);
            out.put("lensShadingAppliedExactlyOnceProven",false);
            out.put("nextComparison",
                    "pair_by_physical_camera_and_scene_then_compare_source_neutral_matrix_and_shading");
        } catch(Throwable caught) {
            try{
                out.put("status","SOURCE_RECEIPT_ERROR");
                out.put("sourceReceiptErrorType",caught.getClass().getSimpleName());
            }catch(Exception ignored){}
        }
        return out;
    }
    private static Object array(float[] values){
        if(values==null)return JSONObject.NULL;
        org.json.JSONArray out=new org.json.JSONArray();
        for(float x:values)out.put(Float.isFinite(x)?(double)x:JSONObject.NULL);
        return out;
    }
    private static Object rect(android.graphics.Rect x){
        if(x==null)return JSONObject.NULL;
        return new org.json.JSONArray().put(x.left).put(x.top).put(x.right).put(x.bottom);
    }
}
