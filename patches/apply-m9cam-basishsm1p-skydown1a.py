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
        raise SystemExit(f'SKYDOWN1A {label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

r=rp.read_text()
old='''                        // BASISHSM1P-SKYCHROMA1A: same-RAW isolation bank.\n                        // A meters exactly as 1P. B/C/D reuse A's exact effective render gain,\n                        // so HSM V authority cannot feed back through TC20 and masquerade as exposure.\n                        // SKYCHROMA1A: same RAW, same BASIS/HSM target role, fixed exposure/tone.\n                        // Encoded bridge modes 30..34 all decode back to production bridge mode 3;\n                        // the low digit selects only the diagnostic gamut/hue scenario.\n                        String[] suffixes = {\n                                "_SKYCHROMA_CONTROL_1P",\n                                "_SKYCHROMA_PREHSM_VECGAMUT",\n                                "_SKYCHROMA_HSM_HUE_OFF",\n                                "_SKYCHROMA_M9BRIDGE_VECGAMUT",\n                                "_SKYCHROMA_BOTH_VECGAMUT"\n                        };\n                        String[] bridgeProbeNames = {\n                                "skychroma_control_1p",\n                                "skychroma_prehsm_vecgamut_gainlocked",\n                                "skychroma_hsm_hue_off_gainlocked",\n                                "skychroma_m9bridge_vecgamut_gainlocked",\n                                "skychroma_both_vecgamut_gainlocked"\n                        };\n                        int[] bridgeProbeModes = {30, 31, 33, 32, 34};'''
new='''                        // BASISHSM1P-SKYDOWN1A: same-RAW downstream isolation bank.\n                        // A meters exactly as frozen 1P. B/C/D/E reuse A's exact effective render gain.\n                        // Encoded bridge modes 40..44 all decode back to production bridge mode 3;\n                        // only the downstream causal probe changes. No sky classifier or scene guard exists.\n                        String[] suffixes = {\n                                "_SKYDOWN_CONTROL_1P",\n                                "_SKYDOWN_POSTGAIN_VECGAMUT",\n                                "_SKYDOWN_SAT3_VECGAMUT",\n                                "_SKYDOWN_SAT3_BYPASS",\n                                "_SKYDOWN_BT601_BYPASS"\n                        };\n                        String[] bridgeProbeNames = {\n                                "skydown_control_1p",\n                                "skydown_postgain_vecgamut_gainlocked",\n                                "skydown_sat3_vecgamut_gainlocked",\n                                "skydown_sat3_bypass_gainlocked",\n                                "skydown_bt601_bypass_gainlocked"\n                        };\n                        int[] bridgeProbeModes = {40, 41, 42, 43, 44};'''
r=replace1(r,old,new,'bank')
r=r.replace('SKYCHROMA1A control gain unavailable before locked variant','SKYDOWN1A control gain unavailable before locked variant')
r=r.replace('SKYCHROMA1A invalid control effective render gain','SKYDOWN1A invalid control effective render gain')
r=r.replace('"BASISHSM1P-SKYCHROMA1A"','"BASISHSM1P-SKYDOWN1A"')
r=r.replace('"completed_skychroma1a"','"completed_skydown1a"')
r=r.replace('"m9cam.renderer.skychroma.v1a"','"m9cam.renderer.skydown.v1a"')

old='''            // SKYCHROMA1A diagnostic encoding. Production and all historical callers keep\n            // bridgeProbeMode 0..3 and therefore skyChromaMode1A=0 bit-for-bit.\n            final boolean skyChromaDiagnosticEncoded1A = bridgeProbeMode >= 30 && bridgeProbeMode <= 34;\n            final int skyChromaMode1A = skyChromaDiagnosticEncoded1A\n                    ? (bridgeProbeMode - 30) : 0;\n            if (skyChromaDiagnosticEncoded1A) bridgeProbeMode = 3;'''
new='''            // SKYCHROMA1A / SKYDOWN1A diagnostic encoding. Production and historical callers\n            // keep bridgeProbeMode 0..3 and therefore diagnostic mode 0 bit-for-bit.\n            final boolean skyChromaDiagnosticEncoded1A = bridgeProbeMode >= 30 && bridgeProbeMode <= 34;\n            final boolean skyDownDiagnosticEncoded1A = bridgeProbeMode >= 40 && bridgeProbeMode <= 44;\n            final boolean skyDiagnosticEncodedAny1A =\n                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A;\n            final int skyChromaMode1A = skyChromaDiagnosticEncoded1A\n                    ? (bridgeProbeMode - 30)\n                    : (skyDownDiagnosticEncoded1A\n                            ? (bridgeProbeMode == 40 ? 0 : bridgeProbeMode - 36)\n                            : 0);\n            if (skyDiagnosticEncodedAny1A) bridgeProbeMode = 3;'''
r=replace1(r,old,new,'decode')

old='''            case 4: return "BOTH_VECGAMUT";\n            default: return "CONTROL_PRODUCTION_CLIP";'''
new='''            case 4: return "BOTH_VECGAMUT";\n            case 5: return "POSTGAIN_VECGAMUT";\n            case 6: return "SAT3_VECGAMUT";\n            case 7: return "SAT3_BYPASS";\n            case 8: return "BT601_BYPASS";\n            default: return "CONTROL_PRODUCTION_CLIP";'''
r=replace1(r,old,new,'mode names')

old='''            d.put("skyChroma1A", skyChromaDiagnosticEncoded1A);\n            d.put("skyChromaMode1A", skyChromaMode1A);'''
new='''            d.put("skyChroma1A", skyChromaDiagnosticEncoded1A);\n            d.put("skyDown1A", skyDownDiagnosticEncoded1A);\n            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);\n            d.put("skyChromaMode1A", skyChromaMode1A);'''
r=replace1(r,old,new,'diag flags')
r=r.replace('skyChromaDiagnosticEncoded1A && skyChromaMode1A != 0','skyDiagnosticEncodedAny1A && skyChromaMode1A != 0')

# Keep the existing read-only signed audit and final pink proxy active; rename aggregate keys only.
r=r.replace('"skyChromaControlTc20BaselineGain"','"skyDownControlTc20BaselineGain"')
r=r.replace('"skyChromaControlEffectiveRenderGain"','"skyDownControlEffectiveRenderGain"')
r=r.replace('"skyChromaControlBitmapHash64"','"skyDownControlBitmapHash64"')
r=r.replace('"skyChromaExactBitmapParityWithControl"','"skyDownExactBitmapParityWithControl"')

rp.write_text(r)

c=cp.read_text()
old='''inline int m9CurvePixel(const double* m9, double gain, const ColorContext& ctx, int* rgbOut) {\n    const int64_t r = clipl(static_cast<int64_t>(std::rint(m9[0] * gain * RAW_MAX)), 0, RAW_MAX);\n    const int64_t g = clipl(static_cast<int64_t>(std::rint(m9[1] * gain * RAW_MAX)), 0, RAW_MAX);\n    const int64_t b = clipl(static_cast<int64_t>(std::rint(m9[2] * gain * RAW_MAX)), 0, RAW_MAX);\n    const bool evenBranch = r >= g;\n    const auto& q = evenBranch ? QE : QO;\n    const int64_t a0 = q[0] * r + q[1] * g + q[2] * b;\n    const int64_t a1 = q[3] * r + q[4] * g + q[5] * b;\n    const int64_t a2 = q[6] * r + q[7] * g + q[8] * b;\n    const int i0 = static_cast<int>(clipl(a0 >> 16, 0, LUT_MAX));\n    const int i1 = static_cast<int>(clipl(a1 >> 16, 0, LUT_MAX));\n    const int i2 = static_cast<int>(clipl(a2 >> 16, 0, LUT_MAX));\n    const int rr = ctx.curve[i0];\n    const int gg = ctx.curve[i1];\n    const int bb = ctx.curve[i2];'''
new='''inline int m9CurvePixel(const double* m9, double gain, const ColorContext& ctx, int* rgbOut) {\n    const double ur = m9[0] * gain * RAW_MAX;\n    const double ug = m9[1] * gain * RAW_MAX;\n    const double ub = m9[2] * gain * RAW_MAX;\n    int64_t r, g, b;\n    if (ctx.skyChromaMode1A == 5) {\n        // SKYDOWN1A causal probe only: common scale preserves post-TC20 channel ratios\n        // when any positive component exceeds the 14-bit container. No production promotion.\n        const double mx = std::max(ur, std::max(ug, ub));\n        const double sc = mx > RAW_MAX ? (RAW_MAX / mx) : 1.0;\n        r = clipl(static_cast<int64_t>(std::rint(ur * sc)), 0, RAW_MAX);\n        g = clipl(static_cast<int64_t>(std::rint(ug * sc)), 0, RAW_MAX);\n        b = clipl(static_cast<int64_t>(std::rint(ub * sc)), 0, RAW_MAX);\n    } else {\n        r = clipl(static_cast<int64_t>(std::rint(ur)), 0, RAW_MAX);\n        g = clipl(static_cast<int64_t>(std::rint(ug)), 0, RAW_MAX);\n        b = clipl(static_cast<int64_t>(std::rint(ub)), 0, RAW_MAX);\n    }\n    const bool evenBranch = r >= g;\n    const auto& q = evenBranch ? QE : QO;\n    const int64_t a0 = q[0] * r + q[1] * g + q[2] * b;\n    const int64_t a1 = q[3] * r + q[4] * g + q[5] * b;\n    const int64_t a2 = q[6] * r + q[7] * g + q[8] * b;\n    int i0, i1, i2;\n    if (ctx.skyChromaMode1A == 7) {\n        // Identity 14-bit -> 11-bit coordinate, bypassing M06/M07 only.\n        i0 = static_cast<int>(clipl(r >> 3, 0, LUT_MAX));\n        i1 = static_cast<int>(clipl(g >> 3, 0, LUT_MAX));\n        i2 = static_cast<int>(clipl(b >> 3, 0, LUT_MAX));\n    } else if (ctx.skyChromaMode1A == 6) {\n        // Causal probe: preserve SAT3 output vector direction instead of independent index clips.\n        double x0 = static_cast<double>(a0 >> 16);\n        double x1 = static_cast<double>(a1 >> 16);\n        double x2 = static_cast<double>(a2 >> 16);\n        const double mn = std::min(x0, std::min(x1, x2));\n        if (mn < 0.0) { x0 -= mn; x1 -= mn; x2 -= mn; }\n        const double mx = std::max(x0, std::max(x1, x2));\n        if (mx > LUT_MAX) { const double sc = LUT_MAX / mx; x0 *= sc; x1 *= sc; x2 *= sc; }\n        i0 = static_cast<int>(clipl(static_cast<int64_t>(std::rint(x0)), 0, LUT_MAX));\n        i1 = static_cast<int>(clipl(static_cast<int64_t>(std::rint(x1)), 0, LUT_MAX));\n        i2 = static_cast<int>(clipl(static_cast<int64_t>(std::rint(x2)), 0, LUT_MAX));\n    } else {\n        i0 = static_cast<int>(clipl(a0 >> 16, 0, LUT_MAX));\n        i1 = static_cast<int>(clipl(a1 >> 16, 0, LUT_MAX));\n        i2 = static_cast<int>(clipl(a2 >> 16, 0, LUT_MAX));\n    }\n    const int rr = ctx.curve[i0];\n    const int gg = ctx.curve[i1];\n    const int bb = ctx.curve[i2];'''
c=replace1(c,old,new,'native curve path')

old='''            const int64_t r0 = rgb0[0], g0 = rgb0[1], b0 = rgb0[2];\n            const int64_t r1 = rgb1[0], g1 = rgb1[1], b1 = rgb1[2];\n            const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;'''
new='''            const int64_t r0 = rgb0[0], g0 = rgb0[1], b0 = rgb0[2];\n            const int64_t r1 = rgb1[0], g1 = rgb1[1], b1 = rgb1[2];\n            if (ctx.skyChromaMode1A == 8) {\n                // SKYDOWN1A causal probe only: preserve curve02 RGB8 and skip exact 4:2:2\n                // encode/decode (TG1 is consequently bypassed too).\n                argb[p0] = packArgb(static_cast<int>(r0), static_cast<int>(g0), static_cast<int>(b0));\n                argb[p1] = packArgb(static_cast<int>(r1), static_cast<int>(g1), static_cast<int>(b1));\n                if (std::max(r0, std::max(g0, b0)) >= 250) nearWhite++;\n                if (std::max(r1, std::max(g1, b1)) >= 250) nearWhite++;\n                continue;\n            }\n            const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;'''
c=replace1(c,old,new,'bt601 bypass')
cp.write_text(c)

b=bp.read_text()
old='-basishsm1p-skychroma1a-nativewpclip1a'
new='-basishsm1p-skydown1a-nativewpclip1a'
b=replace1(b,old,new,'version')
bp.write_text(b)

print('M9Cam BASISHSM1P SKYDOWN1A downstream causal overlay applied')
print(' - production mode 0 unchanged')
print(' - mode 5 post-TC20 common-scale headroom probe')
print(' - mode 6 SAT3 common-vector gamut probe')
print(' - mode 7 SAT3 M06/M07 bypass, identity 14->11 coordinate')
print(' - mode 8 exact BT601/TG1 bypass after curve02')
