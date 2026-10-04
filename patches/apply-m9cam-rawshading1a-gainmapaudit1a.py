#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-rawshading1a-gainmapaudit1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('RAWSHADING1A missing expected file: ' + rel)
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
audit_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
dng_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java'
renderer = read(renderer_rel)
dng = read(dng_rel)

if 'M9 DNGGAINMAPFIX1A' not in dng:
    raise SystemExit('RAWSHADING1A requires DNGGAINMAPFIX1A baseline')
if 'Parameters params = new Parameters();' not in renderer:
    raise SystemExit('RAWSHADING1A renderer Parameters anchor missing')
if 'RenderCore out = renderCore(frame.buffer, frame.width, frame.height,' not in renderer:
    raise SystemExit('RAWSHADING1A renderCore anchor missing')

# Diagnostic-only scope guard: these photographic/capture components must not change.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

# The audit intentionally uses the live CaptureResult LensShadingMap rather than only
# Parameters.hasGainMap so we can distinguish map presence from Photon's fake/all-ones test.
audit_java = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;
import android.util.Rational;
import android.util.Size;

import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * M9RAWSHADING1A / GAINMAPAUDIT1A.
 *
 * Diagnostic only. This class does not modify RAW pixels, TC20, colour, exposure,
 * DNG metadata, JPEG quality or queue ownership. It records the Camera2 shading
 * semantics needed before an exactly-once Bayer-space correction can be tested.
 *
 * Camera2 LensShadingMap channel order is the API-defined interleaved order:
 * [R, G_even, G_odd, B]. The selected camera is identified from Parameters.cameraID,
 * logicalID/physicalID and the live focal length rather than hard-coded Xiaomi IDs,
 * so one build can audit all four Xiaomi 15 Ultra rear modules.
 */
public final class M9RawShadingAudit1A {
    private static final String TAG = "M9RawShadingAudit1A";
    public static final String SCHEMA = "m9cam.rawshading.v1a.gainmapaudit1a.multilens";
    public static final String CHANNEL_ORDER = "R,Geven,Godd,B";

    private M9RawShadingAudit1A() {}

    public static JSONObject captureAndWrite(Path dngPath,
                                             int frameWidth,
                                             int frameHeight,
                                             Parameters params,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest) {
        long startedNs = System.nanoTime();
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("scope", "diagnostic_only_no_raw_or_jpeg_pixel_change");
            out.put("deviceInvestigation", "Xiaomi_15_Ultra_four_rear_modules_unmapped_by_id_until_live_capture");
            out.put("gainMapChannelOrder", CHANNEL_ORDER);
            out.put("gainMapChannelOrderSource", "Android_Camera2_LensShadingMap_API");
            out.put("gainMapApplicationEnabled", false);
            out.put("fixedTc20ComparisonEnabled", false);
            out.put("phase", "A_metadata_semantics_audit");

            if (params != null) {
                out.put("cameraID", params.cameraID != null ? params.cameraID : JSONObject.NULL);
                out.put("logicalID", params.logicalID);
                out.put("physicalID", params.physicalID);
                out.put("focalLengthMm", params.focalLength);
                out.put("aperture", params.aperture);
                out.put("iso", params.iso);
                out.put("exposureTimeSeconds", params.exposureTime);
                out.put("cfaPattern", params.cfaPattern & 0xff);
                out.put("cfaPatternName", cfaName(params.cfaPattern & 0xff));
                out.put("whiteLevel", params.whiteLevel);
                out.put("blackLevel", floatArray(params.blackLevel));
                out.put("whitePoint", floatArray(params.whitePoint));
                out.put("photonHasGainMap", params.hasGainMap);
                out.put("photonGainMapWidth", params.mapSize != null ? params.mapSize.x : 0);
                out.put("photonGainMapHeight", params.mapSize != null ? params.mapSize.y : 0);
                out.put("photonGainMapArrayLength", params.gainMap != null ? params.gainMap.length : 0);
                out.put("photonSensorPix", rectJson(params.sensorPix));
                if (params.sensorSize != null) {
                    JSONObject sensorSize = new JSONObject();
                    sensorSize.put("widthMm", params.sensorSize.getWidth());
                    sensorSize.put("heightMm", params.sensorSize.getHeight());
                    out.put("sensorPhysicalSize", sensorSize);
                }
            }

            out.put("frameWidth", frameWidth);
            out.put("frameHeight", frameHeight);

            Boolean lensShadingApplied = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED) : null;
            out.put("lensShadingAppliedCharacteristic",
                    lensShadingApplied != null ? lensShadingApplied : JSONObject.NULL);
            out.put("lensShadingAppliedInterpretation",
                    "Camera2 map is complete correction when false and remaining correction when true; do not infer skip/apply from flag alone");

            Rect active = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE) : null;
            Rect preCorrection = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE) : null;
            Size advertisedMapSize = characteristics != null
                    ? characteristics.get(CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE) : null;
            out.put("activeArray", rectJson(active));
            out.put("preCorrectionActiveArray", rectJson(preCorrection));
            if (advertisedMapSize != null) {
                JSONObject s = new JSONObject();
                s.put("width", advertisedMapSize.getWidth());
                s.put("height", advertisedMapSize.getHeight());
                out.put("advertisedShadingMapSize", s);
            } else {
                out.put("advertisedShadingMapSize", JSONObject.NULL);
            }

            Rect crop = captureResult != null ? captureResult.get(CaptureResult.SCALER_CROP_REGION) : null;
            if (crop == null && captureRequest != null) crop = captureRequest.get(CaptureRequest.SCALER_CROP_REGION);
            out.put("scalerCropRegion", rectJson(crop));

            putNullableInt(out, "captureShadingMode",
                    captureResult != null ? captureResult.get(CaptureResult.SHADING_MODE) : null);
            putNullableInt(out, "requestShadingMode",
                    captureRequest != null ? captureRequest.get(CaptureRequest.SHADING_MODE) : null);
            putNullableInt(out, "captureLensShadingMapMode",
                    captureResult != null ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE) : null);
            putNullableInt(out, "requestLensShadingMapMode",
                    captureRequest != null ? captureRequest.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE) : null);
            putNullableInt(out, "captureColorCorrectionMode",
                    captureResult != null ? captureResult.get(CaptureResult.COLOR_CORRECTION_MODE) : null);
            putNullableFloat(out, "focusDistanceDiopters",
                    captureResult != null ? captureResult.get(CaptureResult.LENS_FOCUS_DISTANCE) : null);

            Rational[] neutral = captureResult != null
                    ? captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT) : null;
            if (neutral != null) {
                JSONArray a = new JSONArray();
                for (Rational r : neutral) a.put(r != null ? r.doubleValue() : JSONObject.NULL);
                out.put("sensorNeutralColorPoint", a);
            } else {
                out.put("sensorNeutralColorPoint", JSONObject.NULL);
            }

            LensShadingMap liveMap = captureResult != null
                    ? captureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP) : null;
            out.put("captureResultGainMapPresent", liveMap != null);
            if (liveMap != null) {
                int cols = liveMap.getColumnCount();
                int rows = liveMap.getRowCount();
                float[] factors = new float[liveMap.getGainFactorCount()];
                liveMap.copyGainFactors(factors, 0);
                out.put("gainMapWidth", cols);
                out.put("gainMapHeight", rows);
                out.put("gainMapFactorCount", factors.length);
                out.put("gainMapExpectedFactorCount", cols * rows * 4);
                out.put("gainMapInterleaved", true);
                out.put("gainMapSha256FloatBits", sha256FloatBits(factors));
                out.put("gainMapMinPerChannel", stats(factors, cols, rows, 0));
                out.put("gainMapStatsPerChannel", allChannelStats(factors, cols, rows));
                out.put("gainMapCenterPerChannel", sample(factors, cols, rows, 0.5, 0.5));

                JSONObject corners = new JSONObject();
                corners.put("topLeft", sample(factors, cols, rows, 0.0, 0.0));
                corners.put("topRight", sample(factors, cols, rows, 1.0, 0.0));
                corners.put("bottomLeft", sample(factors, cols, rows, 0.0, 1.0));
                corners.put("bottomRight", sample(factors, cols, rows, 1.0, 1.0));
                out.put("gainMapCornersPerChannel", corners);

                JSONObject edges = new JSONObject();
                edges.put("topMid", sample(factors, cols, rows, 0.5, 0.0));
                edges.put("bottomMid", sample(factors, cols, rows, 0.5, 1.0));
                edges.put("leftMid", sample(factors, cols, rows, 0.0, 0.5));
                edges.put("rightMid", sample(factors, cols, rows, 1.0, 0.5));
                out.put("gainMapEdgeMidpointsPerChannel", edges);

                out.put("gainMapCentreToCornerApproxEv", centreToCornerEv(factors, cols, rows));
            } else {
                out.put("gainMapWidth", 0);
                out.put("gainMapHeight", 0);
                out.put("gainMapFactorCount", 0);
            }

            if (dngPath != null) out.put("dngPath", dngPath.toString());
            out.put("auditElapsedMs", (System.nanoTime() - startedNs) / 1_000_000L);

            Path sidecar = sidecarPath(dngPath);
            if (sidecar != null) {
                Files.write(sidecar, out.toString(2).getBytes(StandardCharsets.UTF_8));
                out.put("sidecarPath", sidecar.toString());
            }
            Log.d(TAG, "RAWSHADING1A cameraID=" + out.optString("cameraID", "?")
                    + " physicalID=" + out.optInt("physicalID", -1)
                    + " focalLengthMm=" + String.format(Locale.US, "%.3f", out.optDouble("focalLengthMm", Double.NaN))
                    + " map=" + out.optInt("gainMapWidth", 0) + "x" + out.optInt("gainMapHeight", 0)
                    + " lensShadingApplied=" + out.opt("lensShadingAppliedCharacteristic"));
        } catch (Throwable t) {
            try {
                out.put("error", t.toString());
                out.put("auditElapsedMs", (System.nanoTime() - startedNs) / 1_000_000L);
            } catch (Exception ignored) {}
            Log.e(TAG, "RAWSHADING1A audit failed", t);
        }
        return out;
    }

    private static JSONArray allChannelStats(float[] factors, int cols, int rows) throws Exception {
        JSONArray out = new JSONArray();
        String[] names = {"R", "Geven", "Godd", "B"};
        for (int c = 0; c < 4; c++) {
            JSONObject s = stats(factors, cols, rows, c);
            s.put("channel", c);
            s.put("name", names[c]);
            out.put(s);
        }
        return out;
    }

    private static JSONObject stats(float[] factors, int cols, int rows, int channel) throws Exception {
        JSONObject out = new JSONObject();
        if (factors == null || cols <= 0 || rows <= 0 || factors.length < cols * rows * 4) {
            out.put("valid", false);
            return out;
        }
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
        double sum = 0.0;
        int n = 0;
        for (int i = channel; i < cols * rows * 4; i += 4) {
            double v = factors[i];
            if (!Double.isFinite(v)) continue;
            min = Math.min(min, v);
            max = Math.max(max, v);
            sum += v;
            n++;
        }
        out.put("valid", n > 0);
        out.put("count", n);
        if (n > 0) {
            out.put("min", min);
            out.put("max", max);
            out.put("mean", sum / n);
        }
        return out;
    }

    private static JSONArray sample(float[] factors, int cols, int rows, double nx, double ny) {
        JSONArray out = new JSONArray();
        for (int c = 0; c < 4; c++) out.put(sampleChannel(factors, cols, rows, nx, ny, c));
        return out;
    }

    private static double sampleChannel(float[] factors, int cols, int rows,
                                        double nx, double ny, int channel) {
        if (factors == null || cols <= 0 || rows <= 0 || factors.length < cols * rows * 4) return Double.NaN;
        if (cols == 1 && rows == 1) return factors[channel];
        double gx = Math.max(0.0, Math.min(1.0, nx)) * Math.max(0, cols - 1);
        double gy = Math.max(0.0, Math.min(1.0, ny)) * Math.max(0, rows - 1);
        int x0 = (int)Math.floor(gx), y0 = (int)Math.floor(gy);
        int x1 = Math.min(cols - 1, x0 + 1), y1 = Math.min(rows - 1, y0 + 1);
        double fx = gx - x0, fy = gy - y0;
        double v00 = factors[((y0 * cols + x0) * 4) + channel];
        double v10 = factors[((y0 * cols + x1) * 4) + channel];
        double v01 = factors[((y1 * cols + x0) * 4) + channel];
        double v11 = factors[((y1 * cols + x1) * 4) + channel];
        double top = v00 + (v10 - v00) * fx;
        double bottom = v01 + (v11 - v01) * fx;
        return top + (bottom - top) * fy;
    }

    private static JSONObject centreToCornerEv(float[] factors, int cols, int rows) throws Exception {
        JSONObject out = new JSONObject();
        String[] names = {"R", "Geven", "Godd", "B"};
        double[][] p = {{0,0},{1,0},{0,1},{1,1}};
        for (int c = 0; c < 4; c++) {
            double centre = sampleChannel(factors, cols, rows, 0.5, 0.5, c);
            double cornerMean = 0.0;
            for (double[] xy : p) cornerMean += sampleChannel(factors, cols, rows, xy[0], xy[1], c);
            cornerMean /= 4.0;
            double ev = centre > 0.0 && cornerMean > 0.0 ? Math.log(cornerMean / centre) / Math.log(2.0) : Double.NaN;
            out.put(names[c], ev);
        }
        return out;
    }

    private static String sha256FloatBits(float[] values) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            ByteBuffer bb = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN);
            for (float v : values) {
                bb.clear();
                bb.putInt(Float.floatToRawIntBits(v));
                md.update(bb.array());
            }
            byte[] digest = md.digest();
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) sb.append(String.format(Locale.US, "%02x", b & 0xff));
            return sb.toString();
        } catch (Exception e) {
            return "sha256_error:" + e.getClass().getSimpleName();
        }
    }

    private static Path sidecarPath(Path dngPath) {
        if (dngPath == null || dngPath.getFileName() == null) return null;
        String name = dngPath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        String stem = dot > 0 ? name.substring(0, dot) : name;
        return dngPath.resolveSibling(stem + "_M9_RAWSHADING1A.json");
    }

    private static JSONObject rectJson(Rect r) throws Exception {
        if (r == null) return null;
        JSONObject out = new JSONObject();
        out.put("left", r.left);
        out.put("top", r.top);
        out.put("right", r.right);
        out.put("bottom", r.bottom);
        out.put("width", r.width());
        out.put("height", r.height());
        return out;
    }

    private static JSONArray floatArray(float[] values) {
        if (values == null) return null;
        JSONArray out = new JSONArray();
        for (float v : values) out.put(v);
        return out;
    }

    private static void putNullableInt(JSONObject out, String key, Integer value) throws Exception {
        out.put(key, value != null ? value : JSONObject.NULL);
    }

    private static void putNullableFloat(JSONObject out, String key, Float value) throws Exception {
        out.put(key, value != null ? value : JSONObject.NULL);
    }

    private static String cfaName(int cfa) {
        switch (cfa) {
            case 0: return "RGGB";
            case 1: return "GRBG";
            case 2: return "GBRG";
            case 3: return "BGGR";
            case 4: return "RGB";
            case 5: return "MONO";
            case 6: return "NIR";
            default: return "UNKNOWN_" + cfa;
        }
    }
}
'''
write(audit_rel, audit_java)

# Capture the audit immediately after Parameters has consumed Camera2 metadata. The
# separate sidecar is written before renderCore so a non-primary lens can still yield
# useful semantics even if the main-camera-calibrated M9 renderer later fails.
anchor = '''            params.FillDynamicParameters(captureResult, captureRequest, iso);\n            params.cameraRotation = cameraRotation;\n'''
insert = '''            params.FillDynamicParameters(captureResult, captureRequest, iso);\n            params.cameraRotation = cameraRotation;\n            // M9RAWSHADING1A: metadata/semantics only. No GainMap is applied to RAW here.\n            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(\n                    dngPath, frame.width, frame.height, params, characteristics, captureResult, captureRequest);\n'''
if insert not in renderer:
    count = renderer.count(anchor)
    if count != 1:
        raise SystemExit(f'RAWSHADING1A parameter anchor count {count}, expected 1')
    renderer = renderer.replace(anchor, insert, 1)

# Also embed the audit in the normal renderer diagnostics when rendering succeeds.
diag_anchor = '''            JSONObject diag = out.diagnostics;\n            diag.put("status", "success");\n'''
diag_insert = '''            JSONObject diag = out.diagnostics;\n            diag.put("rawShadingAudit1A", rawShadingAudit1A);\n            diag.put("rawShadingGainMapApplied", false);\n            diag.put("rawShadingPhase", "A_metadata_semantics_audit");\n            diag.put("status", "success");\n'''
if diag_insert not in renderer:
    count = renderer.count(diag_anchor)
    if count != 1:
        raise SystemExit(f'RAWSHADING1A diagnostics anchor count {count}, expected 1')
    renderer = renderer.replace(diag_anchor, diag_insert, 1)

write(renderer_rel, renderer)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit('RAWSHADING1A scope violation: frozen file changed: ' + rel)

# Explicit source guards against accidentally turning Phase A into a photographic change.
renderer_after = read(renderer_rel)
if 'rawShadingGainMapApplied", false' not in renderer_after:
    raise SystemExit('RAWSHADING1A renderer diagnostic marker missing')
if 'renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation)' not in renderer_after:
    raise SystemExit('RAWSHADING1A renderCore call changed; Phase A must not pass GainMap into rendering')

print('M9RAWSHADING1A GAINMAPAUDIT1A applied')
print(' - phase A only: no RAW/JPEG pixel changes and no GainMap application')
print(' - writes *_M9_RAWSHADING1A.json before renderCore')
print(' - logs Camera2 lens-shading semantics, live map statistics, camera/physical ID, focal length, CFA and geometry')
print(' - one diagnostic build can audit all four Xiaomi 15 Ultra rear modules without hard-coded camera IDs')
