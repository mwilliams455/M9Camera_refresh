package com.particlesdevs.photoncamera.m9.render;

import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.os.Build;
import android.util.Size;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;
import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Set;

/** DEVICEPORT1A active descriptor + rear RAW inventory. Diagnostic only. */
public final class M9DevicePortAudit1A {
    private static final String TAG = "M9DevicePort1A";
    public static final String SCHEMA = "m9cam.deviceport.v1a.cfaabstract1a";

    private M9DevicePortAudit1A() {}

    public static JSONObject captureAndWrite(Path dngPath,
                                             int rawWidth,
                                             int rawHeight,
                                             int rawBufferCapacityBytes,
                                             Parameters params,
                                             CameraCharacteristics activeCharacteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("scope", "diagnostic_only_before_frozen_rggb_render_gate");
            out.put("photographicPixelChange", false);
            out.put("toneExposureColorSharpnessPolicyChanged", false);

            M9RawSensorDescriptor descriptor = M9RawSensorDescriptor.fromActive(
                    rawWidth, rawHeight, rawBufferCapacityBytes, params,
                    activeCharacteristics, captureResult, captureRequest);
            out.put("activeRawSensorDescriptor", descriptor.toJson());
            out.put("rearRawCameraInventory", enumerateRearRawCameras());
            out.put("unsupportedCfaFailsClosed", true);
            out.put("cfaResolverVersion", M9RawSensorDescriptor.VERSION);

            if (dngPath != null) out.put("dngPath", dngPath.toString());
            Path sidecar = sidecarPath(dngPath);
            if (sidecar != null) {
                out.put("sidecarPath", sidecar.toString());
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean persisted = M9DiagnosticSidecarIO.persist(
                        sidecar, frozen, "deviceport1a_raw_sensor_probe");
                out.put("sidecarPersisted", persisted);
            }

            Log.d(TAG, "DEVICEPORT1A active CFA="
                    + descriptor.camera2Cfa + "/" + descriptor.cfaPattern.name()
                    + " RAW=" + rawWidth + "x" + rawHeight
                    + " originProven=" + descriptor.rawOriginProven);
        } catch (Throwable t) {
            try {
                out.put("error", t.toString());
            } catch (Exception ignored) {}
            Log.e(TAG, "DEVICEPORT1A probe failed", t);
        }
        return out;
    }

    private static JSONArray enumerateRearRawCameras() {
        JSONArray inventory = new JSONArray();
        Context context = PhotonCamera.getAppContext();
        if (context == null) return inventory;
        CameraManager manager = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);
        if (manager == null) return inventory;

        try {
            for (String cameraId : manager.getCameraIdList()) {
                CameraCharacteristics c = manager.getCameraCharacteristics(cameraId);
                Integer facing = c.get(CameraCharacteristics.LENS_FACING);
                if (facing == null || facing != CameraCharacteristics.LENS_FACING_BACK) continue;

                JSONObject logical = staticCameraJson(cameraId, c);
                logical.put("inventoryRole", "rear_camera_id");
                inventory.put(logical);

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    Set<String> physicalIds = c.getPhysicalCameraIds();
                    if (physicalIds != null) {
                        for (String physicalId : physicalIds) {
                            JSONObject p = new JSONObject();
                            p.put("cameraId", physicalId);
                            p.put("parentLogicalCameraId", cameraId);
                            p.put("inventoryRole", "physical_member");
                            try {
                                CameraCharacteristics pc = manager.getCameraCharacteristics(physicalId);
                                JSONObject details = staticCameraJson(physicalId, pc);
                                copy(details, p);
                                p.put("characteristicsReadable", true);
                            } catch (Throwable physicalError) {
                                p.put("characteristicsReadable", false);
                                p.put("characteristicsError", physicalError.toString());
                            }
                            inventory.put(p);
                        }
                    }
                }
            }
        } catch (Throwable t) {
            JSONObject error = new JSONObject();
            try {
                error.put("inventoryError", t.toString());
                inventory.put(error);
            } catch (Exception ignored) {}
        }
        return inventory;
    }

    private static JSONObject staticCameraJson(String cameraId,
                                               CameraCharacteristics c) throws Exception {
        JSONObject o = new JSONObject();
        o.put("cameraId", cameraId);
        o.put("lensFacing", nullable(c.get(CameraCharacteristics.LENS_FACING)));

        int[] capabilities = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES);
        o.put("rawCapability",
                contains(capabilities, CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW));
        o.put("logicalMultiCameraCapability",
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.P
                        && contains(capabilities,
                        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA));
        o.put("capabilities", ints(capabilities));

        Integer cfa = c.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT);
        int cfaValue = cfa != null ? cfa : -1;
        o.put("colorFilterArrangement", cfaValue);
        o.put("resolvedCfaPattern", M9CfaResolver.fromCamera2(cfaValue).name());
        o.put("supportedConventionalBayer", M9CfaResolver.isSupported(cfaValue));

        Integer white = c.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL);
        o.put("whiteLevel", white != null ? white : JSONObject.NULL);
        o.put("sensorOrientation", nullable(c.get(CameraCharacteristics.SENSOR_ORIENTATION)));
        o.put("lensShadingAppliedToRaw",
                nullable(c.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED)));
        o.put("focalLengthsMm",
                floats(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)));

        StreamConfigurationMap map =
                c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
        JSONArray rawSizes = new JSONArray();
        if (map != null) {
            Size[] sizes = map.getOutputSizes(ImageFormat.RAW_SENSOR);
            if (sizes != null) {
                for (Size s : sizes) {
                    JSONObject so = new JSONObject();
                    so.put("width", s.getWidth());
                    so.put("height", s.getHeight());
                    rawSizes.put(so);
                }
            }
        }
        o.put("rawSensorSizes", rawSizes);
        return o;
    }

    private static void copy(JSONObject source, JSONObject target) throws Exception {
        JSONArray names = source.names();
        if (names == null) return;
        for (int i = 0; i < names.length(); i++) {
            String key = names.getString(i);
            if (!target.has(key)) target.put(key, source.get(key));
        }
    }

    private static boolean contains(int[] values, int needle) {
        if (values == null) return false;
        for (int v : values) if (v == needle) return true;
        return false;
    }

    private static Object nullable(Object value) {
        return value != null ? value : JSONObject.NULL;
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

    private static Path sidecarPath(Path dngPath) {
        if (dngPath == null) return null;
        String name = dngPath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        String stem = dot > 0 ? name.substring(0, dot) : name;
        return dngPath.resolveSibling(stem + "_M9_DEVICEPORT1A.json");
    }
}
