#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1e-shadingdomain1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in [renderer_path, gradle_path, frames_path]:
    if not p.exists(): raise SystemExit('BASISHSM1E verify missing: ' + str(p))
renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required = [
    'm9cam.renderer.basishsm.shadingdomain.v1a.main',
    'shadingDomain1A',
    'shadingRepresentationRestoreApplied',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'restored_physical_shaded_camera_RGB',
    'shadingLateRepresentationScaleApplied',
    'cam16.convertTo(cam16, -1, nativeShading.representationScale, 0.0);',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
    'rawShadingResidual1AEnabled',
    'shadingParity1A',
    'meterParitySelfMeter',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1E verify missing renderer marker: ' + marker)

for forbidden in [
    'meterParityRenderBaseGain * nativeShading.representationScale',
    'effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale',
]:
    if forbidden in renderer:
        raise SystemExit('BASISHSM1E verify stale late-scale path survived: ' + forbidden)

if '-basishsm1e-shadingdomain1a' not in gradle:
    raise SystemExit('BASISHSM1E verify build provenance missing')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1E verify NOHDR boundary missing: ' + marker)

# Domain restore must exist only in the additive prospective path, never frozen Primary.
primary_start = renderer.find('    private static RenderCore renderCore(')
pros_start = renderer.find('    private static RenderCore renderNativeProspectiveCore(')
if primary_start < 0 or pros_start < 0 or primary_start >= pros_start:
    raise SystemExit('BASISHSM1E verify renderer method ordering unexpected')
primary_text = renderer[primary_start:pros_start]
if 'shadingDomain1A' in primary_text or 'shadingRepresentationRestoreApplied' in primary_text:
    raise SystemExit('BASISHSM1E verify leaked into frozen Primary renderCore')

print('BASISHSM1E-SHADINGDOMAIN1A verify OK')
print(' - representation restored post-demosaic before white-point/HSM/TC20')
print(' - late representation-scale gain removed')
print(' - RAW residual audit and SHADINGPARITY OFF/ON outputs retained')
print(' - frozen Primary and single-frame HDR=false boundary retained')
