#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
C = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
T = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
H = ROOT / 'app/src/main/cpp/m9_sharp_fulliso_bank.h'
for p in (CPP, R, C, T, H):
    if not p.exists():
        raise SystemExit('FULLISO1A verify missing ' + str(p))

cpp = CPP.read_text()
r = R.read_text()
c = C.read_text()
t = T.read_text()
h = H.read_text()

ACTIVE_METHOD = '    private static RenderCore renderNativeProspectiveCore('

def method_text(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('FULLISO1A verify active native method missing')
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('FULLISO1A verify active native opening brace missing')
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    esc = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
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
            elif ch in ('"', "'"): state = 'string'; quote = ch; esc = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    raise SystemExit('FULLISO1A verify active native method unterminated')

active = method_text(r, ACTIVE_METHOD)

checks = {
    'bank_13x2050': 'M9_SHARP_BASE[13][2050]' in h,
    'standard_modes': 'M9_SHARP_STANDARD_MODE[13]={4,4,4,4,4,4,3,3,3,3,3,2,2}' in h,
    'canonical_fw': '4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20' in h,
    'dynamic_slot_cpp': 'm9ClosureSharpStandardFullIso(sharpSourceGreen14, closureSharp14, width, height, sharpIsoSlot)' in cpp,
    'mode2_arshift': 'm9SharpArShift1' in cpp,
    'mode2_negative_odd_floor': '-(((-v) + 1) >> 1)' in cpp,
    'no_fixed_slot0_call': 'm9ClosureSharpIso160Standard(sharpSourceGreen14' not in cpp,
    'java_isos': '{160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500}' in r,
    'active_capture_result_iso': 'nativeCaptureResult.get(CaptureResult.SENSOR_SENSITIVITY)' in active,
    'active_main_x2_bridge': 'sharpSensorIso * 2' in active,
    'active_log2_slot': 'm9SharpIsoSlot(sharpNormalizedCaptureIso)' in active,
    'active_native_slot': '!demosaicPlainMhc1A,sharpIsoSlot,mhcStats' in active,
    'active_telemetry_slot': 'd.put("sharpnessIsoSlot", sharpIsoSlot);' in active,
    'active_telemetry_mode': 'd.put("sharpnessInternalMode", sharpIsoSlot <= 5 ? 4 : (sharpIsoSlot <= 10 ? 3 : 2));' in active,
    'active_telemetry_scale': 'd.put("sharpnessEffectiveScale", sharpIsoSlot <= 5 ? "2x" : (sharpIsoSlot <= 10 ? "1x" : "0.5x"));' in active,
    'active_telemetry_lut': 'd.put("sharpnessBaseLutRow", sharpIsoSlot);' in active,
    'active_telemetry_rbanchor': 'RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_RminusG_BminusG_proxy' in active,
    'no_threadlocal_bridge': 'M9_SHARP_NORMALIZED_ISO_TL' not in r,
    'native_slot_arg': 'int sharpIsoSlot' in c,
    'identity': 'STANDARD_FULLISO1A_RBANCHOR1A' in t,
    'rbanchor_preserved': 'const int sg=static_cast<int>(closureSharp14[p]);' in cpp and 'const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;' in cpp,
    'margin9': 'if(x>=9 && x<width-9 && y>=9 && y<height-9)' in cpp,
}

bad = [k for k, v in checks.items() if not v]
if bad:
    raise SystemExit('FULLISO1A verify FAIL ' + ','.join(bad))

print('STANDARD_FULLISO1A verify PASS')
print(' active renderer=renderNativeProspectiveCore')
print(' ISO source=physical CaptureResult.SENSOR_SENSITIVITY')
print(' ISO labels=160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500')
print(' Standard modes=4,4,4,4,4,4,3,3,3,3,3,2,2')
print(' bridge=Xiaomi main physical ISO x2 -> nearest Leica ISO in log2 space')
print(' bridge transport=direct active-renderer CaptureResult; no ThreadLocal')
print(' rbPolicy=RBANCHOR1A unchanged; nNoise=2 supportMargin=9')
