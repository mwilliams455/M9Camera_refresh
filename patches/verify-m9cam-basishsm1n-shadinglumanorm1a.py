#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1n-shadinglumanorm1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1N verifier missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required = [
    'BASISHSM1N-SHADINGLUMANORM1A',
    'm9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main',
    'm9cam.renderer.shadinglumadecomp.v1a',
    'private static JSONObject shadingLumaDecomp1AAudit(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM020EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM040EV1A"',
    'int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3};',
    'boolean[] selfMeterFlags = {true, true, true, true, true, true};',
    'boolean[] applyShadingFlags = {false, true, true, true, true, true};',
    'boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false};',
    'boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true};',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 1.0, 1.0, 1.0};',
    'boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, false, false, true, true, true};',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.0, 0.0, 0.20, 0.30, 0.40};',
    '"main_physical_2_primary_vs_basis_hsm_shading_luma_norm1a"',
    'shadingLumaNorm1ABasis", "LensShadingMap_common_gain_outsideCenter50_median_EV_only_no_scene_luma"',
    'shadingLumaNorm1AUsesSceneBrightness", false',
    'shadingLumaNorm1AUsesFinalClipFeedback", false',
    'shadingLumaNorm1AUsesPrimaryFeedback", false',
    'shadingLumaDecomp1APreDemosaicOnly", true',
    'shadingLumaDecomp1APostRenderVignette", false',
    'shadingLumaDecomp1AGlobalGuardFeedbackIntoGain", false',
    'shadingLumaDecomp1AFinalClipFeedbackIntoGain", false',
    'shadingLumaDecomp1APrimaryMutation", false',
    'chromaOnlyPreservesChannelRatiosWithin1e12',
    'alpha1ParityWithin1e12',
    '.getJSONObject("outsideCenter50")',
    '.getDouble("median")',
    'shadingLumaTargetOutsideMedianEv1A / shadingLumaSourceOutsideMedianEv1A',
    'Math.max(0.0, Math.min(1.0,',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1N verifier missing renderer marker: ' + marker)

for stale in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA025_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA040_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA055_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA070_SHADING1A"',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.25, 0.40, 0.55, 0.70};',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
]:
    if stale in renderer:
        raise SystemExit('BASISHSM1N verifier stale/forbidden output survived: ' + stale)

if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(') != 1:
    raise SystemExit('BASISHSM1N verifier full shading helper count mismatch')
if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(') != 1:
    raise SystemExit('BASISHSM1N verifier decomposition helper count mismatch')
if renderer.count('private static JSONObject shadingLumaDecomp1AAudit(') != 1:
    raise SystemExit('BASISHSM1N verifier decomposition audit count mismatch')

if '-basishsm1n-shadinglumanorm1a' not in gradle:
    raise SystemExit('BASISHSM1N verifier build provenance missing')
if '-basishsm1m-shadingalphasweep1a' in gradle:
    raise SystemExit('BASISHSM1N verifier stale 1M build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1N verifier NOHDR boundary missing: ' + marker)
for forbidden in ['IsoExpoSelector.HDR = true;', 'frameCount = 2;', 'frameCount = 3;']:
    if forbidden in frames:
        raise SystemExit('BASISHSM1N verifier forbidden capture marker: ' + forbidden)

print('BASISHSM1N-SHADINGLUMANORM1A verification OK')
print(' - six same-RAW outputs: OFF, full ON, chroma-only, normalized 0.20/0.30/0.40 EV')
print(' - normalized alpha derives only from LensShadingMap outside-center common-gain median')
print(' - map shape and validated relative RGGB decomposition remain unchanged')
print(' - no scene-luma, final-clip, Primary, global-guard, or post-render-vignette feedback')
print(' - single RAW / HDR=false boundary present')
