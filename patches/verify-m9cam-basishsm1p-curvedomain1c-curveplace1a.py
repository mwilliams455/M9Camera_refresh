#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'CURVEPLACE1A verify missing {label}: {needle}')

def require_count(text, needle, expected, label):
    got = text.count(needle)
    if got != expected:
        raise SystemExit(f'CURVEPLACE1A verify {label}: expected {expected}, got {got}')

cpp = CPP.read_text()
java = JAVA.read_text()
gradle = GRADLE.read_text()

require(cpp, 'if (ctx.skyChromaMode1A == 11)', 'native mode11 branch')
require(cpp, '4899LL * i0 + 9617LL * i1 + 1868LL * i2', 'exact BT601 Y coefficients')
require(cpp, '-2765LL * i0 - 5427LL * i1 + 8192LL * i2', 'exact BT601 Cb coefficients')
require(cpp, '8192LL * i0 - 6860LL * i1 - 1332LL * i2', 'exact BT601 Cr coefficients')
require(cpp, 'ctx.curve[static_cast<size_t>(y11)]', 'curve02 on Y')
require(cpp, '255.0 / static_cast<double>(LUT_MAX)', '11bit-to-8bit chroma scaling')
require(cpp, 'skyChromaMode1A > 11', 'diagnostic mode upper bound')
require_count(cpp, 'ctx.skyChromaMode1A == 11', 1, 'single native mode11 branch')
require(cpp, 'rr = ctx.curve[i0];\n        gg = ctx.curve[i1];\n        bb = ctx.curve[i2];', 'frozen per-channel control path')
require(cpp, 'const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;', 'frozen downstream BT601')
require(cpp, 'cb * tgCbGain', 'frozen TG1 Cb')
require(cpp, 'cr * tgCrGain', 'frozen TG1 Cr')

require(java, '"_CURVEPLACE_SAT3_CURVE02_Y"', 'diagnostic JPEG suffix')
require(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54};', 'five diagnostic modes')
require(java, 'final boolean curvePlaceDiagnosticEncoded1A = bridgeProbeMode == 54;', 'mode54 encoding')
require(java, 'curvePlaceDiagnosticEncoded1A ? 11 : 0', 'mode54-to-native11 mapping')
require(java, 'case 11: return "CURVEPLACE_SAT3_CURVE02_Y_FIXED_BT601_CHROMA";', 'mode name')
require(java, '"B_C_D_E_locked_to_A_exact_effective_render_gain"', 'gain lock invariant')
require(java, 'nativeAb1A.put("curvePlace1AFirmwareStageOrderClaim", false);', 'no stage-order claim')
require(java, 'boolean[] selfMeterFlags = {true, false, false, false, false};', 'meter isolation')
require(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54};', 'variant order')

require(gradle, '-curvedomain1b-neutralaxis1a-curveplace1a-nativewpclip1a', 'version marker')

print('CURVEPLACE1A invariants OK')
print(' - production mode 0 retains independent RGB curve02 control path')
print(' - mode 11 alone uses SAT3 -> BT601 YCbCr -> curve02(Y) -> fixed chroma -> RGB8')
print(' - downstream exact BT601 4:2:2 / TG1 anchors retained')
print(' - fifth JPEG is gain-locked to the existing SAT3 control')
