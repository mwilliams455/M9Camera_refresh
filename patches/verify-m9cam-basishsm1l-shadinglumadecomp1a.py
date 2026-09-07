#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1l-shadinglumadecomp1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1L verifier missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required_renderer = [
    'm9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main',
    'm9cam.renderer.shadinglumadecomp.v1a',
    'private static JSONObject shadingLumaDecomp1AAudit(',
    'private static JSONObject shadingLumaDecomp1ASkipped(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    'lumaDecomp1AEnabled", true',
    'lumaDecomp1ARenderApplied',
    'lumaAuthorityAlpha',
    'shadingLumaDecomp1APreDemosaicOnly", true',
    'shadingLumaDecomp1APostRenderVignette", false',
    'shadingLumaDecomp1AGlobalGuardFeedbackIntoGain", false',
    'shadingLumaDecomp1AFinalClipFeedbackIntoGain", false',
    'shadingLumaDecomp1APrimaryMutation", false',
    'commonGainGeometricMean',
    'commonGainCenter50',
    'commonGainOutsideCenter50',
    'relativeChannelGain',
    'reconstructedGainMapParity',
    'chromaOnlyRatioPreservation',
    'commonLuminanceSuppressionByRegion',
    'Math.exp(0.25 * logSum)',
    'Math.exp(alpha * Math.log(gc))',
    'src[base + p] / gc',
    'fullPhysicalShadingControl',
    'shadedTailSpatial1ARun = fullPhysicalShadingControl',
    'private static JSONObject finalClipAudit1A(',
    'finalClipAudit1AEnabled", true',
    'private static JSONObject shadedTailSpatialAudit1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_PARTIAL_LUMA_SHADING1A"',
    'boolean[] applyShadedGuard1AFlags = {false, false, false, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};',
    'boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true};',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.5};',
    'main_physical_2_primary_vs_basis_hsm_shading_luma_decomp1a',
]
for marker in required_renderer:
    if marker not in renderer:
        raise SystemExit('BASISHSM1L verifier missing renderer marker: ' + marker)

if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(') != 1:
    raise SystemExit('BASISHSM1L verifier exact physical shading helper count mismatch')
if renderer.count('private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(') != 1:
    raise SystemExit('BASISHSM1L verifier decomposition helper count mismatch')
if renderer.count('private static JSONObject shadingLumaDecomp1AAudit(') != 1:
    raise SystemExit('BASISHSM1L verifier decomposition audit count mismatch')

for obsolete_output in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
]:
    if obsolete_output in renderer:
        raise SystemExit('BASISHSM1L verifier obsolete global-guard output survived: ' + obsolete_output)

if '-basishsm1l-shadinglumadecomp1a' not in gradle:
    raise SystemExit('BASISHSM1L verifier build provenance missing')
if '-basishsm1k-shadedtailspatial1a' in gradle:
    raise SystemExit('BASISHSM1L verifier stale 1K build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1L verifier NOHDR boundary missing: ' + marker)

for forbidden in [
    'IsoExpoSelector.HDR = true;',
    'frameCount = 2;',
    'frameCount = 3;',
]:
    if forbidden in frames:
        raise SystemExit('BASISHSM1L verifier forbidden capture marker: ' + forbidden)

print('BASISHSM1L-SHADINGLUMADECOMP1A verification OK')
print(' - same-RAW OFF / exact ON / CHROMA_ONLY / PARTIAL_LUMA outputs present')
print(' - full physical LensShadingMap helper retained alongside isolated decomposition helper')
print(' - geometric-mean common gain and relative-channel reconstruction diagnostics present')
print(' - alpha=0 and alpha=0.5 candidate controls present; alpha=1 parity audit retained')
print(' - global SHADEDGUARD and CAP20 output requests disabled')
print(' - FINALCLIPAUDIT1A and spatial audit retained')
print(' - no post-render vignette or final-clip feedback path introduced')
print(' - single RAW and HDR=false boundary present')
