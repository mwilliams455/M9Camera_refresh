#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
C = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
T = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
for p in (R, C, CPP, T):
    if not p.exists():
        raise SystemExit('FULLISO1A missing ' + str(p))

ACTIVE_METHOD = '    private static RenderCore renderNativeProspectiveCore('

def rep(s, a, b, n):
    c = s.count(a)
    if c != 1:
        raise SystemExit(f'FULLISO1A {n} anchor count={c}')
    return s.replace(a, b, 1)

def method_bounds(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('FULLISO1A active native method missing')
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('FULLISO1A active native opening brace missing')
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
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('FULLISO1A active native method unterminated')

def rep_active(s, a, b, n):
    start, end = method_bounds(s, ACTIVE_METHOD)
    method = s[start:end]
    c = method.count(a)
    if c != 1:
        raise SystemExit(f'FULLISO1A {n} active anchor count={c}; global={s.count(a)}')
    pos = start + method.find(a)
    return s[:pos] + b + s[pos + len(a):]

r = R.read_text()
c = C.read_text()
cpp = CPP.read_text()
t = T.read_text()

# Canonical Leica physical ISO labels for the 13 recovered Sharp rows.
# Pull ISO 80 shares slot 0 in Leica behavior but remains reserved for a future
# explicit user ISO choice. The Xiaomi-main bridge itself is mobile-specific.
class_anchor = '''    private static final class RenderCore {\n        final Bitmap bitmap;'''
helper = '''    private static final int[] M9_SHARP_ISOS = {160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500};\n    private static int m9SharpIsoSlot(int normalizedIso) {\n        int clamped = Math.max(160, Math.min(2500, normalizedIso));\n        int best = 0;\n        double bestD = Double.POSITIVE_INFINITY;\n        for (int i = 0; i < M9_SHARP_ISOS.length; i++) {\n            double d = Math.abs(Math.log(clamped / (double) M9_SHARP_ISOS[i]) / Math.log(2.0));\n            if (d < bestD) { bestD = d; best = i; }\n        }\n        return best;\n    }\n\n''' + class_anchor
r = rep(r, class_anchor, helper, 'slot helper')

# Bind the selector to the active native production renderer itself. This renderer
# already receives the physical CaptureResult, so no orchestration anchor or
# ThreadLocal handoff is required. Missing ISO falls back to Leica slot0 while
# remaining explicit in telemetry as sensorIso=-1.
start, end = method_bounds(r, ACTIVE_METHOD)
brace = r.find('{', start)
selector = '''\n        // STANDARD_FULLISO1A Xiaomi-main bridge: physical CaptureResult ISO uses the\n        // established main-module x2 normalization, then nearest Leica ISO in log2(EV).\n        // This bridge is mobile-specific and is not claimed as Leica firmware behavior.\n        final Integer sharpSensorIsoObj = nativeCaptureResult == null ? null\n                : nativeCaptureResult.get(CaptureResult.SENSOR_SENSITIVITY);\n        final int sharpSensorIso = sharpSensorIsoObj == null ? -1 : sharpSensorIsoObj;\n        final int sharpNormalizedCaptureIso = sharpSensorIso > 0\n                ? Math.max(1, sharpSensorIso * 2) : 160;\n        final int sharpIsoSlot = m9SharpIsoSlot(sharpNormalizedCaptureIso);\n        final int sharpLeicaIso = M9_SHARP_ISOS[sharpIsoSlot];\n'''
r = r[:brace + 1] + selector + r[brace + 1:]

# Native declaration and active MHC call gain one integer ISO-slot argument.
c = rep(c,
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       long[] stats);''',
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       int sharpIsoSlot,\n                                       long[] stats);''', 'java native signature')
r = rep_active(r,
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);''',
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,sharpIsoSlot,mhcStats);''',
'active native call')

# Field telemetry proves the exact slot/mode and keeps the RBANCHOR1A seam explicit.
r = rep_active(r, '            d.put("demosaicElapsedMs", demosaicElapsedMs);',
'''            d.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");\n            d.put("sharpnessMenu", "Standard");\n            d.put("sharpnessSensorIso", sharpSensorIso);\n            d.put("sharpnessCaptureIsoSource", "CaptureResult.SENSOR_SENSITIVITY");\n            d.put("sharpnessNormalizedCaptureIso", sharpNormalizedCaptureIso);\n            d.put("sharpnessLeicaIso", sharpLeicaIso);\n            d.put("sharpnessIsoSlot", sharpIsoSlot);\n            d.put("sharpnessInternalMode", sharpIsoSlot <= 5 ? 4 : (sharpIsoSlot <= 10 ? 3 : 2));\n            d.put("sharpnessEffectiveScale", sharpIsoSlot <= 5 ? "2x" : (sharpIsoSlot <= 10 ? "1x" : "0.5x"));\n            d.put("sharpnessBaseLutRow", sharpIsoSlot);\n            d.put("sharpnessBaseLutBank", "Leica_M9_1.216_canonical_13x2050");\n            d.put("sharpnessNoiseMode", 2);\n            d.put("sharpnessSupportMargin", 9);\n            d.put("sharpnessSource", "LeicaGreenInterpolationWithCo-interior14bit");\n            d.put("sharpnessRgbReconstruction", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_RminusG_BminusG_proxy");\n            d.put("sharpnessIsoBridge", "xiaomi_main_CaptureResultISO_x2_then_nearest_log2_Leica160_2500");\n            d.put("demosaicElapsedMs", demosaicElapsedMs);''', 'active renderer telemetry')

# Generated canonical bank header is created by CI immediately before this patch.
cpp = rep(cpp, '#include <jni.h>', '#include <jni.h>\n#include "m9_sharp_fulliso_bank.h"', 'header include')
cpp = rep(cpp,
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jlongArray statsArray) {''',
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jint sharpIsoSlot,\n        jlongArray statsArray) {''', 'jni signature')
cpp = rep(cpp, '    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;',
'''    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;\n    if (sharpIsoSlot < 0 || sharpIsoSlot >= M9_SHARP_ISO_ROWS) return -8;''', 'slot validation')

# Exact recovered Standard working-coefficient transform:
# mode4 signed x2; mode3 unchanged; mode2 arithmetic >>>1; then clamp [-2048,+2048].
marker = 'inline uint16_t m9ClosureClamp14(int v){'
helper_cpp = r'''inline int m9SharpArShift1(int v){
    // Exact signed arithmetic >>>1 including negative odd values.
    return v >= 0 ? (v >> 1) : -(((-v) + 1) >> 1);
}
inline int m9SharpStandardCoeff(int slot,int idx){
    int v = static_cast<int>(M9_SHARP_BASE[slot][idx]);
    const int mode = M9_SHARP_STANDARD_MODE[slot];
    if (mode == 4) v *= 2;
    else if (mode == 3) {}
    else if (mode == 2) v = m9SharpArShift1(v);
    else return 0;
    if (v < -2048) v = -2048;
    else if (v > 2048) v = 2048;
    return v;
}
''' + marker
cpp = rep(cpp, marker, helper_cpp, 'working coeff helper')
cpp = rep(cpp,
'''inline void m9ClosureSharpIso160Standard(const std::vector<uint16_t>& src,\n                                         std::vector<uint16_t>& dst,int w,int h){''',
'''inline void m9ClosureSharpStandardFullIso(const std::vector<uint16_t>& src,\n                                         std::vector<uint16_t>& dst,int w,int h,int isoSlot){''', 'sharp function signature')
cpp = rep(cpp,
'''            // SHARPNESS_CLOSURETEST1B: Leica Standard slot0 selects internal mode 4.\n            // Firmware mode4 is signed coefficient x2 followed by [-2048,+2048] clamp.\n            // Use multiplication rather than left-shifting a negative signed value in C++.\n            const int baseCorr=m9ClosureSlot0Coeff(1024+r);\n            const int doubledCorr=baseCorr*2;\n            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);''',
'''            // STANDARD_FULLISO1A: canonical ISO-specific base row plus the proven\n            // Standard selector mode for that slot, then firmware [-2048,+2048] clamp.\n            const int corr=m9SharpStandardCoeff(isoSlot,1024+r);''', 'coeff use')
cpp = rep(cpp,
'm9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);',
'm9ClosureSharpStandardFullIso(sharpSourceGreen14, closureSharp14, width, height, sharpIsoSlot);',
'sharp call')
cpp = cpp.replace(
'SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences',
'SHARPNESS_STANDARD_FULLISO1A_ID: menu=Standard slot=dynamic modes=4/3/2 nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=RBANCHOR1A', 1)

# PRIMARY identity no longer claims a fixed slot0/mode4. The actual frame selection
# lives in the nested renderer diagnostics above.
t = t.replace('root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");',
              'root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");', 1)
t = t.replace('root.put("sharpnessSlot", 0);',
              'root.put("sharpnessSlot", -1); // dynamic; actual slot in nested renderer diagnostics', 1)
t = t.replace('root.put("sharpnessInternalMode", 4);',
              'root.put("sharpnessInternalMode", -1); // dynamic Standard 4/3/2 by slot', 1)
t = t.replace('root.put("sharpnessScale", "2x");',
              'root.put("sharpnessScale", "slot-dependent Standard mode4/mode3/mode2");', 1)

R.write_text(r)
C.write_text(c)
CPP.write_text(cpp)
T.write_text(t)
print('STANDARD_FULLISO1A applied: active native CaptureResult ISO -> Leica slot; canonical bank + Standard 4/3/2; RBANCHOR1A unchanged')
