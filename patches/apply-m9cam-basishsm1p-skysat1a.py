#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
rp=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cp=root/'app/src/main/cpp/m9color_jni.cpp'
bp=root/'app/build.gradle'

def replace1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'SKYSAT1A {label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

r=rp.read_text()
old='''                        // BASISHSM1P-SKYDOWN1A: same-RAW downstream isolation bank.\n                        // A meters exactly as frozen 1P. B/C/D/E reuse A's exact effective render gain.\n                        // Encoded bridge modes 40..44 all decode back to production bridge mode 3;\n                        // only the downstream causal probe changes. No sky classifier or scene guard exists.\n                        String[] suffixes = {\n                                "_SKYDOWN_CONTROL_1P",\n                                "_SKYDOWN_POSTGAIN_VECGAMUT",\n                                "_SKYDOWN_SAT3_VECGAMUT",\n                                "_SKYDOWN_SAT3_BYPASS",\n                                "_SKYDOWN_BT601_BYPASS"\n                        };\n                        String[] bridgeProbeNames = {\n                                "skydown_control_1p",\n                                "skydown_postgain_vecgamut_gainlocked",\n                                "skydown_sat3_vecgamut_gainlocked",\n                                "skydown_sat3_bypass_gainlocked",\n                                "skydown_bt601_bypass_gainlocked"\n                        };\n                        int[] bridgeProbeModes = {40, 41, 42, 43, 44};\n                        boolean[] selfMeterFlags = {true, false, false, false, false};\n                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0, 1.0};\n                        boolean[] applyShadingFlags = {true, true, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0, 1.0};\n                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true, true};\n                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30, 0.30};'''
new='''                        // BASISHSM1P-SKYSAT1A: same-RAW authentic Leica saturation-family bank.\n                        // A meters exactly as frozen 1P/SAT3. B/C/D reuse A's exact effective render gain.\n                        // SAT2=04/05 is literal Leica Standard, SAT3=06/07 is current colourful production,\n                        // SAT4=08/09 is authentic High Saturation. D keeps the already-proven identity anchor.\n                        // No sky classifier, scene guard, exposure change, HSM change, or generic desaturation exists.\n                        String[] suffixes = {\n                                "_SKYSAT_CONTROL_SAT3",\n                                "_SKYSAT_SAT2_STANDARD",\n                                "_SKYSAT_SAT4_HIGH",\n                                "_SKYSAT_SAT3_BYPASS"\n                        };\n                        String[] bridgeProbeNames = {\n                                "skysat_control_sat3",\n                                "skysat_sat2_standard_gainlocked",\n                                "skysat_sat4_high_gainlocked",\n                                "skysat_sat3_bypass_gainlocked"\n                        };\n                        int[] bridgeProbeModes = {50, 51, 52, 53};\n                        boolean[] selfMeterFlags = {true, false, false, false};\n                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0};\n                        boolean[] applyShadingFlags = {true, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0};\n                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true};\n                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30};'''
r=replace1(r,old,new,'bank')
r=r.replace('SKYDOWN1A control gain unavailable before locked variant','SKYSAT1A control gain unavailable before locked variant')
r=r.replace('SKYDOWN1A invalid control effective render gain','SKYSAT1A invalid control effective render gain')
r=r.replace('"m9cam.renderer.skydown.v1a"','"m9cam.renderer.skysat.v1a"')
r=r.replace('"BASISHSM1P-SKYDOWN1A"','"BASISHSM1P-SKYSAT1A"')
r=r.replace('"completed_skydown1a"','"completed_skysat1a"')
r=r.replace('"B_C_D_E_locked_to_A_exact_effective_render_gain"','"B_C_D_locked_to_A_exact_effective_render_gain"')

old='''            // SKYCHROMA1A / SKYDOWN1A diagnostic encoding. Production and historical callers\n            // keep bridgeProbeMode 0..3 and therefore diagnostic mode 0 bit-for-bit.\n            final boolean skyChromaDiagnosticEncoded1A = bridgeProbeMode >= 30 && bridgeProbeMode <= 34;\n            final boolean skyDownDiagnosticEncoded1A = bridgeProbeMode >= 40 && bridgeProbeMode <= 44;\n            final boolean skyDiagnosticEncodedAny1A =\n                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A;\n            final int skyChromaMode1A = skyChromaDiagnosticEncoded1A\n                    ? (bridgeProbeMode - 30)\n                    : (skyDownDiagnosticEncoded1A\n                            ? (bridgeProbeMode == 40 ? 0 : bridgeProbeMode - 36)\n                            : 0);\n            if (skyDiagnosticEncodedAny1A) bridgeProbeMode = 3;'''
new='''            // SKYCHROMA1A / SKYDOWN1A / SKYSAT1A diagnostic encoding. Production and\n            // historical callers keep bridgeProbeMode 0..3 and therefore diagnostic mode 0 bit-for-bit.\n            final boolean skyChromaDiagnosticEncoded1A = bridgeProbeMode >= 30 && bridgeProbeMode <= 34;\n            final boolean skyDownDiagnosticEncoded1A = bridgeProbeMode >= 40 && bridgeProbeMode <= 44;\n            final boolean skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 53;\n            final boolean skyDiagnosticEncodedAny1A =\n                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A || skySatDiagnosticEncoded1A;\n            final int skyChromaMode1A = skyChromaDiagnosticEncoded1A\n                    ? (bridgeProbeMode - 30)\n                    : (skyDownDiagnosticEncoded1A\n                            ? (bridgeProbeMode == 40 ? 0 : bridgeProbeMode - 36)\n                            : (skySatDiagnosticEncoded1A\n                                    ? (bridgeProbeMode == 50 ? 0\n                                            : bridgeProbeMode == 51 ? 9\n                                            : bridgeProbeMode == 52 ? 10 : 7)\n                                    : 0));\n            if (skyDiagnosticEncodedAny1A) bridgeProbeMode = 3;'''
r=replace1(r,old,new,'decode')

old='''            case 8: return "BT601_BYPASS";\n            default: return "CONTROL_PRODUCTION_CLIP";'''
new='''            case 8: return "BT601_BYPASS";\n            case 9: return "SAT2_STANDARD_M04_M05";\n            case 10: return "SAT4_HIGH_M08_M09";\n            default: return "CONTROL_PRODUCTION_CLIP";'''
r=replace1(r,old,new,'mode names')

old='''            d.put("skyDown1A", skyDownDiagnosticEncoded1A);\n            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);'''
new='''            d.put("skyDown1A", skyDownDiagnosticEncoded1A);\n            d.put("skySat1A", skySatDiagnosticEncoded1A);\n            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);'''
r=replace1(r,old,new,'diag flag')
rp.write_text(r)

c=cp.read_text()
old='''constexpr std::array<int64_t, 9> QO = {\n        18160, -9034, -922,\n        -3422, 15080, -3458,\n        137, -10264, 18330\n};'''
new='''constexpr std::array<int64_t, 9> QO = {\n        18160, -9034, -922,\n        -3422, 15080, -3458,\n        137, -10264, 18330\n};\n\n// SKYSAT1A: exact recovered authentic Leica sRGB saturation-family neighbours.\n// SAT2 / 04-05 = Standard; SAT3 / 06-07 = current colourful production; SAT4 / 08-09 = High.\nconstexpr std::array<int64_t, 9> Q2E = {\n        13659, -4457, -1004,\n        -2244, 13469, -3033,\n        -199, -6014, 14398\n};\nconstexpr std::array<int64_t, 9> Q2O = {\n        14811, -5604, -1004,\n        -2455, 13688, -3033,\n        393, -6588, 14398\n};\nconstexpr std::array<int64_t, 9> Q4E = {\n        19850, -10808, -840,\n        -4004, 16080, -3884,\n        -936, -13144, 22262\n};\nconstexpr std::array<int64_t, 9> Q4O = {\n        21509, -12464, -840,\n        -4389, 16473, -3884,\n        -117, -13940, 22262\n};'''
c=replace1(c,old,new,'matrix constants')
old='''    const bool evenBranch = r >= g;\n    const auto& q = evenBranch ? QE : QO;\n    const int64_t a0 = q[0] * r + q[1] * g + q[2] * b;'''
new='''    const bool evenBranch = r >= g;\n    const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);\n    if (ctx.skyChromaMode1A == 9) qPtr = &(evenBranch ? Q2E : Q2O);\n    else if (ctx.skyChromaMode1A == 10) qPtr = &(evenBranch ? Q4E : Q4O);\n    const auto& q = *qPtr;\n    const int64_t a0 = q[0] * r + q[1] * g + q[2] * b;'''
c=replace1(c,old,new,'matrix selection')
c=c.replace('|| skyChromaMode1A < 0 || skyChromaMode1A > 8','|| skyChromaMode1A < 0 || skyChromaMode1A > 10')
c=c.replace('// SKYDOWN1A-FIX1: modes 5..8 are diagnostic-only downstream probes; production remains mode 0.','// SKYDOWN1A-FIX1 + SKYSAT1A: modes 5..10 are diagnostic-only; production remains mode 0.')
cp.write_text(c)

b=bp.read_text()
old='-basishsm1p-skydown1a-fix1-nativewpclip1a'
new='-basishsm1p-skysat1a-nativewpclip1a'
b=replace1(b,old,new,'version')
bp.write_text(b)

print('M9Cam BASISHSM1P SKYSAT1A authentic saturation-family diagnostic applied')
print(' - production mode 0 remains exact SAT3 M06/M07')
print(' - mode 9 = exact SAT2 Standard M04/M05')
print(' - mode 10 = exact SAT4 High M08/M09')
print(' - mode 7 = existing SAT3 bypass identity anchor')
