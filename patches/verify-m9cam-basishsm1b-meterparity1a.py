#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1b-meterparity1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
iso_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
for p in [renderer_path, gradle_path, frames_path, iso_path]:
    if not p.exists():
        raise SystemExit('BASISHSM1B-METERPARITY1A verify missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()
iso = iso_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('verify method marker missing: ' + marker)
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
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return src[start:i + 1]
        i += 1
    raise SystemExit('verify unterminated method: ' + marker)


def require(src, marker, label):
    if marker not in src:
        raise SystemExit('BASISHSM1B-METERPARITY1A missing ' + label + ': ' + marker)


def forbid(src, marker, label):
    if marker in src:
        raise SystemExit('BASISHSM1B-METERPARITY1A forbidden ' + label + ': ' + marker)


primary = extract_method(renderer, '    private static RenderCore renderCore(')
prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

# Frozen Primary must not become the new self-meter experiment implicitly.
for marker in ['meterParity1A', 'meterParitySelfMeter', 'boolean selfMeter',
               'native_basis_hsm_same_frame_tc20']:
    forbid(primary, marker, 'Primary mutation marker')
require(primary, 'edgePlacementGainEv', 'existing JPEG-only edge policy')
require(primary, 'tc20MeterNative', 'frozen Primary TC20 path')

# The additive prospective path must contain the validated basis/HSM role and both meter modes.
for marker in [
    'boolean selfMeter',
    'final boolean meterParitySelfMeter = selfMeter;',
    'if (meterParitySelfMeter)',
    'tc20MeterNativeDirect(',
    'tc20MeterNative(',
    'native_basis_hsm_same_frame_tc20',
    'frozen_primary_same_frame',
    'meterParityReferencePrimaryEffectiveGain',
    'meterParityNativeTc20BaselineGain',
    'meterParityGainDeltaEvVsPrimary',
    'meterParityCaptureExposureMutation", false',
    'historical_linear_basis_then_historical_HSM',
    'checkpointIdentityHsmSentinel',
    'historical_interpolated_table',
    'meterParityRawShadingForcedOffByCaller", true',
]:
    require(prospective, marker, 'prospective invariant')

# Field outputs now isolate meter parity only. SOURCE_ONLY is retired from the hook.
hook_start = renderer.find('            // BASISHSM1B-METERPARITY1A: same-RAW BASIS_HSM fixed-vs-self-meter.')
hook_end = renderer.find('\n            // Do not overwrite capture-time lastDiagnostics here:', hook_start)
if hook_start < 0 or hook_end < 0:
    raise SystemExit('BASISHSM1B-METERPARITY1A field hook missing')
hook = renderer[hook_start:hook_end]
for marker in [
    '"_M9_NATIVE_BASIS_HSM"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER"',
    'int[] bridgeProbeModes = {3, 3};',
    'boolean[] selfMeterFlags = {false, true};',
    'selfMeter ? primaryEdgeEv : 0.0',
    'fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter',
    'boolean applyShading = false;',
    'meterParitySelfMeterRequested',
    'primaryOutputPreserved", true',
]:
    require(hook, marker, 'field hook invariant')
for marker in ['"_M9_NATIVE_SOURCE_ONLY"', '"_M9_NATIVE_HSM_ONLY"',
               '"_M9_NATIVE_BASIS_ONLY"', '"_M9_NATIVE_SOURCE_SHADING"']:
    forbid(hook, marker, 'retired field output')

# No-HDR single-frame capture boundary stays exactly in force.
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;']:
    require(frames, marker, 'NOHDR single-frame boundary')
require(iso, 'IsoExpoSelector.HDR = false;', 'HDR disabled boundary')

require(gradle, '-basishsm1b-meterparity1a', 'build provenance')
forbid(gradle, '-basishsm1a-fix2', 'stale build suffix')

print('M9 BASISHSM1B-METERPARITY1A verification OK')
print(' - Primary renderCore remains outside meter-parity experiment')
print(' - fixed BASIS_HSM control + self-meter BASIS_HSM only')
print(' - self-meter uses same native+basis+HSM context and frozen Primary edge policy')
print(' - shading OFF, capture exposure/DNG/HDR boundary unchanged')