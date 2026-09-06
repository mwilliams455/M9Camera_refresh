#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nativeprospective1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('NATIVEPROSPECTIVE1A: not a PhotonCamera root')

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeProspective1A.java'

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('NATIVEPROSPECTIVE1A missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Calibration.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

renderer = read(renderer_rel)
for marker in [
    'CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(',
    'M9SourceCalibrationAudit1A.captureAndWrite(',
    'out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);',
    'ImageSaver.Util.saveBitmapAsJPGPayloadM9(jpgPath, bitmap, JPEG_QUALITY, exif);',
]:
    if marker not in renderer:
        raise SystemExit('NATIVEPROSPECTIVE1A requires prior marker: ' + marker)

if (root / helper_rel).exists():
    raise SystemExit('NATIVEPROSPECTIVE1A helper already exists; refuse ambiguous reapply')

helper_java = r'''package com.particlesdevs.photoncamera.m9.render;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.hardware.camera2.params.LensShadingMap;
import android.util.Rational;
import android.util.Size;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;
import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.processing.render.Converter;
import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.util.FileManager;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.imgproc.Imgproc;

import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.ShortBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** NATIVEPROSPECTIVE1A: additive one-frame Bayer RAW source-colour A/B renderer. */
public final class M9NativeProspective1A {
    private static final String TAG = "M9NativeProspective1A";
    public static final String SCHEMA =
            "m9cam.nativeprospective.v1a.singleframe.nativecamera2_lensshading_m9target";
    private static final int BLOCK_ROWS = 384;
    private static final int WORKERS =
            Math.max(2, Math.min(8, Runtime.getRuntime().availableProcessors()));
    private static final int JPEG_QUALITY = 95;

    private static final double TG_START_K = 4500.0;
    private static final double TG_FULL_K = 3200.0;
    private static final double TG_NEG_CB_COMPRESSION = 0.25;
    private static final double TG_NEG_CR_COMPRESSION = 0.16;

    private static final double[] M9_CM_A = {
            .8560, -.2034, -.0066, -.4240, 1.3600, .2920, -.0740, .2470, .8980
    };
    private static final double[] M9_CM_D65 = {
            .6260, -.1019, -.0470, -.3730, 1.1450, .1930, -.1409, .2950, .6210
    };
    private static final double[] D50_XY = {.34567, .35850};
    private static final double[] D65_XY = {.31271, .32902};
    private static final double[] BRADFORD = {
            .8951, .2664, -.1614, -.7502, 1.7135, .0367, .0389, -.0685, 1.0296
    };
    private static final double[] BRADFORD_INV = inverse3(BRADFORD);
    private static final double[] XYZ2SRGB = {
            3.2404542, -1.5371385, -.4985314,
            -.9692660, 1.8760108, .0415560,
            .0556434, -.2040259, 1.0572252
    };
    private static final double[] PP_TO_XYZ_RAW = {
            .7977, .1352, .0313, .2880, .7119, .0001, 0.0, 0.0, .8249
    };
    private static final double[] PP_TO_XYZ = normalizedPpToXyz();
    private static final double[] XYZ_TO_PP = inverse3(PP_TO_XYZ);

    private M9NativeProspective1A() {}

    public static JSONObject renderAndSave(Path dngPath,
                                           ImageFrame frame,
                                           Parameters params,
                                           CameraCharacteristics suppliedCharacteristics,
                                           CaptureResult physicalCaptureResult,
                                           int cameraRotation,
                                           JSONObject frozenRendererDiagnostics) {
        long startedNs = System.nanoTime();
        JSONObject out = new JSONObject();
        Bitmap bitmap = null;
        Mat rawMat = null;
        Mat cam16 = null;
        long nativeContext = 0L;
        try {
            out.put("schema", SCHEMA);
            out.put("scope", "additive_sidecar_jpeg_only_primary_jpeg_and_dng_frozen");
            out.put("sourceFrameCount", 1);
            out.put("captureMode", "single_frame_raw");
            out.put("hdrEnabled", false);
            out.put("multiFrameFusion", false);
            out.put("androidHdrGainmapUsed", false);
            out.put("camera2LensShadingMapApplied", false);
            out.put("lensShadingApplicationCount", 0);
            out.put("nativeSourceTransformApplied", false);
            out.put("cobaltColorMatrixApplied", false);
            out.put("cobaltForwardMatrixApplied", false);
            out.put("cobaltHsmApplied", false);
            out.put("leicaM9Curve02Applied", false);
            out.put("chromaExposureApplied", false);
            out.put("tc20DecisionSource", "frozen_primary_same_frame");
            out.put("tc20Recomputed", false);
            out.put("frozenPrimaryJpegMutated", false);
            out.put("prospectiveSidecarOnly", true);

            if (dngPath == null || frame == null || frame.buffer == null || params == null) {
                throw new IllegalArgumentException("missing DNG path, single RAW frame or Parameters");
            }
            if (params.cfaPattern != 0) {
                throw new IllegalStateException(
                        "NATIVEPROSPECTIVE1A follows frozen RGGB CFA=0 path; got " + params.cfaPattern);
            }

            String requestedPhysical =
                    M9PhysicalCaptureResult1A.requestedPhysicalCameraId(params.cameraID);
            boolean physicalRequested =
                    M9PhysicalCaptureResult1A.requestsUnderlyingPhysicalCamera(params.cameraID);
            CameraCharacteristics nativeCharacteristics = resolvePhysicalCharacteristics(
                    suppliedCharacteristics, requestedPhysical, physicalRequested, out);
            if (physicalCaptureResult == null) {
                throw new IllegalStateException("physical/top-level CaptureResult unavailable");
            }

            String resultCameraId = M9PhysicalCaptureResult1A.resultCameraId(physicalCaptureResult);
            out.put("requestedPhysicalCameraId",
                    requestedPhysical != null ? requestedPhysical : JSONObject.NULL);
            out.put("captureResultCameraId",
                    resultCameraId != null ? resultCameraId : JSONObject.NULL);
            out.put("physicalCaptureResultRequested", physicalRequested);
            out.put("captureResultMatchesRequestedPhysicalCamera",
                    M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(
                            physicalCaptureResult, params.cameraID));

            NativeModel model = buildNativeModel(nativeCharacteristics, physicalCaptureResult, out);
            M9R35Calibration cal = M9R35Calibration.get();
            if (cal.curve02 == null || cal.curve02.length != 2048) {
                throw new IllegalStateException("Leica M9 firmware curve02 missing/invalid");
            }

            float[] encodedBlack = new float[4];
            for (int i = 0; i < 4; i++) {
                encodedBlack[i] = ((short) params.blackLevel[i]) & 0xffff;
            }
            LensShadingMap lensMap =
                    physicalCaptureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP);
            short[] norm16 = normalizeBayerSingleFrame(
                    frame.buffer, frame.width, frame.height, encodedBlack, params.whiteLevel,
                    lensMap, nativeCharacteristics, out);

            rawMat = new Mat(frame.height, frame.width, CvType.CV_16UC1);
            cam16 = new Mat();
            rawMat.put(0, 0, norm16);
            norm16 = null;
            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
            rawMat.release();
            rawMat = null;

            if (!M9NativeColorCore.ensureLoaded()) {
                throw new IllegalStateException(
                        "M9 scalar JNI library unavailable: " + M9NativeColorCore.loadError());
            }
            nativeContext = M9NativeColorCore.createContext(
                    new double[]{1.0, 1.0, 1.0},
                    model.camToPp,
                    identityHsm2x2(),
                    model.ppToM9,
                    bradford(D50_XY, D65_XY),
                    PP_TO_XYZ,
                    XYZ2SRGB,
                    cal.curve02,
                    2, 2);
            if (nativeContext == 0L) {
                throw new IllegalStateException("native prospective context creation failed");
            }

            JSONObject edge = frozenRendererDiagnostics != null
                    ? frozenRendererDiagnostics.optJSONObject("edgePlacementBestFit2A") : null;
            double tc20BaselineGain = frozenRendererDiagnostics != null
                    ? frozenRendererDiagnostics.optDouble("gain", 1.0) : 1.0;
            String treatment = edge != null ? edge.optString("treatment", "FROZEN") : "FROZEN";
            double renderGainEv = "DARK_EXACT_RERENDER_GAIN_OFFSET".equals(treatment)
                    ? edge.optDouble("appliedEv", 0.0) : 0.0;
            double fixedRenderGain = tc20BaselineGain * Math.pow(2.0, renderGainEv);
            out.put("frozenTc20BaselineGain", tc20BaselineGain);
            out.put("frozenEdgePlacementTreatment", treatment);
            out.put("frozenEdgePlacementRenderGainEv", renderGainEv);
            out.put("prospectiveEffectiveRenderGain", fixedRenderGain);

            bitmap = renderFixedGain(
                    cam16, frame.width, frame.height, cameraRotation,
                    nativeContext, fixedRenderGain, model.cct, out);
            cam16.release();
            cam16 = null;

            if ("BRIGHT_RGB_PIVOT".equals(treatment)
                    && edge != null && edge.optBoolean("applied", false)) {
                double strength = edge.optDouble(
                        "strengthEv", M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                Bitmap pivoted =
                        M9EdgePlacementBestFit2AController.applyBrightPivot(bitmap, strength);
                if (pivoted == null) {
                    throw new IllegalStateException("prospective bright-pivot copy failed");
                }
                if (bitmap != pivoted && !bitmap.isRecycled()) bitmap.recycle();
                bitmap = pivoted;
                out.put("frozenBrightPivotReapplied", true);
                out.put("frozenBrightPivotStrengthEv", strength);
            } else {
                out.put("frozenBrightPivotReapplied", false);
            }

            String dngName = dngPath.getFileName().toString();
            int dot = dngName.lastIndexOf('.');
            String stem = dot > 0 ? dngName.substring(0, dot) : dngName;
            Path jpgPath = Paths.get(
                    FileManager.sDCIM_CAMERA.getAbsolutePath(),
                    stem + "_M9_NATIVEPROSPECTIVE.jpg");
            long jpegStartedNs = System.nanoTime();
            try (OutputStream os = Files.newOutputStream(jpgPath)) {
                if (!bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, os)) {
                    throw new IllegalStateException("prospective JPEG compress returned false");
                }
                os.flush();
            }
            out.put("jpegEncodeWriteElapsedMs",
                    (System.nanoTime() - jpegStartedNs) / 1_000_000.0);
            out.put("jpegQuality", JPEG_QUALITY);
            out.put("jpegPath", jpgPath.toString());
            out.put("galleryPublication", false);
            out.put("nativeSourceTransformApplied", true);
            out.put("leicaM9Curve02Applied", true);
            out.put("status", "success");
            out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
            persistDiagnostics(dngPath, out);
            Log.d(TAG, "single-frame native prospective saved: " + jpgPath);
            return out;
        } catch (Throwable t) {
            try {
                out.put("status", "failed_nonfatal_primary_preserved");
                out.put("error", t.toString());
                out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
                persistDiagnostics(dngPath, out);
            } catch (Throwable ignored) {}
            Log.e(TAG, "NATIVEPROSPECTIVE1A failed; frozen primary preserved", t);
            return out;
        } finally {
            if (nativeContext != 0L) {
                try { M9NativeColorCore.destroyContext(nativeContext); } catch (Throwable ignored) {}
            }
            if (rawMat != null) {
                try { rawMat.release(); } catch (Throwable ignored) {}
            }
            if (cam16 != null) {
                try { cam16.release(); } catch (Throwable ignored) {}
            }
            if (bitmap != null && !bitmap.isRecycled()) {
                try { bitmap.recycle(); } catch (Throwable ignored) {}
            }
        }
    }

    private static CameraCharacteristics resolvePhysicalCharacteristics(
            CameraCharacteristics supplied,
            String requestedPhysical,
            boolean physicalRequested,
            JSONObject out) throws Exception {
        if (!physicalRequested || requestedPhysical == null) {
            out.put("cameraCharacteristicsResolution", "supplied_camera_characteristics");
            return supplied;
        }
        try {
            Context context = PhotonCamera.getAppContext();
            if (context != null) {
                CameraManager manager =
                        (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);
                if (manager != null) {
                    CameraCharacteristics physical =
                            manager.getCameraCharacteristics(requestedPhysical);
                    if (physical != null) {
                        out.put("cameraCharacteristicsResolution",
                                "CameraManager_requested_physical_camera_id");
                        return physical;
                    }
                }
            }
        } catch (Throwable t) {
            out.put("physicalCharacteristicsLookupError", t.toString());
        }
        out.put("cameraCharacteristicsResolution",
                "supplied_characteristics_fallback_after_physical_lookup");
        return supplied;
    }

    private static final class NativeModel {
        final double[] camToPp;
        final double[] ppToM9;
        final double cct;
        NativeModel(double[] camToPp, double[] ppToM9, double cct) {
            this.camToPp = camToPp;
            this.ppToM9 = ppToM9;
            this.cct = cct;
        }
    }

    private static NativeModel buildNativeModel(CameraCharacteristics characteristics,
                                                CaptureResult captureResult,
                                                JSONObject out) throws Exception {
        if (characteristics == null) {
            throw new IllegalStateException("CameraCharacteristics unavailable");
        }
        Integer ref1Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1);
        Integer ref2Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2);
        int ref1 = ref1Obj != null ? ref1Obj : -1;
        int ref2 = ref2Obj != null ? ref2Obj : ref1;

        float[] cal1 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1));
        float[] cal2 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2));
        float[] cm1 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_COLOR_TRANSFORM1));
        float[] cm2 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_COLOR_TRANSFORM2));
        float[] fm1 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_FORWARD_MATRIX1));
        float[] fm2 = transform(characteristics.get(
                CameraCharacteristics.SENSOR_FORWARD_MATRIX2));
        float[] neutral = rationalVector(
                captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT));

        if (ref1 < 0 || ref2 < 0 || !valid3x3(cal1) || !valid3x3(cal2)
                || !valid3x3(cm1) || !valid3x3(cm2)
                || !valid3x3(fm1) || !valid3x3(fm2)
                || neutral == null || neutral.length < 3) {
            throw new IllegalStateException(
                    "native dual-illuminant Camera2/DNG metadata incomplete");
        }

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
        float[] sensorToXyzD50 = new float[9];
        Converter.calculateCameraToXYZD50Transform(
                nfm1, nfm2, cal1, cal2, neutral, factor, sensorToXyzD50);

        double[] xyzToCam1 = matMul3(toDouble(cal1), toDouble(ncm1));
        double[] xyzToCam2 = matMul3(toDouble(cal2), toDouble(ncm2));
        double[] xyzToCam = lerp9(xyzToCam1, xyzToCam2, factor);
        double[] xyzNeutral = matVec3(inverse3(xyzToCam), toDouble3(neutral));
        double sum = xyzNeutral[0] + xyzNeutral[1] + xyzNeutral[2];
        if (!Double.isFinite(sum) || Math.abs(sum) < 1e-12) {
            throw new IllegalStateException("native scene-white solve singular");
        }
        double[] sceneXy = {xyzNeutral[0] / sum, xyzNeutral[1] / sum};
        double cct = cctFromXy(sceneXy);
        double wA = weightA(cct);
        double[] camToPp = matMul3(XYZ_TO_PP, toDouble(sensorToXyzD50));

        double[] whiteXyz = xyToXyz(sceneXy);
        double[] m9cm = new double[9];
        for (int i = 0; i < 9; i++) {
            m9cm[i] = wA * M9_CM_A[i] + (1.0 - wA) * M9_CM_D65[i];
        }
        double[] mwhite = matVec3(m9cm, whiteXyz);
        for (int i = 0; i < 3; i++) mwhite[i] = Math.max(mwhite[i], 1e-8);
        double[] ppToM9Raw =
                matMul3(m9cm, matMul3(bradford(D50_XY, sceneXy), PP_TO_XYZ));
        double[] ppToM9 = ppToM9Raw.clone();
        for (int r = 0; r < 3; r++) {
            int base = r * 3;
            ppToM9[base] /= mwhite[r];
            ppToM9[base + 1] /= mwhite[r];
            ppToM9[base + 2] /= mwhite[r];
        }

        out.put("nativeReferenceIlluminant1", ref1);
        out.put("nativeReferenceIlluminant2", ref2);
        out.put("nativeInterpolationFactor", factor);
        out.put("nativeSensorNeutralColorPoint", jsonArray(neutral));
        out.put("nativeSensorToXYZD50", jsonMatrix(sensorToXyzD50));
        out.put("nativeSceneWhiteX", sceneXy[0]);
        out.put("nativeSceneWhiteY", sceneXy[1]);
        out.put("nativeSceneCctKelvin", cct);
        out.put("nativeSceneAWeight", wA);
        out.put("sourceSceneSpace", "XYZ_D50");
        out.put("nativeTransformIncludesLiveNeutralWhiteBalance", true);
        out.put("additionalWhiteBalanceDiagonalApplied", false);
        out.put("sourceHueSatMap", "identity_2x2");
        out.put("targetBridge", "Leica_M9_CM_A_D65_plus_scene_white_Bradford");
        return new NativeModel(camToPp, ppToM9, cct);
    }

    private static short[] normalizeBayerSingleFrame(ByteBuffer rawBuffer,
                                                     int width,
                                                     int height,
                                                     float[] black,
                                                     int whiteLevel,
                                                     LensShadingMap lensMap,
                                                     CameraCharacteristics characteristics,
                                                     JSONObject out) throws Exception {
        int pixels = Math.multiplyExact(width, height);
        ByteBuffer dup = rawBuffer.duplicate().order(ByteOrder.LITTLE_ENDIAN);
        dup.position(0);
        if (dup.remaining() < Math.multiplyExact(pixels, 2)) {
            throw new IllegalArgumentException("single RAW buffer too small");
        }
        ShortBuffer raw = dup.asShortBuffer();
        short[] normalized = new short[pixels];

        int wl = Math.max(2, whiteLevel);
        boolean useMap = lensMap != null
                && lensMap.getColumnCount() >= 2
                && lensMap.getRowCount() >= 2;
        float[] map = null;
        int mapCols = 0;
        int mapRows = 0;
        if (useMap) {
            mapCols = lensMap.getColumnCount();
            mapRows = lensMap.getRowCount();
            map = new float[lensMap.getGainFactorCount()];
            lensMap.copyGainFactors(map, 0);
            out.put("camera2LensShadingMapApplied", true);
            out.put("lensShadingApplicationCount", 1);
            out.put("lensShadingMapColumns", mapCols);
            out.put("lensShadingMapRows", mapRows);
        } else {
            out.put("lensShadingUnavailableOrDegenerate", true);
        }

        Boolean alreadyApplied = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED)
                : null;
        out.put("sensorInfoLensShadingApplied",
                alreadyApplied != null ? alreadyApplied : JSONObject.NULL);
        out.put("lensShadingSemantics",
                "Camera2_remaining_or_complete_map_applied_once_in_Bayer_space");

        Rect active = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE) : null;
        Rect pre = characteristics != null
                ? characteristics.get(
                        CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE) : null;
        Size pixel = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE) : null;
        SpatialMapping spatial = new SpatialMapping(width, height, active, pre, pixel);
        out.put("lensShadingSpatialMapping", spatial.mode);
        if (active != null) out.put("activeArray", rectJson(active));
        if (pre != null) out.put("preCorrectionActiveArray", rectJson(pre));

        double[] minGain = {
                Double.POSITIVE_INFINITY, Double.POSITIVE_INFINITY,
                Double.POSITIVE_INFINITY, Double.POSITIVE_INFINITY
        };
        double[] maxGain = {
                Double.NEGATIVE_INFINITY, Double.NEGATIVE_INFINITY,
                Double.NEGATIVE_INFINITY, Double.NEGATIVE_INFINITY
        };
        double[] sumGain = new double[4];
        long[] gainCount = new long[4];

        for (int y = 0, index = 0; y < height; y++) {
            SpatialRow row = spatial.row(y);
            for (int x = 0; x < width; x++, index++) {
                int plane = ((y & 1) << 1) | (x & 1);
                int rawValue = raw.get(index) & 0xffff;
                double gain = 1.0;
                if (useMap) {
                    SpatialPoint pt = row.point(x);
                    if (pt.insideActive) {
                        gain = bilinearGain(map, mapCols, mapRows, plane, pt.u, pt.v);
                    }
                }
                if (!Double.isFinite(gain) || gain < 1.0) gain = 1.0;
                minGain[plane] = Math.min(minGain[plane], gain);
                maxGain[plane] = Math.max(maxGain[plane], gain);
                sumGain[plane] += gain;
                gainCount[plane]++;

                double bl = black != null && black.length >= 4 ? black[plane] : 64.0;
                double denominator = Math.max(1.0, wl - bl);
                double corrected = Math.max(0.0, rawValue - bl) * gain;
                double unit = Math.max(0.0, Math.min(1.0, corrected / denominator));
                normalized[index] = (short) Math.round(unit * 65535.0);
            }
        }

        JSONArray stats = new JSONArray();
        for (int c = 0; c < 4; c++) {
            JSONObject s = new JSONObject();
            s.put("channel", c);
            s.put("min", Double.isFinite(minGain[c]) ? minGain[c] : 1.0);
            s.put("max", Double.isFinite(maxGain[c]) ? maxGain[c] : 1.0);
            s.put("mean", gainCount[c] > 0 ? sumGain[c] / gainCount[c] : 1.0);
            stats.put(s);
        }
        out.put("appliedLensShadingGainStats", stats);
        out.put("bayerCorrectionOrder",
                "max(raw-encoded_black,0)*Camera2_LensShadingMap_then_whiteLevel_normalize");
        return normalized;
    }

    private static final class SpatialMapping {
        final int width, height;
        final Rect active, pre;
        final Size pixel;
        final String mode;
        SpatialMapping(int width, int height, Rect active, Rect pre, Size pixel) {
            this.width = width;
            this.height = height;
            this.active = active;
            this.pre = pre;
            this.pixel = pixel;
            if (active != null && width == active.width() && height == active.height()) {
                mode = "frame_dimensions_equal_active_array";
            } else if (active != null && pixel != null
                    && width == pixel.getWidth() && height == pixel.getHeight()) {
                mode = "frame_dimensions_equal_pixel_array_active_rect_offset";
            } else if (active != null && pre != null
                    && width == pre.width() && height == pre.height()) {
                mode = "frame_dimensions_equal_pre_correction_array_active_rect_offset";
            } else {
                mode = "proportional_frame_to_active_array_fallback";
            }
        }
        SpatialRow row(int y) { return new SpatialRow(this, y); }
    }

    private static final class SpatialRow {
        final SpatialMapping m;
        final double v;
        final boolean rowInside;
        SpatialRow(SpatialMapping m, int y) {
            this.m = m;
            if ("frame_dimensions_equal_pixel_array_active_rect_offset".equals(m.mode)
                    && m.active != null) {
                rowInside = y >= m.active.top && y < m.active.bottom;
                v = rowInside && m.active.height() > 1
                        ? (y - m.active.top) / (double) (m.active.height() - 1) : 0.0;
            } else if ("frame_dimensions_equal_pre_correction_array_active_rect_offset".equals(m.mode)
                    && m.active != null && m.pre != null) {
                int ay = m.pre.top + y;
                rowInside = ay >= m.active.top && ay < m.active.bottom;
                v = rowInside && m.active.height() > 1
                        ? (ay - m.active.top) / (double) (m.active.height() - 1) : 0.0;
            } else {
                rowInside = true;
                v = m.height > 1 ? y / (double) (m.height - 1) : 0.0;
            }
        }
        SpatialPoint point(int x) {
            boolean inside = rowInside;
            double u;
            if ("frame_dimensions_equal_pixel_array_active_rect_offset".equals(m.mode)
                    && m.active != null) {
                inside = inside && x >= m.active.left && x < m.active.right;
                u = inside && m.active.width() > 1
                        ? (x - m.active.left) / (double) (m.active.width() - 1) : 0.0;
            } else if ("frame_dimensions_equal_pre_correction_array_active_rect_offset".equals(m.mode)
                    && m.active != null && m.pre != null) {
                int ax = m.pre.left + x;
                inside = inside && ax >= m.active.left && ax < m.active.right;
                u = inside && m.active.width() > 1
                        ? (ax - m.active.left) / (double) (m.active.width() - 1) : 0.0;
            } else {
                u = m.width > 1 ? x / (double) (m.width - 1) : 0.0;
            }
            return new SpatialPoint(inside, clamp01(u), clamp01(v));
        }
    }

    private static final class SpatialPoint {
        final boolean insideActive;
        final double u, v;
        SpatialPoint(boolean insideActive, double u, double v) {
            this.insideActive = insideActive;
            this.u = u;
            this.v = v;
        }
    }

    private static double bilinearGain(
            float[] map, int cols, int rows, int channel, double u, double v) {
        double gx = clamp01(u) * (cols - 1);
        double gy = clamp01(v) * (rows - 1);
        int x0 = Math.min(cols - 1, Math.max(0, (int) Math.floor(gx)));
        int y0 = Math.min(rows - 1, Math.max(0, (int) Math.floor(gy)));
        int x1 = Math.min(cols - 1, x0 + 1);
        int y1 = Math.min(rows - 1, y0 + 1);
        double fx = gx - x0;
        double fy = gy - y0;
        double g00 = map[((y0 * cols + x0) * 4) + channel];
        double g10 = map[((y0 * cols + x1) * 4) + channel];
        double g01 = map[((y1 * cols + x0) * 4) + channel];
        double g11 = map[((y1 * cols + x1) * 4) + channel];
        double top = g00 + fx * (g10 - g00);
        double bottom = g01 + fx * (g11 - g01);
        return top + fy * (bottom - top);
    }

    private static Bitmap renderFixedGain(
            Mat cam16, int width, int height, int cameraRotation,
            long nativeContext, double gain, double cct, JSONObject out) throws Exception {
        int rotation = ((cameraRotation % 360) + 360) % 360;
        int orientedWidth = (rotation == 90 || rotation == 270) ? height : width;
        int orientedHeight = (rotation == 90 || rotation == 270) ? width : height;
        Bitmap oriented = Bitmap.createBitmap(
                orientedWidth, orientedHeight, Bitmap.Config.ARGB_8888);

        int maxBlockPixels = Math.multiplyExact(width, BLOCK_ROWS);
        short[] camBlock = new short[Math.multiplyExact(maxBlockPixels, 3)];
        int[] argbBlock = new int[maxBlockPixels];
        long[] stats = new long[12];
        double tgWeight = tungstenGuardWeight(cct);
        double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
        double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;

        long renderStartedNs = System.nanoTime();
        for (int y0 = 0; y0 < height; y0 += BLOCK_ROWS) {
            int rows = Math.min(BLOCK_ROWS, height - y0);
            int blockPixels = Math.multiplyExact(rows, width);
            cam16.get(y0, 0, camBlock);
            M9NativeColorCore.renderBlockParallel(
                    nativeContext, camBlock, blockPixels, width, argbBlock,
                    gain, tgCbGain, tgCrGain, rotation, WORKERS, stats);
            if (rotation == 90) {
                int destX = height - (y0 + rows);
                oriented.setPixels(argbBlock, 0, rows, destX, 0, rows, width);
            } else if (rotation == 270) {
                oriented.setPixels(argbBlock, 0, rows, y0, 0, rows, width);
            } else if (rotation == 180) {
                int destY = height - (y0 + rows);
                oriented.setPixels(argbBlock, 0, width, 0, destY, width, rows);
            } else {
                oriented.setPixels(argbBlock, 0, width, 0, y0, width, rows);
            }
        }
        out.put("nativeProspectiveRenderElapsedMs",
                (System.nanoTime() - renderStartedNs) / 1_000_000.0);
        out.put("nativeColorMode", "existing_M9_scalar_cpp_JNI_block_renderer");
        out.put("nativeColorWorkers", WORKERS);
        out.put("tungstenGuard", "TG1");
        out.put("tungstenGuardWeight", tgWeight);
        out.put("sat3AndBt601Path", "existing_frozen_native_scalar_kernel");
        return oriented;
    }

    private static double[] identityHsm2x2() {
        double[] hsm = new double[12];
        for (int i = 0; i < 4; i++) {
            int base = i * 3;
            hsm[base] = 0.0;
            hsm[base + 1] = 1.0;
            hsm[base + 2] = 1.0;
        }
        return hsm;
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
        for (int i = 0; i < in.length; i++) {
            out[i] = in[i] != null ? in[i].floatValue() : Float.NaN;
        }
        return out;
    }

    private static boolean valid3x3(float[] a) {
        if (a == null || a.length != 9) return false;
        for (float v : a) if (!Float.isFinite(v)) return false;
        return true;
    }

    private static JSONArray jsonArray(float[] a) {
        JSONArray out = new JSONArray();
        if (a != null) for (float v : a) out.put(Float.isFinite(v) ? v : JSONObject.NULL);
        return out;
    }

    private static JSONArray jsonMatrix(float[] a) {
        JSONArray rows = new JSONArray();
        if (a == null || a.length != 9) return rows;
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

    private static JSONObject rectJson(Rect r) throws Exception {
        JSONObject out = new JSONObject();
        out.put("left", r.left);
        out.put("top", r.top);
        out.put("right", r.right);
        out.put("bottom", r.bottom);
        out.put("width", r.width());
        out.put("height", r.height());
        return out;
    }

    private static void persistDiagnostics(Path dngPath, JSONObject out) {
        if (dngPath == null || out == null) return;
        try {
            String name = dngPath.getFileName().toString();
            int dot = name.lastIndexOf('.');
            String stem = dot > 0 ? name.substring(0, dot) : name;
            Path sidecar = dngPath.resolveSibling(stem + "_M9_NATIVEPROSPECTIVE.json");
            out.put("sidecarPath", sidecar.toString());
            out.put("sidecarTransport", M9DiagnosticSidecarIO.SCHEMA);
            byte[] bytes = out.toString(2).getBytes(StandardCharsets.UTF_8);
            out.put("sidecarPersisted",
                    M9DiagnosticSidecarIO.persist(
                            sidecar, bytes, "native_prospective_singleframe"));
        } catch (Throwable ignored) {}
    }

    private static double[] normalizedPpToXyz() {
        double[] pcs = xyToXyz(D50_XY);
        double[] row = matVec3(PP_TO_XYZ_RAW, new double[]{1, 1, 1});
        double[] m = PP_TO_XYZ_RAW.clone();
        for (int r = 0; r < 3; r++) {
            double scale = pcs[r] / row[r];
            for (int c = 0; c < 3; c++) m[r * 3 + c] *= scale;
        }
        return m;
    }

    private static double cctFromXy(double[] xy) {
        double n = (xy[0] - .3320) / (xy[1] - .1858);
        return clamp(
                -449 * n * n * n + 3525 * n * n - 6823.3 * n + 5520.33,
                2000, 12000);
    }

    private static double weightA(double t) {
        double m = 1e6 / t;
        return clamp(
                (m - 1e6 / 6500.0) / (1e6 / 2850.0 - 1e6 / 6500.0),
                0.0, 1.0);
    }

    private static double[] xyToXyz(double[] xy) {
        return new double[]{xy[0] / xy[1], 1.0, (1.0 - xy[0] - xy[1]) / xy[1]};
    }

    private static double[] bradford(double[] srcXy, double[] dstXy) {
        double[] s = matVec3(BRADFORD, xyToXyz(srcXy));
        double[] d = matVec3(BRADFORD, xyToXyz(dstXy));
        double[] diag = {d[0] / s[0], 0, 0, 0, d[1] / s[1], 0, 0, 0, d[2] / s[2]};
        return matMul3(matMul3(BRADFORD_INV, diag), BRADFORD);
    }

    private static double[] lerp9(double[] a, double[] b, double t) {
        double[] out = new double[9];
        for (int i = 0; i < 9; i++) out[i] = a[i] * (1.0 - t) + b[i] * t;
        return out;
    }

    private static double[] matMul3(double[] a, double[] b) {
        double[] o = new double[9];
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                o[r * 3 + c] =
                        a[r * 3] * b[c]
                                + a[r * 3 + 1] * b[3 + c]
                                + a[r * 3 + 2] * b[6 + c];
            }
        }
        return o;
    }

    private static double[] matVec3(double[] m, double[] v) {
        return new double[]{
                m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
                m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
                m[6] * v[0] + m[7] * v[1] + m[8] * v[2]
        };
    }

    private static double[] inverse3(double[] m) {
        double a = m[0], b = m[1], c = m[2], d = m[3], e = m[4], f = m[5],
                g = m[6], h = m[7], i = m[8];
        double A = e * i - f * h;
        double B = -(d * i - f * g);
        double C = d * h - e * g;
        double D = -(b * i - c * h);
        double E = a * i - c * g;
        double F = -(a * h - b * g);
        double G = b * f - c * e;
        double H = -(a * f - c * d);
        double I = a * e - b * d;
        double det = a * A + b * B + c * C;
        if (Math.abs(det) < 1e-15) throw new IllegalArgumentException("singular 3x3 matrix");
        return new double[]{
                A / det, D / det, G / det,
                B / det, E / det, H / det,
                C / det, F / det, I / det
        };
    }

    private static double[] toDouble(float[] a) {
        double[] out = new double[a.length];
        for (int i = 0; i < a.length; i++) out[i] = a[i];
        return out;
    }

    private static double[] toDouble3(float[] a) {
        return new double[]{a[0], a[1], a[2]};
    }

    private static double tungstenGuardWeight(double cct) {
        double x = clamp(
                (TG_START_K - cct) / (TG_START_K - TG_FULL_K), 0.0, 1.0);
        return x * x * (3.0 - 2.0 * x);
    }

    private static double clamp01(double v) {
        return clamp(v, 0.0, 1.0);
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}
'''
write(helper_rel, helper_java)

anchor = '''            bitmap = null;
            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");
            if (SAVE_PARITY_PNG && !pngSaved) throw new IllegalStateException("M9 parity PNG save failed");

            long elapsedMs = (System.nanoTime() - started) / 1_000_000L;
'''
insert = '''            bitmap = null;
            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");
            if (SAVE_PARITY_PNG && !pngSaved) throw new IllegalStateException("M9 parity PNG save failed");

            // NATIVEPROSPECTIVE1A / SINGLEFRAME: additive A/B sidecar only. The normal
            // JPEG payload above is already safely written. Reuse this exact one RAW frame,
            // the resolved physical CaptureResult and the frozen final TC20/edge decision.
            JSONObject nativeProspective1A = M9NativeProspective1A.renderAndSave(
                    dngPath, frame, params, characteristics, diagnosticCaptureResult1A,
                    cameraRotation, out.diagnostics);
            out.diagnostics.put("nativeProspective1A", nativeProspective1A);

            long elapsedMs = (System.nanoTime() - started) / 1_000_000L;
'''
if renderer.count(anchor) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1A insertion anchor missing/non-unique')
renderer = renderer.replace(anchor, insert, 1)
write(renderer_rel, renderer)

for marker in [
    'JSONObject nativeProspective1A = M9NativeProspective1A.renderAndSave(',
    'dngPath, frame, params, characteristics, diagnosticCaptureResult1A,',
    'out.diagnostics.put("nativeProspective1A", nativeProspective1A);',
]:
    if marker not in read(renderer_rel):
        raise SystemExit('NATIVEPROSPECTIVE1A renderer marker missing: ' + marker)

for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('NATIVEPROSPECTIVE1A changed frozen file: ' + rel)

print('M9 NATIVEPROSPECTIVE1A SINGLEFRAME applied')
print(' - primary JPEG encoded first; additive prospective JPEG cannot replace it')
print(' - one existing Bayer RAW ImageFrame reused; capture/queue/DNG paths frozen')
print(' - Camera2 physical metadata -> native sensor-to-XYZ D50; Cobalt CM/FM/HSM bypassed')
print(' - Camera2 LensShadingMap applied once in Bayer space when present')
print(' - frozen TC20/edge-placement decision reused; no prospective remetering')
print(' - Leica M9 target bridge, curve02, SAT3, BT.601 4:2:2 and TG1 retained')
