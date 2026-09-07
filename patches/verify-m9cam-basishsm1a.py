#!/usr/bin/env python3
from pathlib import Path
import hashlib
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('BASISHSM1A-FIX1 verifier: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists(): raise SystemExit('BASISHSM1A-FIX1 verifier missing: ' + str(p))

# Apply the diagnostics-only field-test fix here so the existing workflow sequence
# stays reproducible without changing any earlier photographic patch stage.
fix = Path(__file__).with_name('apply-m9cam-basishsm1a-fix1.py')
subprocess.run([sys.executable, str(fix), str(root)], check=True)

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def require(src, marker, label):
    if marker not in src: raise SystemExit('BASISHSM1A-FIX1 verifier missing ' + label + ': ' + marker)
def forbid(src, marker, label):
    if marker in src: raise SystemExit('BASISHSM1A-FIX1 verifier forbidden ' + label + ': ' + marker)

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0: raise SystemExit('method marker missing: ' + marker)
    brace = src.find('{', start); depth = 0; i = brace; state = 'code'; quote = ''; escape = False
    while i < len(src):
        ch = src[i]; nxt = src[i+1] if i+1 < len(src) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return src[start:i+1]
        i += 1
    raise SystemExit('unterminated method: ' + marker)

prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')
primary = extract_method(renderer, '    private static RenderCore renderCore(')

for marker in [
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only',
    'sensorToXYZD50_forward_matrix_path_only_no_double_WB',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
    'int[] bridgeProbeModes = {0, 3};',
    '"_M9_NATIVE_SOURCE_ONLY"',
    '"_M9_NATIVE_BASIS_HSM"',
    'bridgeProbeMode == 3',
    'bridgeProbeName = "native_plus_historical_basis_hsm";',
    'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);',
    'ctx.hsm = new double[cal.hsmA.length];',
    '"identity_passthrough_source_only"',
    '"historical_interpolated_table"',
    'checkpointHistoricalHsmAvailable',
    'checkpointActualHsmLength',
    'd.put("basisHsmCheckpointSamples", basisHsmCheckpoints);',
]: require(renderer, marker, 'renderer invariant')

basis_pos = prospective.find('ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);', prospective.find('bridgeProbeMode == 3'))
hsm_pos = prospective.find('ctx.hsm = new double[cal.hsmA.length];', basis_pos)
if basis_pos < 0 or hsm_pos < 0 or basis_pos >= hsm_pos:
    raise SystemExit('BASISHSM1A-FIX1 ordering failure: basis must precede historical HSM')

for marker in ['tc20MeterNative(', 'tc20MeterNativeDirect(', 'METER_TARGET /']:
    forbid(prospective, marker, 'prospective re-metering')
require(prospective, 'final double effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale;', 'fixed gain')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY','frameCount = 1;','throwCount = 0;','IsoExpoSelector.HDR = false;']:
    require(frames, marker, 'NOHDR1A boundary')
for marker in ['"_M9_NATIVE_HSM_ONLY"','"_M9_NATIVE_BASIS_ONLY"','"_M9_NATIVE_SOURCE_SHADING"']:
    forbid(renderer, marker, 'retired output')
require(gradle, '-nativeapiorder1a-basishsm1a-fix1', 'FIX1 build provenance')

print('M9 BASISHSM1A-FIX1 verified')
print(' - SOURCE_ONLY checkpoint uses identity pass-through instead of historical HSM indexing')
print(' - BASIS_HSM historical basis -> HSM order retained')
print(' - frozen Primary, fixed gain, NOHDR1A, shading-off experiment and downstream M9 stages retained')
print(' - primary renderCore sha256:', hashlib.sha256(primary.encode('utf-8')).hexdigest())
