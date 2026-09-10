#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'CURVEPLACE1B-DUALAXIS1A verify missing {label}: {needle}')

def require_count(text, needle, expected, label):
    got = text.count(needle)
    if got != expected:
        raise SystemExit(f'CURVEPLACE1B-DUALAXIS1A verify {label}: expected {expected}, got {got}')

cpp = CPP.read_text()
java = JAVA.read_text()
gradle = GRADLE.read_text()

# Parent CURVEPLACE1A structural discriminator remains intact.
require(cpp, 'if (ctx.skyChromaMode1A == 11)', 'native mode11 branch')
require_count(cpp, 'if (ctx.skyChromaMode1A == 11)', 1, 'single native mode11 branch')
require(cpp, 'ctx.curve[static_cast<size_t>(y11)]', 'production diagnostic Y-curve lookup')
require(cpp, 'rr = ctx.curve[i0];\n        gg = ctx.curve[i1];\n        bb = ctx.curve[i2];', 'frozen RGB production control')
require(cpp, 'const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;', 'frozen downstream BT601')
require(cpp, 'cb * tgCbGain', 'frozen TG1 Cb')
require(cpp, 'cr * tgCrGain', 'frozen TG1 Cr')
require(java, '"_CURVEPLACE_SAT3_CURVE02_Y"', 'existing fifth JPEG')
require(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54};', 'existing diagnostic bank')
require(java, 'curvePlaceDiagnosticEncoded1A ? 11 : 0', 'existing mode54-to-native11 mapping')
require(java, '"B_C_D_E_locked_to_A_exact_effective_render_gain"', 'gain lock')

# New telemetry-only dual-axis mirror.
require(cpp, 'inline bool satCurvePlaceYRgb8(', 'read-only Y-path helper')
require(cpp, '4899LL * rgb11[0] + 9617LL * rgb11[1] + 1868LL * rgb11[2]', 'audit exact BT601 Y')
require(cpp, '-2765LL * rgb11[0] - 5427LL * rgb11[1] + 8192LL * rgb11[2]', 'audit exact BT601 Cb')
require(cpp, '8192LL * rgb11[0] - 6860LL * rgb11[1] - 1332LL * rgb11[2]', 'audit exact BT601 Cr')
require(cpp, '255.0 / static_cast<double>(LUT_MAX)', 'audit chroma coordinate scale')
require(cpp, 'const bool curveYClipAny = satCurvePlaceYRgb8(curve, clamped, curveYRgb);', 'audit helper call')
require(cpp, 'neutralBandCurveYGreenDeficit[3]', 'Y-path green deficit aggregate')
require(cpp, 'neutralBandCurveYSpread[3]', 'Y-path spread aggregate')
require(cpp, 'neutralBandCurveYMagentaSide1pct[3]', 'Y-path magenta aggregate')
require(cpp, 'neutralBandCrossToMagentaAtCurveY1pct[3]', 'Y-path crossing aggregate')
require(cpp, 'neutralBandCurveYClipAny[3]', 'Y-path clip aggregate')
require(cpp, 'm9cam.curveplace1b.dualaxis1a.v1', 'dual-axis schema')
require(cpp, 'meanGreenDeficitNormalizedPostCurveY', 'Y-path green deficit JSON')
require(cpp, 'curveYMinusRgbMeanGreenDeficit', 'direct Y-minus-RGB delta JSON')
require(cpp, 'meanRelativeSpreadPostCurveY', 'Y-path spread JSON')
require(cpp, 'magentaSide1pctFractionPostCurveY', 'Y-path magenta fraction JSON')
require(cpp, 'crossToMagentaAtCurveY1pctFraction', 'Y-path crossing JSON')
require(cpp, 'curveYClipAnyFraction', 'Y-path clip fraction JSON')
require(cpp, 'dualAxisAuditReadOnly', 'read-only declaration')
require(cpp, 'curvePlace1AFirmwareStageOrderClaim', 'no Leica stage-order claim')
require(gradle, '-curvedomain1b-neutralaxis1a-curveplace1b-dualaxis1a-nativewpclip1a', 'version marker')

# Guard against accidentally adding a new render mode or changing the five-JPEG bank.
require_count(java, '"_CURVEPLACE_SAT3_CURVE02_Y"', 1, 'single CURVEPLACE diagnostic suffix')
require_count(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54};', 1, 'unchanged five diagnostic modes')

print('CURVEPLACE1B-DUALAXIS1A invariants OK')
print(' - CURVEPLACE1A fifth JPEG and mode 11 remain unchanged')
print(' - same neutral samples now report RGB-curve and Y-curve outcomes side-by-side')
print(' - exact Y/Cb/Cr arithmetic is mirrored in read-only audit code')
print(' - no new render mode, no production pixel path change, no gain/exposure/HSM/SAT change')
