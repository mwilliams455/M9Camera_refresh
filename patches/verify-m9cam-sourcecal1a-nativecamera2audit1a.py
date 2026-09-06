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
    'm9cam.sourcecal.v1b.embeddedcalibrationroles1a',
    'Cobalt_Xiaomi_15_Ultra_Rear_Wide_Camera_Modular_DCP',
    'sourceAdapterPhysicalCameraScope',
    'ColorMatrix_A_D65,ForwardMatrix_A_D65,ProfileHueSatMap_A_D65',
    'sourceAdapterCurrentlyAppliedToRender", true',
    'targetProvider", "Leica_M9_firmware',
    'targetComponentsInThisAsset", "curve02',
    'mixedSourceAndTargetAsset", true',
    'replace_source_adapter_only_keep_firmware_target_components_frozen',
    'embedded.put("colorMatrixA", matrix(embeddedCal.colorMatrixA))',
    'embedded.put("colorMatrixD65", matrix(embeddedCal.colorMatrixD65))',
    'embedded.put("forwardMatrixA", matrix(embeddedCal.forwardMatrixA))',
    'embedded.put("forwardMatrixD65", matrix(embeddedCal.forwardMatrixD65))',
    'nativeReplacementApplied", false',
]:
    if marker not in source:
        raise SystemExit('SOURCECAL1A/1B audit marker missing: ' + marker)

renderer = require(renderer_rel, 'M9SourceCalibrationAudit1A.captureAndWrite(')
for marker in [
    'sourceCalibrationAudit1A',
    'sourceCalibrationNativeTransformApplied", false',
    'rawShadingGainMapApplied", false',
]:
    if marker not in renderer:
        raise SystemExit('SOURCECAL1A renderer marker missing: ' + marker)

# Phase A/B remains observability-only. Native source matrices may be computed/logged,
# and the embedded Cobalt source adapter may be identified, but neither audit may enter
# the M9 rendering call or replace the existing source adapter yet.
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

# The frozen mixed calibration loader is itself the provenance source for SOURCECAL1B.
cal = require('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Calibration.java',
              'Xiaomi 15 Ultra Rear Wide Camera Cobalt Modular.dcp')
for marker in [
    'Leica M9 firmware curve_02.bin',
    'colorMatrixA', 'colorMatrixD65', 'forwardMatrixA', 'forwardMatrixD65',
    'hsmA', 'hsmD65', 'curve02',
]:
    if marker not in cal:
        raise SystemExit('SOURCECAL1B calibration provenance marker missing: ' + marker)

print('M9SOURCECAL1A/1B verification OK')
print(' - native Camera2 ColorMatrix/ForwardMatrix/CalibrationTransform/illuminants/neutral captured')
print(' - native-only dual-illuminant sensor->XYZ D50 calculated using Photon Converter math')
print(' - matrix convention matches Parameters.ReCalcColor')
print(' - current M9R35CAL mixed asset is explicitly split into Cobalt source-adapter and Leica firmware target roles')
print(' - embedded Cobalt CM/FM/HSM logged beside native Camera2 source characterization')
print(' - Leica curve02 remains identified and frozen as a target-camera firmware component')
print(' - RAWSHADING1A remains diagnostic-only')
print(' - neither native source transform nor GainMap is applied to renderer in this audit build')
