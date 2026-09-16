#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-dngphysicalmeta1b-trace.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p = root / rel
renderer = root / renderer_rel
if not p.exists() or not renderer.exists():
    raise SystemExit('DNGPHYSICALMETA1B missing expected assembled source')
renderer_before = hashlib.sha256(renderer.read_bytes()).hexdigest()
text = p.read_text()

anchor = 'import com.particlesdevs.photoncamera.processing.render.Parameters;\n'
insert = '''import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;

import org.json.JSONArray;
import org.json.JSONObject;
'''
if 'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;' not in text:
    if text.count(anchor) != 1:
        raise SystemExit('DNGPHYSICALMETA1B import anchor missing/ambiguous')
    text = text.replace(anchor, insert, 1)

method_anchor = '''        private static boolean saveSingleRawInternal(Path dngFilePath,
'''
helper = r'''        /** DNGPHYSICALMETA1B: read-only record of the exact metadata object handed to DngCreator. */
        private static void stageM9DngPhysicalMeta1B(Path dngFilePath,
                                                     Parameters parameters,
                                                     CameraCharacteristics characteristics,
                                                     CaptureResult captureResult,
                                                     int rawWidth,
                                                     int rawHeight) {
            if (dngFilePath == null || parameters == null || characteristics == null || captureResult == null) return;
            try {
                JSONObject out = new JSONObject();
                out.put("schema", "m9cam.dngphysicalmeta.v1b.writerinput");
                out.put("diagnosticOnly", true);
                out.put("rawBytesModified", false);
                out.put("jpegPixelsModified", false);
                out.put("dngPath", dngFilePath.toString());
                out.put("rawWidth", rawWidth);
                out.put("rawHeight", rawHeight);
                out.put("writerCfaPattern", (int) parameters.cfaPattern);
                out.put("writerWhiteLevel", parameters.whiteLevel);
                out.put("writerBlackLevel", floatArrayJson(parameters.blackLevel));
                out.put("writerUsedDynamicBlack", parameters.usedDynamic);
                out.put("writerNeutral", floatArrayJson(parameters.whitePoint));
                out.put("writerCalibrationIlluminant1", parameters.calibrationIlluminant1);
                out.put("writerCalibrationIlluminant2", parameters.calibrationIlluminant2);
                out.put("writerCalibrationTransform1", floatArrayJson(parameters.calibrationTransform1));
                out.put("writerCalibrationTransform2", floatArrayJson(parameters.calibrationTransform2));
                out.put("writerColorMatrix1", floatArrayJson(parameters.ColorMatrix1));
                out.put("writerColorMatrix2", floatArrayJson(parameters.ColorMatrix2));
                out.put("writerForwardMatrix1", floatArrayJson(parameters.ForwardTransform1));
                out.put("writerForwardMatrix2", floatArrayJson(parameters.ForwardTransform2));
                out.put("writerSensorToProPhoto", floatArrayJson(parameters.sensorToProPhoto));
                out.put("writerIso", parameters.iso);
                out.put("writerExposureTimeSeconds", parameters.exposureTime);

                Integer physicalCfa = characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT);
                Integer physicalWhite = characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL);
                android.hardware.camera2.params.BlackLevelPattern physicalBlack =
                        characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN);
                int[] physicalBlackValues = null;
                if (physicalBlack != null) {
                    physicalBlackValues = new int[4];
                    physicalBlack.copyTo(physicalBlackValues, 0);
                }
                out.put("physicalCharacteristicCfa", physicalCfa == null ? JSONObject.NULL : physicalCfa);
                out.put("physicalCharacteristicWhiteLevel", physicalWhite == null ? JSONObject.NULL : physicalWhite);
                out.put("physicalCharacteristicBlackLevel", intArrayJson(physicalBlackValues));
                out.put("physicalReferenceIlluminant1", nullableNumber(
                        characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1)));
                out.put("physicalReferenceIlluminant2", nullableNumber(
                        characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2)));
                out.put("physicalCalibrationTransform1", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1)));
                out.put("physicalCalibrationTransform2", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2)));
                out.put("physicalColorMatrix1", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1)));
                out.put("physicalColorMatrix2", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2)));
                out.put("physicalForwardMatrix1", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1)));
                out.put("physicalForwardMatrix2", transformJson(
                        characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2)));

                android.util.Rational[] neutral = captureResult.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
                JSONArray physicalNeutral = new JSONArray();
                if (neutral != null) {
                    for (android.util.Rational v : neutral) physicalNeutral.put(v.floatValue());
                }
                out.put("physicalCaptureNeutral", physicalNeutral);

                boolean cfaMatch = physicalCfa == null || ((int) parameters.cfaPattern == physicalCfa);
                boolean staticBlackMatch = parameters.usedDynamic || physicalBlackValues == null
                        || floatIntArrayEqual(parameters.blackLevel, physicalBlackValues, 1.0e-6f);
                boolean neutralMatch = neutral == null
                        || rationalFloatArrayEqual(neutral, parameters.whitePoint, 1.0e-6f);
                boolean cal1Match = transformMatches(parameters.calibrationTransform1,
                        characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1), 1.0e-6f);
                boolean cal2Match = transformMatches(parameters.calibrationTransform2,
                        characteristics.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2), 1.0e-6f);
                boolean cm1Match = transformMatches(parameters.ColorMatrix1,
                        characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1), 1.0e-6f);
                boolean cm2Match = transformMatches(parameters.ColorMatrix2,
                        characteristics.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2), 1.0e-6f);
                boolean fm1Match = transformMatches(parameters.ForwardTransform1,
                        characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1), 1.0e-6f);
                boolean fm2Match = transformMatches(parameters.ForwardTransform2,
                        characteristics.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2), 1.0e-6f);
                out.put("writerCfaMatchesPhysical", cfaMatch);
                out.put("writerStaticBlackMatchesPhysical", staticBlackMatch);
                out.put("writerNeutralMatchesPhysicalCapture", neutralMatch);
                out.put("writerCalibrationTransform1MatchesPhysical", cal1Match);
                out.put("writerCalibrationTransform2MatchesPhysical", cal2Match);
                out.put("writerColorMatrix1MatchesPhysical", cm1Match);
                out.put("writerColorMatrix2MatchesPhysical", cm2Match);
                out.put("writerForwardMatrix1MatchesPhysical", fm1Match);
                out.put("writerForwardMatrix2MatchesPhysical", fm2Match);
                out.put("writerPhysicalBindingPass", cfaMatch && staticBlackMatch && neutralMatch
                        && cal1Match && cal2Match && cm1Match && cm2Match && fm1Match && fm2Match);
                out.put("bindingAuthority",
                        "physical_CameraCharacteristics_plus_same_RAW_CaptureResult_after_ReCalcColorPhysical");

                String name = dngFilePath.getFileName().toString();
                int dot = name.lastIndexOf('.');
                String stem = dot > 0 ? name.substring(0, dot) : name;
                Path sidecar = dngFilePath.resolveSibling(stem + "_M9_DNGPHYSICALMETA1B.json");
                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
                byte[] frozen = out.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8);
                boolean staged = M9DiagnosticBurstSpool.stage(
                        sidecar, frozen, "dng_physical_metadata_writer_input");
                out.put("sidecarStaged", staged);
            } catch (Throwable t) {
                Log.e(TAG, "DNGPHYSICALMETA1B telemetry failed", t);
            }
        }

        private static JSONArray floatArrayJson(float[] values) {
            JSONArray out = new JSONArray();
            if (values != null) for (float v : values) out.put(v);
            return out;
        }

        private static JSONArray intArrayJson(int[] values) {
            JSONArray out = new JSONArray();
            if (values != null) for (int v : values) out.put(v);
            return out;
        }

        private static Object nullableNumber(Object value) {
            return value == null ? JSONObject.NULL : value;
        }

        private static JSONArray transformJson(
                android.hardware.camera2.params.ColorSpaceTransform transform) {
            JSONArray out = new JSONArray();
            if (transform == null) return out;
            android.util.Rational[] values = new android.util.Rational[9];
            transform.copyElements(values, 0);
            for (android.util.Rational v : values) out.put(v.floatValue());
            return out;
        }

        private static boolean transformMatches(float[] writer,
                                                android.hardware.camera2.params.ColorSpaceTransform transform,
                                                float tolerance) {
            if (transform == null) return true;
            if (writer == null || writer.length < 9) return false;
            android.util.Rational[] values = new android.util.Rational[9];
            transform.copyElements(values, 0);
            for (int i = 0; i < 9; i++) {
                if (Math.abs(writer[i] - values[i].floatValue()) > tolerance) return false;
            }
            return true;
        }

        private static boolean floatIntArrayEqual(float[] a, int[] b, float tolerance) {
            if (a == null || b == null || a.length < b.length) return false;
            for (int i = 0; i < b.length; i++) {
                if (Math.abs(a[i] - b[i]) > tolerance) return false;
            }
            return true;
        }

        private static boolean rationalFloatArrayEqual(android.util.Rational[] a,
                                                       float[] b,
                                                       float tolerance) {
            if (a == null || b == null || b.length < a.length) return false;
            for (int i = 0; i < a.length; i++) {
                if (Math.abs(a[i].floatValue() - b[i]) > tolerance) return false;
            }
            return true;
        }

'''
if 'stageM9DngPhysicalMeta1B(' not in text:
    if text.count(method_anchor) != 1:
        raise SystemExit('DNGPHYSICALMETA1B helper insertion anchor missing/ambiguous')
    text = text.replace(method_anchor, helper + method_anchor, 1)

call_anchor = '''            parameters.cameraRotation = cameraRotation;
            Log.d(TAG, "Camera rotation: " + parameters.cameraRotation);
'''
call_new = '''            parameters.cameraRotation = cameraRotation;
            if (physicalCfaAuthority) {
                stageM9DngPhysicalMeta1B(dngFilePath, parameters, characteristics, captureResult,
                        image.width, image.height);
            }
            Log.d(TAG, "Camera rotation: " + parameters.cameraRotation);
'''
if 'stageM9DngPhysicalMeta1B(dngFilePath, parameters' not in text:
    if text.count(call_anchor) != 1:
        raise SystemExit('DNGPHYSICALMETA1B call anchor missing/ambiguous')
    text = text.replace(call_anchor, call_new, 1)
p.write_text(text)
post = p.read_text()
for marker in [
    'm9cam.dngphysicalmeta.v1b.writerinput',
    'writerPhysicalBindingPass',
    'writerColorMatrix1MatchesPhysical',
    'writerNeutralMatchesPhysicalCapture',
    'M9DiagnosticBurstSpool.stage(',
    'dng_physical_metadata_writer_input',
    'parameters.ReCalcColorPhysical(false, captureResult, characteristics);',
]:
    if marker not in post:
        raise SystemExit('DNGPHYSICALMETA1B required marker missing: ' + marker)
if 'M9DiagnosticSidecarIO.persist(' in post:
    raise SystemExit('DNGPHYSICALMETA1B must not add blocking sidecar IO')
if hashlib.sha256(renderer.read_bytes()).hexdigest() != renderer_before:
    raise SystemExit('DNGPHYSICALMETA1B unexpectedly changed renderer')

print('DNGPHYSICALMETA1B writer-input trace applied')
print(' - records exact Parameters metadata handed to DngCreator after physical rebinding')
print(' - compares CFA/black/neutral/calibration/CM/FM against same physical job authority')
print(' - telemetry uses existing private SIDECAR1B spool')
print(' - RAW bytes, DNG pixel payload and JPEG renderer unchanged')
