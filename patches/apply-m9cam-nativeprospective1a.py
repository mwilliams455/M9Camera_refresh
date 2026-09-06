#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nativeprospective1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('NATIVEPROSPECTIVE1A: not a PhotonCamera root')

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_rel = 'app/build.gradle'


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


def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method marker missing: ' + marker)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method opening brace missing')
    depth = 0
    i = brace
    in_string = False
    string_quote = ''
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == string_quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, text[start:i + 1]
        i += 1
    raise SystemExit('NATIVEPROSPECTIVE1A unterminated method')

renderer = read(renderer_rel)
gradle = read(gradle_rel)

for marker in [
    'M9RawShadingAudit1A.captureAndWrite(',
    'M9SourceCalibrationAudit1A.captureAndWrite(',
    'M9PhysicalCaptureResult1A.resolve(',
    'M9EdgePlacementBestFit2AController',
    'saveBitmapAsJPGPayloadM9(',
]:
    if marker not in renderer:
        raise SystemExit('NATIVEPROSPECTIVE1A requires promoted SOURCECAL/BESTFIT baseline marker: ' + marker)
if 'renderNativeProspectiveCore(' in renderer:
    raise SystemExit('NATIVEPROSPECTIVE1A already present; refuse ambiguous reapply')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

orig_start, orig_end, frozen_render_core = extract_method(
    renderer, '    private static RenderCore renderCore(')
frozen_render_core_sha = hashlib.sha256(frozen_render_core.encode('utf-8')).hexdigest()

imports = [
    ('import android.hardware.camera2.CaptureResult;\n',
     'import android.hardware.camera2.CaptureResult;\nimport android.hardware.camera2.params.ColorSpaceTransform;\nimport android.hardware.camera2.params.LensShadingMap;\nimport android.util.Rational;\n'),
    ('import com.particlesdevs.photoncamera.processing.render.Parameters;\n',
     'import com.particlesdevs.photoncamera.processing.render.Parameters;\nimport com.particlesdevs.photoncamera.processing.render.Converter;\n'),
]
for old, new in imports:
    if new not in renderer:
        if old not in renderer:
            raise SystemExit('NATIVEPROSPECTIVE1A import anchor missing: ' + old.strip())
        renderer = renderer.replace(old, new, 1)
if 'import org.json.JSONArray;' not in renderer:
    renderer = renderer.replace('import org.json.JSONObject;\n', 'import org.json.JSONArray;\nimport org.json.JSONObject;\n', 1)
if 'import java.nio.charset.StandardCharsets;' not in renderer:
    renderer = renderer.replace('import java.nio.file.Files;\n', 'import java.nio.file.Files;\nimport java.nio.charset.StandardCharsets;\n', 1)

prospective = frozen_render_core
prospective = prospective.replace(
    '    private static RenderCore renderCore(ByteBuffer rawBuffer,',
    '    private static RenderCore renderNativeProspectiveCore(ByteBuffer rawBuffer,', 1)
sig_tail = '''                                         int cameraRotation,
                                         double edgePlacementGainEv) throws Exception {'''
new_sig_tail = '''                                         int cameraRotation,
                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult) throws Exception {'''
if sig_tail not in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A expected BESTFIT2A renderCore signature not found')
prospective = prospective.replace(sig_tail, new_sig_tail, 1)

shade_anchor = '''        rawCounts = null;
        normalizeRawElapsedMs = (System.nanoTime() - normalizeRawStartedNs) / 1_000_000L;

        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);'''
shade_insert = '''        rawCounts = null;
        normalizeRawElapsedMs = (System.nanoTime() - normalizeRawStartedNs) / 1_000_000L;

        // NATIVEPROSPECTIVE1A: apply the selected physical camera's live Camera2
        // LensShadingMap exactly once in linear normalized Bayer space, before demosaic.
        // The frozen renderCore above remains byte-for-byte unchanged and still applies none.
        LensShadingMap nativeLiveGainMap = nativeCaptureResult != null
                ? nativeCaptureResult.get(CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP) : null;
        NativeProspectiveShadingStats nativeShading = applyNativeProspectiveGainMap(
                norm16, width, height, nativeLiveGainMap);

        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);'''
if shade_anchor not in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A normalized Bayer insertion anchor missing')
prospective = prospective.replace(shade_anchor, shade_insert, 1)

color_old = '''            long colorContextStartedNs = System.nanoTime();
            M9R35Calibration cal = M9R35Calibration.get();
            ColorContext ctx = buildColorContext(neutralF, cal);
            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
color_new = '''            long colorContextStartedNs = System.nanoTime();
            // The mixed calibration asset is loaded only to retain Leica firmware curve02.
            // Cobalt ColorMatrix/ForwardMatrix/HSM components are not read into this context.
            M9R35Calibration cal = M9R35Calibration.get();
            NativeProspectiveSource nativeSource = buildNativeProspectiveSource(
                    nativeCharacteristics, nativeCaptureResult);
            ColorContext ctx = nativeSource.ctx;
            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
if color_old not in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A Cobalt context anchor missing')
prospective = prospective.replace(color_old, color_new, 1)

diag_anchor = '''            d.put("orientationElapsedMs", orientationElapsedMs);
            return new RenderCore(oriented, d);'''
diag_insert = '''            d.put("orientationElapsedMs", orientationElapsedMs);
            d.put("schema", "m9cam.renderer.nativeprospective.v1a.sourceadapter1a");
            d.put("reference", "NATIVEPROSPECTIVE1A additive Cobalt-source-bypass branch; frozen primary renderCore preserved");
            d.put("pipeline", "physical live Bayer GainMap once -> EA demosaic -> native Camera2 dual-illuminant sensor->XYZ D50 -> ProPhoto identity-HSM -> M9 target bridge -> frozen TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> TG1");
            d.put("nativeProspective", true);
            d.put("sourceAdapter", "Camera2_native_dual_illuminant_no_Cobalt_source_matrices");
            d.put("cobaltColorMatrixApplied", false);
            d.put("cobaltForwardMatrixApplied", false);
            d.put("cobaltHueSatMapApplied", false);
            d.put("identityHsmApplied", true);
            d.put("mixedCalibrationAssetUsage", "curve02_target_component_only");
            d.put("gainMapAppliedToRender", true);
            d.put("gainMapApplicationCount", 1);
            d.put("gainMapApplicationStage", "normalized_linear_Bayer_pre_demosaic");
            d.put("gainMapWidth", nativeShading.mapWidth);
            d.put("gainMapHeight", nativeShading.mapHeight);
            d.put("gainMapFactorMin", nativeShading.minGain);
            d.put("gainMapFactorMax", nativeShading.maxGain);
            d.put("gainMapCorrectedPixelCount", nativeShading.correctedPixels);
            d.put("nativeReferenceIlluminant1", nativeSource.referenceIlluminant1);
            d.put("nativeReferenceIlluminant2", nativeSource.referenceIlluminant2);
            d.put("nativeInterpolationFactor", nativeSource.interpolationFactor);
            d.put("nativeSceneX", nativeSource.sceneX);
            d.put("nativeSceneY", nativeSource.sceneY);
            d.put("nativeSensorNeutralR", nativeSource.neutral[0]);
            d.put("nativeSensorNeutralG", nativeSource.neutral[1]);
            d.put("nativeSensorNeutralB", nativeSource.neutral[2]);
            d.put("nativeSensorToXYZD50", nativeProspectiveMatrix(nativeSource.sensorToXyzD50));
            d.put("nativeCameraToProPhotoD50", nativeProspectiveMatrix(nativeSource.cameraToProPhotoD50));
            d.put("hsmHueStrength", 0.0);
            d.put("hsmSaturationStrength", 0.0);
            d.put("hsmValueStrength", 0.0);
            d.put("fullColorRenderStages", "native Camera2 source adapter + identity HSM + retained M9 bridge/SAT3/curve02/BT601/TG1");
            return new RenderCore(oriented, d);'''
if diag_anchor not in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A diagnostics return anchor missing')
prospective = prospective.replace(diag_anchor, diag_insert, 1)

renderer = renderer[:orig_end] + '\n\n' + prospective + renderer[orig_end:]

helpers = r'''

    private static final class NativeProspectiveSource {
        final ColorContext ctx;
        final float[] sensorToXyzD50;
        final float[] cameraToProPhotoD50;
        final float[] neutral;
        final double interpolationFactor;
        final double sceneX;
        final double sceneY;
        final int referenceIlluminant1;
        final int referenceIlluminant2;

        NativeProspectiveSource(ColorContext ctx,
                                float[] sensorToXyzD50,
                                float[] cameraToProPhotoD50,
                                float[] neutral,
                                double interpolationFactor,
                                double sceneX,
                                double sceneY,
                                int referenceIlluminant1,
                                int referenceIlluminant2) {
            this.ctx = ctx;
            this.sensorToXyzD50 = sensorToXyzD50;
            this.cameraToProPhotoD50 = cameraToProPhotoD50;
            this.neutral = neutral;
            this.interpolationFactor = interpolationFactor;
            this.sceneX = sceneX;
            this.sceneY = sceneY;
            this.referenceIlluminant1 = referenceIlluminant1;
            this.referenceIlluminant2 = referenceIlluminant2;
        }
    }

    private static NativeProspectiveSource buildNativeProspectiveSource(
            CameraCharacteristics characteristics,
            CaptureResult captureResult) throws Exception {
        if (characteristics == null || captureResult == null) {
            throw new IllegalStateException("native prospective requires physical CameraCharacteristics + CaptureResult");
        }

        Integer ref1Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1);
        Integer ref2Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2);
        if (ref1Obj == null || ref2Obj == null) {
            throw new IllegalStateException("native prospective missing dual reference illuminants");
        }
        final int ref1 = ref1Obj;
        final int ref2 = ref2Obj;

        float[] cal1 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1));
        float[] cal2 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2));
        float[] cm1 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1));
        float[] cm2 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2));
        float[] fm1 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1));
        float[] fm2 = nativeProspectiveTransform(
                characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2));
        if (!nativeProspectiveValid3x3(cal1) || !nativeProspectiveValid3x3(cal2)
                || !nativeProspectiveValid3x3(cm1) || !nativeProspectiveValid3x3(cm2)
                || !nativeProspectiveValid3x3(fm1) || !nativeProspectiveValid3x3(fm2)) {
            throw new IllegalStateException("native prospective incomplete Camera2 dual-illuminant matrices");
        }

        Rational[] neutralR = captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
        if (neutralR == null || neutralR.length < 3) {
            throw new IllegalStateException("native prospective missing physical SENSOR_NEUTRAL_COLOR_POINT");
        }
        float[] neutral = new float[3];
        for (int i = 0; i < 3; i++) {
            neutral[i] = neutralR[i] != null ? neutralR[i].floatValue() : Float.NaN;
            if (!Float.isFinite(neutral[i]) || neutral[i] <= 0.0f) {
                throw new IllegalStateException("native prospective invalid physical neutral channel " + i);
            }
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

        float[] xyzToCamera1 = new float[9];
        float[] xyzToCamera2 = new float[9];
        Converter.multiply(cal1, ncm1, xyzToCamera1);
        Converter.multiply(cal2, ncm2, xyzToCamera2);
        float[] xyzToCamera = new float[9];
        Converter.lerp(xyzToCamera1, xyzToCamera2, factor, xyzToCamera);
        float[] cameraToXyzScene = new float[9];
        if (!Converter.invert(xyzToCamera, cameraToXyzScene)) {
            throw new IllegalStateException("native prospective cannot invert interpolated XYZ->camera matrix");
        }
        float[] whiteXyz = new float[3];
        Converter.map(cameraToXyzScene, neutral, whiteXyz);
        double sum = (double)whiteXyz[0] + whiteXyz[1] + whiteXyz[2];
        if (!Double.isFinite(sum) || Math.abs(sum) < 1.0e-12) {
            throw new IllegalStateException("native prospective invalid scene-white XYZ");
        }
        double[] xy = {whiteXyz[0] / sum, whiteXyz[1] / sum};

        double[] sensorToXyzD = nativeProspectiveDouble(sensorToXyzD50);
        double[] cameraToProPhoto = matMul3(XYZ_TO_PP, sensorToXyzD);
        ColorContext ctx = new ColorContext();
        ctx.cw = new double[]{1.0, 1.0, 1.0};
        ctx.camToPp = cameraToProPhoto;
        ctx.hsm = new double[]{
                0.0, 1.0, 1.0,
                0.0, 1.0, 1.0,
                0.0, 1.0, 1.0,
                0.0, 1.0, 1.0
        };
        ctx.hueDivisions = 2;
        ctx.satDivisions = 2;
        ctx.cct = cctFromXy(xy);
        ctx.wA = weightA(ctx.cct);
        ctx.adapt50ToScene = bradford(D50_XY, xy);
        ctx.adapt50To65 = bradford(D50_XY, D65_XY);
        ctx.m9cm = interp9(M9_CM_A, M9_CM_D65, ctx.wA);
        double[] sceneWhiteXyz = xyToXyz(xy);
        ctx.mwhite = matVec3(ctx.m9cm, sceneWhiteXyz);
        for (int k = 0; k < 3; k++) ctx.mwhite[k] = Math.max(ctx.mwhite[k], 1e-8);
        double[] ppToM9Unnormalized = matMul3(
                ctx.m9cm, matMul3(ctx.adapt50ToScene, PP_TO_XYZ));
        ctx.ppToM9 = new double[9];
        for (int row = 0; row < 3; row++) {
            double den = ctx.mwhite[row];
            int base = row * 3;
            ctx.ppToM9[base] = ppToM9Unnormalized[base] / den;
            ctx.ppToM9[base + 1] = ppToM9Unnormalized[base + 1] / den;
            ctx.ppToM9[base + 2] = ppToM9Unnormalized[base + 2] / den;
        }

        float[] cameraToProPhotoF = new float[9];
        for (int i = 0; i < 9; i++) cameraToProPhotoF[i] = (float)cameraToProPhoto[i];
        return new NativeProspectiveSource(
                ctx, sensorToXyzD50, cameraToProPhotoF, neutral, factor,
                xy[0], xy[1], ref1, ref2);
    }

    private static float[] nativeProspectiveTransform(ColorSpaceTransform transform) {
        if (transform == null) return null;
        float[] out = new float[9];
        Converter.convertColorspaceTransform(transform, out);
        return out;
    }

    private static boolean nativeProspectiveValid3x3(float[] a) {
        if (a == null || a.length != 9) return false;
        for (float v : a) if (!Float.isFinite(v)) return false;
        return true;
    }

    private static double[] nativeProspectiveDouble(float[] a) {
        double[] out = new double[a.length];
        for (int i = 0; i < a.length; i++) out[i] = a[i];
        return out;
    }

    private static JSONArray nativeProspectiveMatrix(float[] a) throws Exception {
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) row.put(a[r * 3 + c]);
            rows.put(row);
        }
        return rows;
    }

    private static final class NativeProspectiveShadingStats {
        final int mapWidth;
        final int mapHeight;
        final double minGain;
        final double maxGain;
        final long correctedPixels;
        NativeProspectiveShadingStats(int mapWidth, int mapHeight,
                                      double minGain, double maxGain, long correctedPixels) {
            this.mapWidth = mapWidth;
            this.mapHeight = mapHeight;
            this.minGain = minGain;
            this.maxGain = maxGain;
            this.correctedPixels = correctedPixels;
        }
    }

    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(
            short[] norm16, int width, int height, LensShadingMap map) {
        if (map == null) {
            throw new IllegalStateException("native prospective requires live physical LensShadingMap");
        }
        final int mapW = map.getColumnCount();
        final int mapH = map.getRowCount();
        float[] gains = new float[map.getGainFactorCount()];
        map.copyGainFactors(gains, 0);
        if (mapW < 1 || mapH < 1 || gains.length != mapW * mapH * 4) {
            throw new IllegalStateException("native prospective invalid LensShadingMap dimensions");
        }
        double minGain = Double.POSITIVE_INFINITY;
        double maxGain = Double.NEGATIVE_INFINITY;
        for (float g : gains) {
            if (!Float.isFinite(g) || g <= 0.0f) {
                throw new IllegalStateException("native prospective invalid LensShadingMap factor");
            }
            minGain = Math.min(minGain, g);
            maxGain = Math.max(maxGain, g);
        }

        final double xScale = width > 1 ? (mapW - 1.0) / (width - 1.0) : 0.0;
        final double yScale = height > 1 ? (mapH - 1.0) / (height - 1.0) : 0.0;
        long corrected = 0;
        for (int y = 0; y < height; y++) {
            double gy = y * yScale;
            int y0 = (int)Math.floor(gy);
            int y1 = Math.min(mapH - 1, y0 + 1);
            double fy = gy - y0;
            int row = y * width;
            int planeBase = (y & 1) * 2;
            for (int x = 0; x < width; x++) {
                double gx = x * xScale;
                int x0 = (int)Math.floor(gx);
                int x1 = Math.min(mapW - 1, x0 + 1);
                double fx = gx - x0;
                int plane = planeBase + (x & 1);
                int i00 = ((y0 * mapW + x0) * 4) + plane;
                int i01 = ((y0 * mapW + x1) * 4) + plane;
                int i10 = ((y1 * mapW + x0) * 4) + plane;
                int i11 = ((y1 * mapW + x1) * 4) + plane;
                double g0 = gains[i00] + fx * (gains[i01] - gains[i00]);
                double g1 = gains[i10] + fx * (gains[i11] - gains[i10]);
                double gain = g0 + fy * (g1 - g0);
                int index = row + x;
                double v = ((norm16[index] & 0xffff) / 65535.0) * gain;
                int q = (int)Math.floor(clamp(v, 0.0, 1.0) * 65535.0 + 0.5);
                norm16[index] = (short)(q & 0xffff);
                corrected++;
            }
        }
        return new NativeProspectiveShadingStats(mapW, mapH, minGain, maxGain, corrected);
    }
'''

last = renderer.rfind('\n}')
if last < 0:
    raise SystemExit('NATIVEPROSPECTIVE1A class closing brace missing')
renderer = renderer[:last] + helpers + renderer[last:]

hook_anchor = '''            diag.put("outputRole", primaryRoute ? "primary_photon_jpeg" : "legacy_m9_sidecar");
            // Do not overwrite capture-time lastDiagnostics here: a later shutter may already
'''
hook_insert = '''            diag.put("outputRole", primaryRoute ? "primary_photon_jpeg" : "legacy_m9_sidecar");

            if (primaryRoute) {
                Path nativeProspectivePath = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),
                        stem + "_M9_NATIVEPROSPECTIVE.jpg");
                Path nativeProspectiveJsonPath = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),
                        stem + "_M9_NATIVEPROSPECTIVE.json");
                Bitmap nativeProspectiveBitmap = null;
                JSONObject nativeProspectiveDiag = new JSONObject();
                long nativeProspectiveStartedNs = System.nanoTime();
                try {
                    CaptureResult physicalResult = M9PhysicalCaptureResult1A.resolve(
                            captureResult, params.cameraID);
                    if (!M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(
                            physicalResult, params.cameraID)) {
                        throw new IllegalStateException("native prospective physical CaptureResult mismatch");
                    }
                    RenderCore nativeProspective = renderNativeProspectiveCore(
                            frame.buffer, frame.width, frame.height,
                            encodedBlack, params.whiteLevel, params.whitePoint,
                            cameraRotation, 0.0, characteristics, physicalResult);
                    nativeProspectiveBitmap = nativeProspective.bitmap;
                    nativeProspectiveDiag = nativeProspective.diagnostics;
                    nativeProspectiveDiag.put("requestedCameraID", params.cameraID);
                    nativeProspectiveDiag.put("requestedPhysicalCameraId",
                            M9PhysicalCaptureResult1A.requestedPhysicalCameraId(params.cameraID));
                    String resultCameraId = M9PhysicalCaptureResult1A.resultCameraId(physicalResult);
                    nativeProspectiveDiag.put("captureResultCameraId",
                            resultCameraId != null ? resultCameraId : JSONObject.NULL);
                    nativeProspectiveDiag.put("outputPath", nativeProspectivePath.toString());
                    nativeProspectiveDiag.put("outputJsonPath", nativeProspectiveJsonPath.toString());
                    ParseExif.ExifData nativeExif = ParseExif.parse(captureResult, captureRequest);
                    boolean nativeSaved = ImageSaver.Util.saveBitmapAsJPG(
                            nativeProspectivePath, nativeProspectiveBitmap, JPEG_QUALITY, nativeExif);
                    if (nativeSaved) nativeProspectiveBitmap = null;
                    if (!nativeSaved) throw new IllegalStateException("native prospective JPEG save failed");
                    nativeProspectiveDiag.put("status", "success");
                } catch (Throwable nativeError) {
                    if (nativeProspectiveBitmap != null && !nativeProspectiveBitmap.isRecycled()) {
                        nativeProspectiveBitmap.recycle();
                    }
                    nativeProspectiveDiag = new JSONObject();
                    nativeProspectiveDiag.put("schema", "m9cam.renderer.nativeprospective.v1a.sourceadapter1a");
                    nativeProspectiveDiag.put("status", "failed_isolated_primary_preserved");
                    nativeProspectiveDiag.put("error", nativeError.toString());
                    nativeProspectiveDiag.put("outputPath", nativeProspectivePath.toString());
                    nativeProspectiveDiag.put("outputJsonPath", nativeProspectiveJsonPath.toString());
                }
                nativeProspectiveDiag.put("elapsedMs",
                        (System.nanoTime() - nativeProspectiveStartedNs) / 1_000_000.0);
                nativeProspectiveDiag.put("frozenPrimaryRenderCoreSha256",
                        "''' + frozen_render_core_sha + r'''");
                try {
                    Files.write(nativeProspectiveJsonPath,
                            nativeProspectiveDiag.toString(2).getBytes(StandardCharsets.UTF_8));
                    nativeProspectiveDiag.put("jsonPersisted", true);
                } catch (Throwable nativeJsonError) {
                    nativeProspectiveDiag.put("jsonPersisted", false);
                    nativeProspectiveDiag.put("jsonError", nativeJsonError.toString());
                }
                diag.put("nativeProspective1A", nativeProspectiveDiag);
            }

            // Do not overwrite capture-time lastDiagnostics here: a later shutter may already
'''
if hook_anchor not in renderer:
    raise SystemExit('NATIVEPROSPECTIVE1A post-primary hook anchor missing')
renderer = renderer.replace(hook_anchor, hook_insert, 1)

_, _, frozen_after = extract_method(renderer, '    private static RenderCore renderCore(')
if hashlib.sha256(frozen_after.encode('utf-8')).hexdigest() != frozen_render_core_sha:
    raise SystemExit('NATIVEPROSPECTIVE1A unexpectedly changed frozen renderCore')

if '-nativeprospective1a' not in gradle:
    version_re = re.compile(r"(versionName\s+['\"])([^'\"]+)(['\"])")
    m = version_re.search(gradle)
    if not m:
        raise SystemExit('NATIVEPROSPECTIVE1A versionName anchor missing')
    gradle = gradle[:m.start(2)] + m.group(2) + '-nativeprospective1a' + gradle[m.end(2):]

write(renderer_rel, renderer)
write(gradle_rel, gradle)

for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('NATIVEPROSPECTIVE1A changed frozen file: ' + rel)

print('M9 NATIVEPROSPECTIVE1A applied')
print(' - frozen renderCore sha256:', frozen_render_core_sha)
print(' - frozen primary JPEG is encoded before prospective branch starts')
print(' - prospective applies live physical Bayer GainMap exactly once before demosaic')
print(' - prospective source adapter uses Camera2 dual-illuminant sensor->XYZ D50; Cobalt CM/FM/HSM bypassed')
print(' - existing native m9color C++ unchanged; identity HSM + retained M9 bridge/TC20/SAT3/curve02/BT601/TG1')
print(' - emits *_M9_NATIVEPROSPECTIVE.jpg + *_M9_NATIVEPROSPECTIVE.json; any failure is isolated')
