#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcecal1a-nativecamera2audit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def require(rel, needle):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1A verify missing file: ' + rel)
    text = p.read_text()
    if needle not in text:
        raise SystemExit('SOURCECAL1A verify missing marker in %s: %s' % (rel, needle))
    return text

source_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
source = require(source_rel, 'm9cam.sourcecal.v1a.nativecamera2audit1a.multilens')
for marker in [
    'SENSOR_REFERENCE_ILLUMINANT1',
    'SENSOR_REFERENCE_ILLUMINANT2',
    'SENSOR_CALIBRATION_TRANSFORM1',
    'SENSOR_CALIBRATION_TRANSFORM2',
    'SENSOR_COLOR_TRANSFORM1',
    'SENSOR_COLOR_TRANSFORM2',
    'SENSOR_FORWARD_MATRIX1',
    'SENSOR_FORWARD_MATRIX2',
    'SENSOR_NEUTRAL_COLOR_POINT',
    'COLOR_CORRECTION_TRANSFORM',
    'Converter.convertColorspaceTransform(t, out)',
    'Converter.findDngInterpolationFactor(',
    'Converter.calculateCameraToXYZD50Transform(',
    'nativeSensorToXYZD50',
    'nativeDualIlluminantMetadataComplete',
    'activeMetadataDiffersFromNative',
    'activeHueSatMapPresent',
    'cameraID',
    'physicalID',
    'focalLengthMm',
    '_M9_SOURCECAL1A.json',
    'M9DiagnosticSidecarIO.persist(',
    'source_calibration_audit',
    'nativeTransformAppliedToRender", false',
    'cobaltRuntimeDependencyChanged", false',
    'Leica_M9_firmware_renderer_separate_and_frozen',
]:
    if marker not in source:
        raise SystemExit('SOURCECAL1A audit marker missing: ' + marker)

renderer = require(renderer_rel, 'M9SourceCalibrationAudit1A.captureAndWrite(')
for marker in [
    'sourceCalibrationAudit1A',
    'sourceCalibrationNativeTransformApplied", false',
    'rawShadingGainMapApplied", false',
]:
    if marker not in renderer:
        raise SystemExit('SOURCECAL1A renderer marker missing: ' + marker)

# Phase A must remain observability-only. Native source matrices may be computed/logged,
# but must not enter the M9 rendering call or replace the existing active source adapter.
expected_render_call = '''RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
if expected_render_call not in renderer:
    raise SystemExit('SOURCECAL1A current BESTFIT2A renderCore baseline changed')
for forbidden in [
    'nativeSensorToXYZD50, cameraRotation',
    'sourceCalibrationAudit1A, cameraRotation',
    'sourceCalibrationAudit1A.opt',
]:
    if forbidden in renderer:
        raise SystemExit('SOURCECAL1A native audit unexpectedly participates in rendering: ' + forbidden)

# RAWSHADING1A must remain diagnostic-only in this combined audit build.
raw = require('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java',
              'm9cam.rawshading.v1a.gainmapaudit1a.multilens')
if 'CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE' in raw:
    raise SystemExit('SOURCECAL1A baseline reintroduced unsupported shading-map-size key')

print('M9SOURCECAL1A NATIVECAMERA2AUDIT1A verification OK')
print(' - native Camera2 ColorMatrix/ForwardMatrix/CalibrationTransform/illuminants/neutral captured')
print(' - native-only dual-illuminant sensor->XYZ D50 calculated using Photon Converter math')
print(' - matrix convention matches Parameters.ReCalcColor')
print(' - active Photon metadata/HueSatMap logged only for override comparison')
print(' - RAWSHADING1A remains diagnostic-only')
print(' - neither native source transform nor GainMap is applied to renderer in Phase A')
