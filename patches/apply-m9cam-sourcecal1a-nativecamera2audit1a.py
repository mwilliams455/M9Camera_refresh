#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourcecal1a-nativecamera2audit1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1A missing expected file: ' + rel)
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
source_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
renderer = read(renderer_rel)

if 'M9RawShadingAudit1A.captureAndWrite(' not in renderer:
    raise SystemExit('SOURCECAL1A requires RAWSHADING1A audit baseline')
if 'params.FillDynamicParameters(captureResult, captureRequest, iso);' not in renderer:
    raise SystemExit('SOURCECAL1A dynamic-parameter anchor missing')

# Diagnostic-only scope. Pixel/capture components are frozen before and after this patch.
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

source_java = r'''package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.util.Rational;

import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;
import com.particlesdevs.photoncamera.processing.render.Converter;
import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Locale;

/**
 * M9SOURCECAL1A / NATIVECAMERA2AUDIT1A.
 *
 * Diagnostic-only audit of the Xiaomi source-camera characterization supplied by
 * Camera2/DNG semantics. It deliberately computes a second, native-only sensor->XYZ
 * transform directly from CameraCharacteristics, independently of any Photon
 * sensor-specific/DCP override. Nothing from this helper is fed into rendering.
 *
 * Purpose: establish whether each Xiaomi 15 Ultra physical RAW camera can be mapped
 * into one common scene-referred colour space without a Cobalt runtime dependency,
 * while the already recovered Leica M9 firmware remains the separate target renderer.
 */
public final class M9SourceCalibrationAudit1A {
    private static final String TAG = "M9SourceCalAudit1A";
    public static final String SCHEMA = "m9cam.sourcecal.v1a.nativecamera2audit1a.multilens";

    private M9SourceCalibrationAudit1A() {}

    public static JSONObject captureAndWrite(Path dngPath,
                                             Parameters params,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult) {
        long startedNs = System.nanoTime();
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("scope", "diagnostic_only_no_raw_or_jpeg_pixel_change");
            out.put("sourceModelGoal", "physical_Xiaomi_RAW_to_common_scene_XYZ_without_Cobalt_runtime_dependency");
            out.put("targetModel", "Leica_M9_firmware_renderer_separate_and_frozen");
            out.put("nativeTransformAppliedToRender", false);
            out.put("cobaltRuntimeDependencyChanged", false);
            out.put("phase", "A_native_metadata_and_transform_audit");

            if (params != null) {
                out.put("cameraID", params.cameraID != null ? params.cameraID : JSONObject.NULL);
                out.put("logicalID", params.logicalID);
                out.put("physicalID", params.physicalID);
                out.put("focalLengthMm", params.focalLength);
                out.put("aperture", params.aperture);
                out.put("iso", params.iso);
                out.put("exposureTimeSeconds", params.exposureTime);
                out.put("cfaPattern", params.cfaPattern & 0xff);
                out.put("whiteLevel", params.whiteLevel);
                out.put("blackLevel", array(params.blackLevel));
                out.put("activeWhitePoint", array(params.whitePoint));

                // These are the transforms actually held by Photon after ReCalcColor().
                // They may reflect a sensor-specific profile override; keep them as the
                // active-path comparison, never as the native-only source of truth.
                out.put("activeCalibrationIlluminant1", params.calibrationIlluminant1);
                out.put("activeCalibrationIlluminant2", params.calibrationIlluminant2);
                out.put("activeCalibrationTransform1", matrix(params.calibrationTransform1));
                out.put("activeCalibrationTransform2", matrix(params.calibrationTransform2));
                out.put("activeColorMatrix1", matrix(params.ColorMatrix1));
                out.put("activeColorMatrix2", matrix(params.ColorMatrix2));
                out.put("activeForwardMatrix1", matrix(params.ForwardTransform1));
                out.put("activeForwardMatrix2", matrix(params.ForwardTransform2));
                out.put("activeSensorToProPhoto", matrix(params.sensorToProPhoto));
                out.put("activeHueSatMapPresent", params.HSVMap != null && params.HSVMap.length > 0);
                out.put("activeHueSatMapHueDivisions", params.HSVMapSize != null && params.HSVMapSize.length > 0 ? params.HSVMapSize[0] : 0);
                out.put("activeHueSatMapSatDivisions", params.HSVMapSize != null && params.HSVMapSize.length > 1 ? params.HSVMapSize[1] : 0);
            }

            int ref1 = number(characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1) : null, -1);
            int ref2 = number(characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2) : null, ref1);
            out.put("nativeReferenceIlluminant1", ref1);
            out.put("nativeReferenceIlluminant2", ref2);

            ColorSpaceTransform nativeCal1 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1) : null;
            ColorSpaceTransform nativeCal2 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2) : null;
            ColorSpaceTransform nativeCm1 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1) : null;
            ColorSpaceTransform nativeCm2 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2) : null;
            ColorSpaceTransform nativeFm1 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1) : null;
            ColorSpaceTransform nativeFm2 = characteristics != null
                    ? characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2) : null;

            float[] cal1 = transform(nativeCal1);
            float[] cal2 = transform(nativeCal2);
            float[] cm1 = transform(nativeCm1);
            float[] cm2 = transform(nativeCm2);
            float[] fm1 = transform(nativeFm1);
            float[] fm2 = transform(nativeFm2);

            out.put("nativeCalibrationTransform1", matrix(cal1));
            out.put("nativeCalibrationTransform2", matrix(cal2));
            out.put("nativeColorMatrix1", matrix(cm1));
            out.put("nativeColorMatrix2", matrix(cm2));
            out.put("nativeForwardMatrix1", matrix(fm1));
            out.put("nativeForwardMatrix2", matrix(fm2));

            Rational[] neutralR = captureResult != null
                    ? captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT) : null;
            float[] neutral = rationalVector(neutralR);
            out.put("nativeSensorNeutralColorPoint", array(neutral));

            ColorSpaceTransform captureCct = captureResult != null
                    ? captureResult.get(CaptureResult.COLOR_CORRECTION_TRANSFORM) : null;
            out.put("captureColorCorrectionTransform", matrix(transform(captureCct)));

            boolean nativeComplete = ref1 >= 0 && ref2 >= 0
                    && valid3x3(cal1) && valid3x3(cal2)
                    && valid3x3(cm1) && valid3x3(cm2)
                    && valid3x3(fm1) && valid3x3(fm2)
                    && neutral != null && neutral.length >= 3;
            out.put("nativeDualIlluminantMetadataComplete", nativeComplete);

            if (nativeComplete) {
                float[] ncm1 = cm1.clone();
                float[] ncm2 = cm2.clone();
                float[] nfm1 = fm1.clone();
                float[] nfm2 = fm2.clone();
                Converter.normalizeFM(ncm1);
                Converter.normalizeFM(ncm2);
                Converter.normalizeFM(nfm1);
                Converter.normalizeFM(nfm2);

                double factor = Converter.findDngInterpolationFactor(
                        ref1, ref2, cal1, cal2, ncm1, ncm2, neutral);
                float[] nativeSensorToXyzD50 = new float[9];
                Converter.calculateCameraToXYZD50Transform(
                        nfm1, nfm2, cal1, cal2, neutral, factor, nativeSensorToXyzD50);

                out.put("nativeInterpolationFactor", factor);
                out.put("nativeSensorToXYZD50", matrix(nativeSensorToXyzD50));
                out.put("nativeSceneSpaceCandidate", "XYZ_D50");
                out.put("nativeTransformCalculation",
                        "Photon_Converter_DNG_dual_illuminant_math_using_only_CameraCharacteristics_and_live_neutral");

                if (params != null) {
                    out.put("activeMetadataDiffersFromNative",
                            differs(params.calibrationTransform1, cal1)
                                    || differs(params.calibrationTransform2, cal2)
                                    || differs(params.ColorMatrix1, cm1)
                                    || differs(params.ColorMatrix2, cm2)
                                    || differs(params.ForwardTransform1, fm1)
                                    || differs(params.ForwardTransform2, fm2));
                }
            } else {
                out.put("nativeInterpolationFactor", JSONObject.NULL);
                out.put("nativeSensorToXYZD50", JSONObject.NULL);
                out.put("nativeSceneSpaceCandidate", JSONObject.NULL);
            }

            if (dngPath != null) out.put("dngPath", dngPath.toString());
            out.put("auditElapsedMs", (System.nanoTime() - startedNs) / 1_000_000L);

            Path sidecar = sidecarPath(dngPath);
            if (sidecar != null) {
                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticSidecarIO.SCHEMA);
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean persisted = M9DiagnosticSidecarIO.persist(sidecar, frozen, "source_calibration_audit");
                out.put("sidecarPersisted", persisted);
            }

            Log.d(TAG, "SOURCECAL1A cameraID=" + out.optString("cameraID", "?")
                    + " physicalID=" + out.optInt("physicalID", -1)
                    + " focalLengthMm=" + String.format(Locale.US, "%.3f", out.optDouble("focalLengthMm", Double.NaN))
                    + " nativeComplete=" + nativeComplete
                    + " activeDiff=" + out.optBoolean("activeMetadataDiffersFromNative", false));
        } catch (Throwable t) {
            try {
                out.put("error", t.toString());
                out.put("auditElapsedMs", (System.nanoTime() - startedNs) / 1_000_000L);
            } catch (Exception ignored) {}
            Log.e(TAG, "SOURCECAL1A audit failed", t);
        }
        return out;
    }

    private static int number(Object value, int fallback) {
        return value instanceof Number ? ((Number) value).intValue() : fallback;
    }

    private static float[] transform(ColorSpaceTransform t) {
        if (t == null) return null;
        float[] out = new float[9];
        int k = 0;
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                Rational v = t.getElement(r, c);
                out[k++] = v != null ? v.floatValue() : Float.NaN;
            }
        }
        return out;
    }

    private static float[] rationalVector(Rational[] in) {
        if (in == null) return null;
        float[] out = new float[in.length];
        for (int i = 0; i < in.length; i++) out[i] = in[i] != null ? in[i].floatValue() : Float.NaN;
        return out;
    }

    private static boolean valid3x3(float[] a) {
        if (a == null || a.length != 9) return false;
        for (float v : a) if (!Float.isFinite(v)) return false;
        return true;
    }

    private static boolean differs(float[] a, float[] b) {
        if (a == null || b == null || a.length != b.length) return true;
        for (int i = 0; i < a.length; i++) {
            if (!Float.isFinite(a[i]) || !Float.isFinite(b[i]) || Math.abs(a[i] - b[i]) > 1.0e-6f) return true;
        }
        return false;
    }

    private static JSONArray array(float[] a) {
        if (a == null) return null;
        JSONArray out = new JSONArray();
        for (float v : a) out.put(Float.isFinite(v) ? v : JSONObject.NULL);
        return out;
    }

    private static JSONArray matrix(float[] a) {
        if (a == null || a.length != 9) return null;
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) {
                float v = a[r * 3 + c];
                row.put(Float.isFinite(v) ? v : JSONObject.NULL);
            }
            rows.put(row);
        }
        return rows;
    }

    private static Path sidecarPath(Path dngPath) {
        if (dngPath == null) return null;
        String name = dngPath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        String stem = dot > 0 ? name.substring(0, dot) : name;
        return dngPath.resolveSibling(stem + "_M9_SOURCECAL1A.json");
    }
}
'''
write(source_rel, source_java)

anchor = '''            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(
                    dngPath, frame.width, frame.height, params, characteristics, captureResult, captureRequest);
'''
insert = anchor + '''            // M9SOURCECAL1A: native Camera2/DNG source characterization only; never feeds renderCore.
            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(
                    dngPath, params, characteristics, captureResult);
'''
if 'M9SourceCalibrationAudit1A.captureAndWrite(' not in renderer:
    if renderer.count(anchor) != 1:
        raise SystemExit('SOURCECAL1A RAWSHADING call anchor changed')
    renderer = renderer.replace(anchor, insert, 1)

diag_anchor = '''            diag.put("rawShadingAudit1A", rawShadingAudit1A);
            diag.put("rawShadingGainMapApplied", false);
'''
diag_insert = '''            diag.put("rawShadingAudit1A", rawShadingAudit1A);
            diag.put("sourceCalibrationAudit1A", sourceCalibrationAudit1A);
            diag.put("sourceCalibrationNativeTransformApplied", false);
            diag.put("rawShadingGainMapApplied", false);
'''
if 'diag.put("sourceCalibrationAudit1A"' not in renderer:
    if renderer.count(diag_anchor) != 1:
        raise SystemExit('SOURCECAL1A diagnostics anchor changed')
    renderer = renderer.replace(diag_anchor, diag_insert, 1)

write(renderer_rel, renderer)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit('SOURCECAL1A changed frozen photographic component: ' + rel)

print('M9SOURCECAL1A NATIVECAMERA2AUDIT1A applied')
print(' - direct native Camera2 dual-illuminant matrices captured per physical camera')
print(' - native-only sensor->XYZ D50 calculated with Photon DNG math, independent of sensor-specific override')
print(' - active Photon transform/HueSatMap state logged only for comparison')
print(' - *_M9_SOURCECAL1A.json diagnostic sidecar added')
print(' - native transform is NOT applied to rendering; M9 target core remains frozen')
