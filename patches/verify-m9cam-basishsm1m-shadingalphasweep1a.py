#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1m-shadingalphasweep1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1M verifier missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required = [
    'BASISHSM1M-SHADINGALPHASWEEP1A',
    'm9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main',
    'm9cam.renderer.shadinglumadecomp.v1a',
    'private static JSONObject shadingLumaDecomp1AAudit(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA025_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA040_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA055_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA070_SHADING1A"',
    'int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3, 3};',
    'boolean[] selfMeterFlags = {true, true, true, true, true, true, true};',
    'boolean[] applyShadingFlags = {false, true, true, true, true, true, true};',
    'boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false, false};',
    'boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true, true};',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.25, 0.40, 0.55, 0.70};',
    '"main_physical_2_primary_vs_basis_hsm_shading_alpha_sweep1a"',
    'shadingLumaDecomp1APreDemosaicOnly", true',
    'shadingLumaDecomp1APostRenderVignette", false',
    'shadingLumaDecomp1AGlobalGuardFeedbackIntoGain", false',
    'shadingLumaDecomp1AFinalClipFeedbackIntoGain", false',
    'shadingLumaDecomp1APrimaryMutation", false',
    'chromaOnlyPreservesChannelRatiosWithin1e12',
    'alpha1ParityWithin1e12',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1M verifier missing renderer marker: ' + marker)

for stale in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_PARTIAL_LUMA_SHADING1A"',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.5};',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
]:
    if stale in renderer:
        raise SystemExit('BASISHSM1M verifier stale/forbidden output survived: ' + stale)

if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(') != 1:
    raise SystemExit('BASISHSM1M verifier full shading helper count mismatch')
if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(') != 1:
    raise SystemExit('BASISHSM1M verifier decomposition helper count mismatch')
if renderer.count('private static JSONObject shadingLumaDecomp1AAudit(') != 1:
    raise SystemExit('BASISHSM1M verifier decomposition audit count mismatch')

if '-basishsm1m-shadingalphasweep1a' not in gradle:
    raise SystemExit('BASISHSM1M verifier build provenance missing')
if '-basishsm1l-shadinglumadecomp1a' in gradle:
    raise SystemExit('BASISHSM1M verifier stale 1L build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1M verifier NOHDR boundary missing: ' + marker)

for forbidden in [
    'IsoExpoSelector.HDR = true;',
    'frameCount = 2;',
    'frameCount = 3;',
]:
    if forbidden in frames:
        raise SystemExit('BASISHSM1M verifier forbidden capture marker: ' + forbidden)

print('BASISHSM1M-SHADINGALPHASWEEP1A verification OK')
print(' - seven same-RAW diagnostic outputs present')
print(' - endpoints: OFF, full physical ON; decomposed alpha bank: 0, .25, .40, .55, .70')
print(' - no global shaded-guard or cap output variants')
print(' - validated 1L decomposition diagnostics and parity checks retained')
print(' - no post-render vignette / clip-feedback / Primary mutation path')
print(' - single RAW / HDR=false boundary present')
