#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1c-shadingparity1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('SHADINGPARITY1A verify: required assembled file missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('SHADINGPARITY1A verify method marker missing: ' + marker)
    brace = src.find('{', start)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n': state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*': state = 'block_comment'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return src[start:i + 1]
        i += 1
    raise SystemExit('SHADINGPARITY1A verify unterminated method: ' + marker)


# Capture hard boundary must still be explicit in the assembled Photon tree.
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('SHADINGPARITY1A verify NOHDR marker missing: ' + marker)

if '-basishsm1c-shadingparity1a' not in gradle:
    raise SystemExit('SHADINGPARITY1A verify build provenance missing')

primary = extract_method(renderer, '    private static RenderCore renderCore(')
prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

# The experiment must remain additive; the frozen Primary cannot acquire any new seams.
for forbidden in [
    'shadingParity1A',
    'applyNativeShading',
    'applyNativeProspectiveGainMap',
    '_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_',
]:
    if forbidden in primary:
        raise SystemExit('SHADINGPARITY1A verify leaked experiment into frozen Primary: ' + forbidden)

# Validated colour and meter architecture remains present in the prospective renderer.
for marker in [
    'historical_linear_basis_then_historical_HSM',
    'basisHsmCombinedApplied',
    'meterParity1A',
    'native_basis_hsm_same_frame_tc20',
    'meterParitySelfMeter',
    'm9cam.renderer.basishsm.shadingparity.v1a.main',
]:
    if marker not in prospective:
        raise SystemExit('SHADINGPARITY1A verify prospective architecture marker missing: ' + marker)

# The historical-table interpolation label lives in the shared checkpoint/helper code,
# outside renderNativeProspectiveCore; verify it at renderer scope rather than mis-scoping it.
for marker in [
    'historical_interpolated_table',
    'checkpointHsmMode',
    'checkpointIdentityHsmSentinel',
]:
    if marker not in renderer:
        raise SystemExit('SHADINGPARITY1A verify shared BASIS/HSM marker missing: ' + marker)

# LensShadingMap must be optional and must be consumed on normalized Bayer before demosaic.
for marker in [
    'NativeProspectiveShadingStats nativeShading = applyNativeShading',
    'applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)',
    'NativeProspectiveShadingStats.none()',
    'gainMapApplicationStage',
    'normalized_linear_Bayer_pre_demosaic_headroom_preserved',
    'gainMapRepresentationScale',
    'gainMapPostScaleClipCount',
    'singleFrameLinearHeadroomPreserved',
]:
    if marker not in prospective:
        raise SystemExit('SHADINGPARITY1A verify shading seam marker missing: ' + marker)
shade_pos = prospective.find('NativeProspectiveShadingStats nativeShading = applyNativeShading')
rawmat_pos = prospective.find('Mat rawMat = new Mat(')
if shade_pos < 0 or rawmat_pos < 0 or shade_pos >= rawmat_pos:
    raise SystemExit('SHADINGPARITY1A verify gain map is not pre-demosaic')

# Field outputs: same self-meter treatment, only shading OFF/ON differs.
required_global = [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
    '"native_plus_historical_basis_hsm_self_meter_shading_off"',
    '"native_plus_historical_basis_hsm_self_meter_shading_on"',
    'int[] bridgeProbeModes = {3, 3};',
    'boolean[] selfMeterFlags = {true, true};',
    'boolean[] applyShadingFlags = {false, true};',
    'boolean applyShading = applyShadingFlags[variantIndex];',
    'shadingParityRequested',
    'shadingParityApplied',
    'shadingParityApplicationCount',
    'shadingParityAllBayerSitesCorrected',
    'shadingParitySelfMeterAfterShading',
    '"main_physical_2_primary_vs_basis_hsm_selfmeter_shading_off_on"',
]
for marker in required_global:
    if marker not in renderer:
        raise SystemExit('SHADINGPARITY1A verify field marker missing: ' + marker)

for obsolete in [
    '"_M9_NATIVE_BASIS_HSM"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER"',
    '"native_plus_historical_basis_hsm_fixed_primary_gain"',
    'boolean[] selfMeterFlags = {false, true};',
]:
    if obsolete in renderer:
        raise SystemExit('SHADINGPARITY1A verify obsolete METERPARITY field control survived: ' + obsolete)

# Capture/DNG statements remain diagnostics only; no experiment may claim capture mutation.
for marker in [
    'meterParityCaptureExposureMutation", false',
    'sameRawAsPrimary',
    'primaryTreatment", "FROZEN"',
]:
    if marker not in renderer:
        raise SystemExit('SHADINGPARITY1A verify frozen-boundary diagnostic missing: ' + marker)

print('M9Cam BASISHSM1C-SHADINGPARITY1A verification OK')
print(' - NOHDR single-frame boundary explicit')
print(' - frozen Primary contains no shading experiment seams')
print(' - native+basis+HSM and self-owned TC20 retained')
print(' - field variants are self-meter shading OFF vs ON only')
print(' - GainMap application occurs once on normalized Bayer before demosaic when requested')
