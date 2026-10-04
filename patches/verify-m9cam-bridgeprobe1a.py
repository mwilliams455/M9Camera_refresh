#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-bridgeprobe1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('BRIDGEPROBE1A verifier: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in [renderer_path, gradle_path, frames_path]:
    if not p.exists():
        raise SystemExit('BRIDGEPROBE1A verifier missing: ' + str(p))
renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def require(src, marker, label):
    if marker not in src:
        raise SystemExit('BRIDGEPROBE1A verifier missing ' + label + ': ' + marker)


def forbid(src, marker, label):
    if marker in src:
        raise SystemExit('BRIDGEPROBE1A verifier forbidden ' + label + ': ' + marker)


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BRIDGEPROBE1A verifier method marker missing: ' + marker)
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
    raise SystemExit('BRIDGEPROBE1A verifier unterminated method')


prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

# Preserve the validated v2.91 source semantics and single-frame boundary.
for marker in [
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'storage_row_major_getElement_signature_column_row_copyElements_used',
    'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only',
    'sensorToXYZD50_forward_matrix_path_only_no_double_WB',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
]:
    require(renderer, marker, 'v2.91 invariant')
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    require(frames, marker, 'NOHDR1A boundary')

# Probe signature and role math.
for marker in [
    'int bridgeProbeMode',
    'bridgeProbeMode == 1',
    'bridgeProbeMode == 2',
    'ctx.hsm = new double[cal.hsmA.length];',
    'ctx.wA * cal.hsmA[i]',
    '(1.0 - ctx.wA) * cal.hsmD65[i]',
    'ctx.hueDivisions = cal.hueDivisions;',
    'ctx.satDivisions = cal.satDivisions;',
    'ColorContext historicalLinear = buildColorContext(neutralF, cal);',
    'historicalLinear.camToPp, inverse3(nativeCamToPpBeforeProbe)',
    'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);',
    'bridgeProbeHistoricalLinearMaxAbsDelta',
]:
    require(prospective, marker, 'probe role math')

# The prospective branch must still reuse the primary exposure decision and never meter itself.
for marker in ['tc20MeterNative(', 'tc20MeterNativeDirect(', 'METER_TARGET /']:
    forbid(prospective, marker, 'prospective re-metering')
require(prospective,
        'final double effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale;',
        'fixed primary gain boundary')

# Output hook is exactly three no-shading colour-role comparisons.
for marker in [
    '"_M9_NATIVE_SOURCE_ONLY"',
    '"_M9_NATIVE_HSM_ONLY"',
    '"_M9_NATIVE_BASIS_ONLY"',
    '"source_only"',
    '"native_plus_historical_hsm"',
    '"native_plus_historical_linear_basis"',
    'int[] bridgeProbeModes = {0, 1, 2};',
    'boolean applyShading = false;',
    'fixedPrimaryGain, applyShading, bridgeProbeMode)',
]:
    require(renderer, marker, 'three-way output hook')
for marker in ['"_M9_NATIVE_SOURCE_SHADING"', 'source_plus_shading', 'shadingFlags']:
    forbid(renderer, marker, 'old shading output')

# Diagnostic interpretation must be unambiguous.
for marker in [
    '"m9cam.renderer.bridgeprobe.v1a.main.fixedgain"',
    'd.put("bridgeProbe1A", true);',
    'd.put("bridgeProbeMode", bridgeProbeMode);',
    'd.put("bridgeProbeName", bridgeProbeName);',
    'd.put("bridgeProbeShadingApplied", nativeShading.applied);',
    'd.put("bridgeProbeExposureDecision", "frozen_primary_same_frame");',
    'd.put("bridgeProbeTargetBridge", "native_scene_white_existing_M9_bridge_unchanged");',
    'd.put("historicalLinearBasisDiagnosticApplied"',
    'd.put("historicalLinearBasisDerivedFromCobaltSourceProfile"',
    'd.put("bridgeProbeBasisMatrix", bridgeProbeBasisRows);',
]:
    require(prospective, marker, 'probe diagnostics')

# Baseline and basis modes keep identity HSM; only the HSM probe enables H25/S85/V100.
require(prospective,
        'd.put("hsmHueStrength", bridgeProbeHistoricalHsmApplied ? HSM_H : 0.0);',
        'dynamic HSM H strength')
require(prospective,
        'd.put("hsmSaturationStrength", bridgeProbeHistoricalHsmApplied ? HSM_S : 0.0);',
        'dynamic HSM S strength')
require(prospective,
        'd.put("hsmValueStrength", bridgeProbeHistoricalHsmApplied ? HSM_V : 0.0);',
        'dynamic HSM V strength')

# No photographic target constants changed by this patch; their frozen markers must remain present.
for marker in [
    'private static final double HSM_H = 0.25;',
    'private static final double HSM_S = 0.85;',
    'private static final double HSM_V = 1.00;',
    'public static final int SATURATION_BANK = 3;',
    'public static final int JPEG_QUALITY = 95;',
    'private static final double TG_NEG_CB_COMPRESSION = 0.25;',
    'private static final double TG_NEG_CR_COMPRESSION = 0.16;',
    'curve02 normal-ISO sRGB Standard',
]:
    require(renderer, marker, 'frozen target marker')

require(gradle, '-nativeapiorder1a-bridgeprobe1a', 'build provenance suffix')

print('M9 BRIDGEPROBE1A verified')
print(' - validated NATIVEAPIORDER1A + NATIVEWPCLIP1A source path retained')
print(' - single-frame NOHDR1A boundary retained')
print(' - SOURCE_ONLY / HSM_ONLY / BASIS_ONLY use same RAW and frozen primary gain')
print(' - LensShadingMap comparison removed from this colour-role experiment')
print(' - HSM_ONLY isolates historical nonlinear HSM role')
print(' - BASIS_ONLY isolates historical linear source-basis role with identity HSM')
print(' - M9 target bridge/SAT3/curve02/BT601/TG1/JPEG95 markers retained')
