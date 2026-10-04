#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1o-lumanorm030accept1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1O verify missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required = [
    'BASISHSM1O-LUMANORM030ACCEPT1A: same-RAW photographic acceptance bank.',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    'int[] bridgeProbeModes = {3, 3, 3};',
    'boolean[] selfMeterFlags = {true, true, true};',
    'boolean[] applyShadingFlags = {false, true, true};',
    'boolean[] applyShadingLumaDecomp1AFlags = {false, true, false};',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 1.0};',
    'boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, true, false};',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.30, 0.0};',
    '"main_physical_2_primary_vs_basis_hsm_lumanorm030_accept1a"',
    '"shadingLumaNorm1ABasis", "LensShadingMap_common_gain_outsideCenter50_median_EV_only_no_scene_luma"',
    '"shadingLumaNorm1AUsesSceneBrightness", false',
    '"shadingLumaNorm1AUsesFinalClipFeedback", false',
    '"shadingLumaNorm1AUsesPrimaryFeedback", false',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1O verify required marker missing: ' + marker)

for forbidden in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM020EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM040EV1A"',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.0, 0.0, 0.20, 0.30, 0.40};',
]:
    if forbidden in renderer:
        raise SystemExit('BASISHSM1O verify stale 1N bank marker present: ' + forbidden)

if '-basishsm1o-lumanorm030accept1a' not in gradle:
    raise SystemExit('BASISHSM1O verify provenance missing')
if '-basishsm1n-shadinglumanorm1a' in gradle:
    raise SystemExit('BASISHSM1O verify stale provenance present')

for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1O verify NOHDR boundary missing: ' + marker)

for forbidden in ['IsoExpoSelector.HDR = true;', 'frameCount = 2;', 'frameCount = 3;']:
    if forbidden in frames:
        raise SystemExit('BASISHSM1O verify forbidden capture marker present: ' + forbidden)

print('M9Cam BASISHSM1O-LUMANORM030ACCEPT1A verification passed')
print(' - bank count: 3 (OFF / NORM030 / exact ON)')
print(' - 0.30 EV normalization remains map-only and feedback-free')
print(' - single-frame / HDR=false boundary present')
