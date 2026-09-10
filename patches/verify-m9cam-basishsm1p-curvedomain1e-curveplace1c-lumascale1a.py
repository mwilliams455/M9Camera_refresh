#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'CURVEPLACE1C-LUMASCALE1A verify missing {label}: {needle}')

def require_count(text, needle, expected, label):
    got = text.count(needle)
    if got != expected:
        raise SystemExit(f'CURVEPLACE1C-LUMASCALE1A verify {label}: expected {expected}, got {got}')

cpp = CPP.read_text()
java = JAVA.read_text()
gradle = GRADLE.read_text()

# Frozen production and prior discriminator must remain present.
require(cpp, 'if (ctx.skyChromaMode1A == 11)', 'existing CURVEPLACE1A mode11')
require_count(cpp, 'if (ctx.skyChromaMode1A == 11)', 1, 'single mode11 branch')
require(cpp, 'rr = ctx.curve[i0];\n        gg = ctx.curve[i1];\n        bb = ctx.curve[i2];', 'frozen production RGB curve')
require(cpp, 'const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;', 'frozen downstream BT601')
require(cpp, 'cb * tgCbGain', 'frozen TG1 Cb')
require(cpp, 'cr * tgCrGain', 'frozen TG1 Cr')
require(java, '"_CURVEPLACE_SAT3_CURVE02_Y"', 'existing fixed-chroma JPEG')

# New rendered LUMASCALE diagnostic.
require(cpp, 'else if (ctx.skyChromaMode1A == 12)', 'native mode12 branch')
require_count(cpp, 'ctx.skyChromaMode1A == 12', 1, 'single native mode12 branch')
require(cpp, 'const double lumaScale = yCurve8 / static_cast<double>(y11);', 'common luma scale')
require(cpp, 'rr = clipRoundU8(static_cast<double>(i0) * lumaScale);', 'R common scale')
require(cpp, 'gg = clipRoundU8(static_cast<double>(i1) * lumaScale);', 'G common scale')
require(cpp, 'bb = clipRoundU8(static_cast<double>(i2) * lumaScale);', 'B common scale')
require(cpp, 'skyChromaMode1A > 12', 'native mode range')
require(java, '"_CURVEPLACE_SAT3_CURVE02_LUMASCALE"', 'sixth JPEG suffix')
require(java, '"curveplace_sat3_curve02_lumascale_gainlocked"', 'sixth probe name')
require(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54, 55};', 'six diagnostic modes')
require(java, 'curvePlaceLumaScaleDiagnostic1A = bridgeProbeMode == 55', 'mode55 encoding')
require(java, 'curvePlaceLumaScaleDiagnostic1A ? 12 : 0', 'mode55-to-native12 mapping')
require(java, 'case 12: return "CURVEPLACE_SAT3_CURVE02_LUMASCALE";', 'mode12 name')
require(java, '"B_C_D_E_F_locked_to_A_exact_effective_render_gain"', 'six-way gain lock')
require(java, 'curvePlaceLumaScaleChromaticityPreservingBeforeClip', 'candidate semantics metadata')
require(java, 'curvePlaceLumaScaleFirmwareStageOrderClaim', 'no firmware stage-order claim')

# Triple-path telemetry on identical neutral samples.
require(cpp, 'inline bool satCurvePlaceLumaScaleRgb8(', 'read-only LUMASCALE helper')
require(cpp, 'neutralBandCurveLumaScaleGreenDeficit[3]', 'LUMASCALE green deficit aggregate')
require(cpp, 'neutralBandCurveLumaScaleSpread[3]', 'LUMASCALE spread aggregate')
require(cpp, 'neutralBandCurveLumaScaleMagentaSide1pct[3]', 'LUMASCALE magenta aggregate')
require(cpp, 'neutralBandCrossToMagentaAtCurveLumaScale1pct[3]', 'LUMASCALE crossing aggregate')
require(cpp, 'neutralBandCurveLumaScaleClipAny[3]', 'LUMASCALE clip aggregate')
require(cpp, 'm9cam.curveplace1c.lumascale1a.v1', 'LUMASCALE schema')
require(cpp, 'meanGreenDeficitNormalizedPostCurveLumaScale', 'LUMASCALE green deficit JSON')
require(cpp, 'curveLumaScaleMinusRgbMeanGreenDeficit', 'LUMASCALE delta JSON')
require(cpp, 'meanRelativeSpreadPostCurveLumaScale', 'LUMASCALE spread JSON')
require(cpp, 'magentaSide1pctFractionPostCurveLumaScale', 'LUMASCALE magenta JSON')
require(cpp, 'curveLumaScaleClipAnyFraction', 'LUMASCALE clip JSON')
require(cpp, 'crossToMagentaAtCurveLumaScale1pctFraction', 'LUMASCALE crossing JSON')
require(cpp, 'triplePathAuditReadOnly', 'read-only triple-path declaration')
require(cpp, 'lumaScaleFirmwareStageOrderClaim', 'no LUMASCALE firmware stage-order claim')
require(gradle, '-curvedomain1b-neutralaxis1a-curveplace1c-lumascale1a-nativewpclip1a', 'version marker')

# Diagnostic-bank cardinality: one fixed-chroma Y and one LUMASCALE output only.
require_count(java, '"_CURVEPLACE_SAT3_CURVE02_Y"', 1, 'single fixed-chroma suffix')
require_count(java, '"_CURVEPLACE_SAT3_CURVE02_LUMASCALE"', 1, 'single LUMASCALE suffix')
require_count(java, 'int[] bridgeProbeModes = {50, 51, 52, 53, 54, 55};', 1, 'single six-mode bank')

print('CURVEPLACE1C-LUMASCALE1A invariants OK')
print(' - production RGB curve path remains unchanged')
print(' - CURVEPLACE1A fixed-chroma Y path remains available as mode 11')
print(' - mode 12 applies one curve02(Y)/Y scale identically to post-SAT RGB')
print(' - sixth JPEG is gain-locked to the SAT3 control')
print(' - neutral telemetry compares RGB, fixed-chroma Y, and LUMASCALE paths')
print(' - no exposure, TC20, HSM, SAT, shading, downstream BT601, or TG1 mutation')
