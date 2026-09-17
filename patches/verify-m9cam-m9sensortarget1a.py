#!/usr/bin/env python3
from pathlib import Path
import hashlib, re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9sensortarget1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
curve = root / 'app/src/main/assets/m9/m9_curve02_firmware.bin'
cobalt = root / 'app/src/main/assets/m9/m9_r35_calibration.bin'
loader = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9TargetFirmwareCalibration.java'
cpp = root / 'app/src/main/cpp/m9color_jni.cpp'
for p in (renderer, curve, cobalt, loader, cpp):
    if not p.exists(): raise SystemExit('M9SENSORTARGET1A missing expected retained file: ' + str(p))
s = renderer.read_text()


def method_span(text, signature):
    start = text.find(signature)
    if start < 0: raise SystemExit('missing method: ' + signature)
    brace = text.find('{', start); depth = 0; state = 'code'; quote = ''; esc = False
    i = brace
    while i < len(text):
        ch = text[i]; nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i+1]
        i += 1
    raise SystemExit('unterminated method: ' + signature)

# Source side must be the active physical Camera2/DNG sensor characterization.
source = method_span(s, 'private static NativeProspectiveSource buildNativeProspectiveSource(')
source_required = [
    'SENSOR_REFERENCE_ILLUMINANT1', 'SENSOR_REFERENCE_ILLUMINANT2',
    'SENSOR_CALIBRATION_TRANSFORM1', 'SENSOR_CALIBRATION_TRANSFORM2',
    'SENSOR_COLOR_TRANSFORM1', 'SENSOR_COLOR_TRANSFORM2',
    'SENSOR_FORWARD_MATRIX1', 'SENSOR_FORWARD_MATRIX2',
    'SENSOR_NEUTRAL_COLOR_POINT',
    'Converter.findDngInterpolationFactor(',
    'Converter.calculateCameraToXYZD50Transform(',
    'ctx.camToPp = cameraToProPhoto;',
    'ctx.hsm = new double[]{',
    'ctx.m9cm = interp9(M9_CM_A, M9_CM_D65, ctx.wA);',
    'ctx.ppToM9 = new double[9];',
]
for token in source_required:
    if token not in source:
        raise SystemExit('M9SENSORTARGET1A source/target math missing: ' + token)
for forbidden in ('TARGETINPUT15_', 'C15_historical', 'targetInputAdapter', 'cal.hsmA', 'cal.hsmD65'):
    if forbidden in source:
        raise SystemExit('M9SENSORTARGET1A forbidden historical target dependency in source transform: ' + forbidden)

# Recovered Leica M9 sensor matrices currently frozen in the firmware target model.
for token in [
'''private static final double[] M9_CM_A = {
            .8560, -.2034, -.0066,
            -.4240, 1.3600, .2920,
            -.0740, .2470, .8980
    };''',
'''private static final double[] M9_CM_D65 = {
            .6260, -.1019, -.0470,
            -.3730, 1.1450, .1930,
            -.1409, .2950, .6210
    };''']:
    if token not in s:
        raise SystemExit('M9SENSORTARGET1A recovered M9 sensor matrix changed/missing')

core = method_span(s, 'private static RenderCore renderNativeProspectiveCore(')
core_required = [
    'final boolean historicalProbeCalibrationRequired = bridgeProbeMode != 0;',
    '? M9R35Calibration.get() : null;',
    '? cal.curve02 : M9TargetFirmwareCalibration.get().curve02;',
    'NativeProspectiveSource nativeSource = buildNativeProspectiveSource(',
    'm9SensorTarget1AAssertProductionContext(',
    'd.put("m9SensorTarget1ARuntimeVerified", true);',
    'd.put("m9SensorTarget1AHistoricalCobaltCalibrationLoaded", false);',
]
for token in core_required:
    if token not in core:
        raise SystemExit('M9SENSORTARGET1A core invariant missing: ' + token)

prod = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
if '                0,\n                true,\n                false, false,' not in prod:
    raise SystemExit('M9SENSORTARGET1A production is not frozen to direct bridge mode 0')
for token in [
    'm9SensorTarget1ARuntimeVerified',
    'm9SensorTarget1A',
    'm9SensorTarget1ACobaltAssetRetainedForControl',
    'm9SensorTarget1ACobaltAssetUsedByRender", false',
    'm9SensorTarget1ATargetInputAdapterUsed", false',
    'SAT2_M04_M05_native_mode9',
]:
    if token not in prod:
        raise SystemExit('M9SENSORTARGET1A production guard/telemetry missing: ' + token)

# HSM is topology-only identity; nonlinear target rendering is the recovered firmware SAT2 operation.
assert_method = method_span(s, 'private static void m9SensorTarget1AAssertProductionContext(')
for token in [
    'historical Cobalt calibration reached production context',
    'active physical sensor -> XYZ D50 transform',
    'HSM must be topology-only 2x2 identity',
    'common_scene_to_M9_virtual_sensor',
]:
    if token not in assert_method:
        raise SystemExit('M9SENSORTARGET1A runtime assertion missing: ' + token)

# Java and native renderer must agree on Leica Standard SAT2 / M04-M05.
if not re.search(r'\bSATURATION_BANK\s*=\s*2\s*;', s):
    raise SystemExit('M9SENSORTARGET1A SATURATION_BANK is not 2')
for token in [
    'SATURATION_BANK == 2 ? 9',
    'nativeSaturationMode1A == 9 ? "M04_M05"',
    '13659, -4457, -1004',
    '14811, -5604, -1004',
]:
    if token not in s:
        raise SystemExit('M9SENSORTARGET1A Java SAT2/native mode invariant missing: ' + token)
cpps = cpp.read_text()
for token in ['13659', '-4457', '14811', '-5604']:
    if token not in cpps:
        raise SystemExit('M9SENSORTARGET1A native SAT2 coefficient missing: ' + token)

# Cobalt control asset is intentionally retained for this validation branch; curve02 is the
# separate Leica-only production target asset. Nothing is deleted in this test.
if cobalt.stat().st_size < 60000:
    raise SystemExit('M9SENSORTARGET1A historical calibration control asset unexpectedly changed/removed')
if cobalt.read_bytes()[:8] != b'M9R35CAL':
    raise SystemExit('M9SENSORTARGET1A historical calibration control header changed')
curve_hash = hashlib.sha256(curve.read_bytes()).hexdigest()
expected_curve_hash = '5b303ff7d9d47ecb8e193a648ddf0570fef46ad29a62d112993d37d52f8c135c'
if curve_hash != expected_curve_hash:
    raise SystemExit('M9SENSORTARGET1A Leica firmware curve02 hash changed: ' + curve_hash)
if 'm9/m9_curve02_firmware.bin' not in loader.read_text():
    raise SystemExit('M9SENSORTARGET1A target loader does not use Leica-only curve02 asset')

print('M9SENSORTARGET1A VERIFY PASS')
print('source_authority=active physical Camera2/DNG dual-illuminant sensor calibration')
print('common_scene=XYZ D50')
print('target_authority=recovered Leica M9 A/D65 sensor calibration + firmware SAT2/curve02')
print('hsm=identity')
print('native_saturation=SAT2 M04/M05 mode9')
print('historical_cobalt_asset=RETAINED_CONTROL_NOT_PRODUCTION_RENDER_DEPENDENCY')
print('curve02_sha256=' + curve_hash)