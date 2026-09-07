#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('BASISHSM1A verifier: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in [renderer_path, gradle_path, frames_path]:
    if not p.exists(): raise SystemExit('BASISHSM1A verifier missing: ' + str(p))

renderer = renderer_path.read_text(); gradle = gradle_path.read_text(); frames = frames_path.read_text()

def require(src, marker, label):
    if marker not in src: raise SystemExit('BASISHSM1A verifier missing ' + label + ': ' + marker)

def forbid(src, marker, label):
    if marker in src: raise SystemExit('BASISHSM1A verifier forbidden ' + label + ': ' + marker)

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0: raise SystemExit('BASISHSM1A verifier method marker missing: ' + marker)
    brace = src.find('{', start); depth = 0; i = brace; state = 'code'; quote = ''; escape = False
    while i < len(src):
        ch = src[i]; nxt = src[i + 1] if i + 1 < len(src) else ''
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
    raise SystemExit('BASISHSM1A verifier unterminated method')

prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

for marker in [
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'storage_row_major_getElement_signature_column_row_copyElements_used',
    'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only',
    'sensorToXYZD50_forward_matrix_path_only_no_double_WB',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
]: require(renderer, marker, 'v2.91 invariant')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY','frameCount = 1;','throwCount = 0;','IsoExpoSelector.HDR = false;']:
    require(frames, marker, 'NOHDR1A boundary')

for marker in ['d.put("bridgeProbe1A", true);','bridgeProbeMode == 1','bridgeProbeMode == 2','historicalLinear.camToPp, inverse3(nativeCamToPpBeforeProbe)']:
    require(prospective, marker, 'BRIDGEPROBE1A foundation')

for marker in [
    'bridgeProbeMode == 3',
    'bridgeProbeName = "native_plus_historical_basis_hsm";',
    'bridgeProbeHistoricalLinearBasisApplied = true;',
    'bridgeProbeHistoricalHsmApplied = true;',
    'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);',
    'ctx.hsm = new double[cal.hsmA.length];',
    'ctx.wA * cal.hsmA[i]',
    '(1.0 - ctx.wA) * cal.hsmD65[i]',
    'ctx.hueDivisions = cal.hueDivisions;',
    'ctx.satDivisions = cal.satDivisions;',
]: require(prospective, marker, 'combined role math')
basis_pos = prospective.find('ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);', prospective.find('bridgeProbeMode == 3'))
hsm_pos = prospective.find('ctx.hsm = new double[cal.hsmA.length];', basis_pos)
if basis_pos < 0 or hsm_pos < 0 or basis_pos >= hsm_pos:
    raise SystemExit('BASISHSM1A verifier ordering failure: historical basis must precede HSM')

for marker in ['tc20MeterNative(', 'tc20MeterNativeDirect(', 'METER_TARGET /']:
    forbid(prospective, marker, 'prospective re-metering')
require(prospective, 'final double effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale;', 'fixed primary gain boundary')

for marker in [
    '"_M9_NATIVE_SOURCE_ONLY"','"_M9_NATIVE_BASIS_HSM"','"source_only"',
    '"native_plus_historical_basis_hsm"','int[] bridgeProbeModes = {0, 3};',
    'boolean applyShading = false;','fixedPrimaryGain, applyShading, bridgeProbeMode)',
]: require(renderer, marker, 'minimal output hook')
for marker in ['"_M9_NATIVE_HSM_ONLY"','"_M9_NATIVE_BASIS_ONLY"','"_M9_NATIVE_SOURCE_SHADING"','source_plus_shading','shadingFlags']:
    forbid(renderer, marker, 'retired field output')

for marker in [
    'private static JSONObject basisHsmTraceCheckpoint(', '"normalizedSensorRgb"',
    '"postNativeWpClipRgb"','"xyzD50"','"nativeLinearWorkingRgb"',
    '"postHistoricalBasisRgb"','"hsmInputWorkingRgb"','"hsmInputHsv"',
    '"hsmOutputRgb"','"m9BridgeInputRgb"','"m9BridgeOutputRgb"',
    '"postSat3PreCurveIndices"','"postCurve02PreBt601Rgb8"',
    '"capture_sensor_neutral"','"demosaic_fixed_sample_" + i',
]: require(renderer, marker, 'checkpoint instrumentation')

for marker in [
    '"m9cam.renderer.basishsm.v1a.main.fixedgain"','d.put("basisHsm1A", true);',
    'd.put("basisHsmCombinedApplied", bridgeProbeMode == 3);',
    '"historical_linear_basis_then_historical_HSM"',
    'd.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3);',
    '"cal.hsmA_plus_cal.hsmD65_interpolated_by_native_wA"',
    'Long.toUnsignedString(bridgeProbeHsmHash64, 16)',
    'd.put("basisHsmCheckpointSamples", basisHsmCheckpoints);',
    '"historical_linear_basis_plus_HSM_role_diagnostic_plus_curve02_target_component"',
]: require(prospective, marker, 'BASISHSM diagnostics')

for marker in [
    'd.put("cobaltColorMatrixApplied", false);','d.put("cobaltForwardMatrixApplied", false);',
    'private static final double HSM_H = 0.25;','private static final double HSM_S = 0.85;',
    'private static final double HSM_V = 1.00;','public static final int SATURATION_BANK = 3;',
    'public static final int JPEG_QUALITY = 95;','private static final double TG_NEG_CB_COMPRESSION = 0.25;',
    'private static final double TG_NEG_CR_COMPRESSION = 0.16;','curve02 normal-ISO sRGB Standard',
]: require(renderer, marker, 'frozen source/target marker')

require(gradle, '-nativeapiorder1a-basishsm1a', 'build provenance suffix')
forbid(gradle, '-nativeapiorder1a-bridgeprobe1a', 'stale BRIDGEPROBE build suffix')

print('M9 BASISHSM1A verified')
print(' - NATIVEAPIORDER1A + NATIVEWPCLIP1A Camera2 source path retained')
print(' - single-frame NOHDR1A boundary retained')
print(' - SOURCE_ONLY / BASIS_HSM use same RAW and frozen primary gain')
print(' - LensShadingMap remains OFF for the colour-role experiment')
print(' - historical linear basis is applied before historical HSM')
print(' - neutral + five fixed same-RAW checkpoint traces are present')
print(' - output set reduced to SOURCE_ONLY + BASIS_HSM while frozen Primary remains normal')
print(' - M9 bridge/SAT3/curve02/BT601/TG1/JPEG95 constants retained')
