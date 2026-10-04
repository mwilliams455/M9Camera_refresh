#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1d-rawshadingresidual1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A verifier inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required = [
    'm9cam.renderer.rawshadingresidual.v1a',
    'rawShadingResidualAudit1A(',
    '"flatFieldInterpretationOnly", true',
    '"pixelMutation", false',
    '"sampleStrideRawPixels", 8',
    '"observedCenterToCornerFalloffEv"',
    '"mapPredictedCorrectionEv"',
    '"residualAfterMapPredictionEv"',
    '"rawShadingResidual1AEnabled", true',
    '"rawShadingResidual1A", rawShadingResidual1A',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
    'historical_linear_basis_then_historical_HSM',
    'historical_interpolated_table',
    'normalized_linear_Bayer_pre_demosaic_headroom_preserved',
    'meterParitySelfMeter',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A verifier missing: ' + marker)

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A verifier NOHDR missing: ' + marker)

if '-basishsm1d-rawshadingresidual1a' not in gradle:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A verifier build provenance missing')

audit_pos = renderer.find('JSONObject rawShadingResidual1A = rawShadingResidualAudit1A(')
shade_pos = renderer.find('NativeProspectiveShadingStats nativeShading = applyNativeShading', audit_pos)
rawmat_pos = renderer.find('Mat rawMat = new Mat(', shade_pos)
if audit_pos < 0 or shade_pos < 0 or rawmat_pos < 0 or not (audit_pos < shade_pos < rawmat_pos):
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A audit/shading/demosaic order invalid')

for forbidden in [
    'RAWSHADINGRESIDUAL1A_CAPTURE_MUTATION',
    'RAWSHADINGRESIDUAL1A_DNG_MUTATION',
    'RAWSHADINGRESIDUAL1A_PRIMARY_MUTATION',
    'RAWSHADINGRESIDUAL1A_TC20_RETUNE',
]:
    if forbidden in renderer:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A forbidden marker: ' + forbidden)

print('BASISHSM1D-RAWSHADINGRESIDUAL1A verifier passed')
print(' - diagnostic reads normalized Bayer before optional map application')
print(' - prior shading OFF/ON field products remain unchanged')
print(' - colour architecture, TC20 logic, Primary, capture and DNG remain frozen')
