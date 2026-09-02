package com.particlesdevs.photoncamera.m9;

import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.BlackLevelPattern;
import android.util.Range;
import android.util.Rational;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class M9CaptureMetadataWriter {
    private static final String TAG="M9Metadata"; private M9CaptureMetadataWriter(){}
    public static Path sidecarPath(Path dngPath){String f=dngPath.getFileName().toString();int dot=f.lastIndexOf('.');String stem=dot>0?f.substring(0,dot):f;return dngPath.resolveSibling(stem+"_M9.json");}
    public static boolean write(Path dngPath, ImageFrame frame, CameraCharacteristics characteristics, CaptureResult result, CaptureRequest request, int cameraRotation){
        Path jsonPath=sidecarPath(dngPath); try {
            JSONObject root=new JSONObject();root.put("schema","m9cam.photon.capture.v2");root.put("route",M9Config.ROUTE.name());root.put("dng",dngPath.getFileName().toString());root.put("cameraId",PhotonCamera.getSettings().mCameraID);putCameraIds(root,PhotonCamera.getSettings().mCameraID);
            JSONObject raw=new JSONObject();raw.put("width",frame.width);raw.put("height",frame.height);raw.put("timestampNs",frame.timestamp);raw.put("cameraRotationDegrees",cameraRotation);put(raw,"cfa",characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT));put(raw,"whiteLevel",characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL));putBlackLevel(raw,characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN));putRange(raw,"sensitivityRange",characteristics.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE));put(raw,"maxAnalogSensitivity",characteristics.get(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY));root.put("raw",raw);
            JSONObject capture=new JSONObject();put(capture,"iso",result.get(CaptureResult.SENSOR_SENSITIVITY));put(capture,"exposureTimeNs",result.get(CaptureResult.SENSOR_EXPOSURE_TIME));put(capture,"postRawSensitivityBoost",result.get(CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST));put(capture,"aperture",result.get(CaptureResult.LENS_APERTURE));put(capture,"focalLengthMm",result.get(CaptureResult.LENS_FOCAL_LENGTH));put(capture,"aeState",result.get(CaptureResult.CONTROL_AE_STATE));put(capture,"afState",result.get(CaptureResult.CONTROL_AF_STATE));put(capture,"awbState",result.get(CaptureResult.CONTROL_AWB_STATE));put(capture,"aeMode",result.get(CaptureResult.CONTROL_AE_MODE));put(capture,"awbMode",result.get(CaptureResult.CONTROL_AWB_MODE));put(capture,"sensorFrameDurationNs",result.get(CaptureResult.SENSOR_FRAME_DURATION));putNeutral(capture,result.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT));root.put("captureResult",capture);
            JSONObject requested=new JSONObject();put(requested,"iso",request.get(CaptureRequest.SENSOR_SENSITIVITY));put(requested,"exposureTimeNs",request.get(CaptureRequest.SENSOR_EXPOSURE_TIME));put(requested,"postRawSensitivityBoost",request.get(CaptureRequest.CONTROL_POST_RAW_SENSITIVITY_BOOST));put(requested,"aeMode",request.get(CaptureRequest.CONTROL_AE_MODE));put(requested,"exposureCompensation",request.get(CaptureRequest.CONTROL_AE_EXPOSURE_COMPENSATION));root.put("captureRequest",requested);
            JSONObject sensor=new JSONObject();if(characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)!=null){sensor.put("physicalWidthMm",characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE).getWidth());sensor.put("physicalHeightMm",characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE).getHeight());}if(characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)!=null)sensor.put("activeArray",characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE).flattenToString());root.put("sensor",sensor);
            root.put("photonExposureDecision",M9ExposureDiagnostics.snapshotJson());
            root.put("m9ModernExposureDecision",M9ModernExposurePolicy.snapshotJson());
            JSONObject motion=M9SubjectMotionAnalyzer.snapshotJson();JSONObject dyn=root.optJSONObject("photonExposureDecision")!=null?root.optJSONObject("photonExposureDecision").optJSONObject("dynamicScaling"):null;if(dyn!=null&&dyn.has("gyroFilteredShakiness")){int gyro=dyn.optInt("gyroFilteredShakiness",-1);motion.put("gyroFilteredShakiness",gyro);double imageGlobal=motion.optDouble("globalMotionMagnitude",0.0);boolean imageReliable=motion.optBoolean("motionEstimateReliable",false);boolean disagreement=gyro>=500&&imageGlobal<=0.50;motion.put("gyroImageMotionDisagreement",disagreement);if(disagreement)motion.put("gyroImageMotionDisagreementReason",imageReliable?"high gyro motion but image global displacement remained near zero":"high gyro motion with low-confidence image motion estimate");}root.put("subjectMotion",motion);
            OutputStream safOut=SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());if(safOut!=null){try(OutputStream out=safOut){out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));out.flush();}}else{try(OutputStream out=Files.newOutputStream(jsonPath)){out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));out.flush();}}Log.d(TAG,"Saved sidecar: "+jsonPath);return true;
        } catch(Exception e){Log.e(TAG,"Unable to save M9 metadata: "+Log.getStackTraceString(e));return false;}
    }
    private static void putCameraIds(JSONObject root,String cameraId)throws Exception{if(cameraId==null)return;if(cameraId.contains("-")){String[] ids=cameraId.split("-",2);root.put("logicalCameraId",ids[0]);root.put("physicalCameraId",ids[1]);}else{root.put("logicalCameraId",cameraId);root.put("physicalCameraId",cameraId);}}
    private static void put(JSONObject o,String n,Object v)throws Exception{if(v!=null)o.put(n,v);}
    private static void putRange(JSONObject o,String n,Range<Integer> r)throws Exception{if(r==null)return;JSONArray a=new JSONArray();a.put(r.getLower());a.put(r.getUpper());o.put(n,a);}
    private static void putBlackLevel(JSONObject o,BlackLevelPattern p)throws Exception{if(p==null)return;JSONArray a=new JSONArray();a.put(p.getOffsetForIndex(0,0));a.put(p.getOffsetForIndex(1,0));a.put(p.getOffsetForIndex(0,1));a.put(p.getOffsetForIndex(1,1));o.put("blackLevelPattern",a);}
    private static void putNeutral(JSONObject o,Rational[] n)throws Exception{if(n==null)return;JSONArray a=new JSONArray();for(Rational r:n)a.put(r.doubleValue());o.put("neutralColorPoint",a);}
}
