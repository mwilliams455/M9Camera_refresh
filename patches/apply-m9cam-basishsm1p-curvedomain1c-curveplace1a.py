#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'CURVEPLACE1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)

# Native: add diagnostic mode 11. It leaves SAT3 and all upstream stages frozen,
# computes full-range BT.601 Y/Cb/Cr from the post-SAT 11-bit coordinates,
# applies firmware curve02 only to Y, carries Cb/Cr unchanged in normalized range,
# reconstructs RGB8, then returns to the existing exact BT.601 4:2:2 + TG1 path.
# This is a structural discriminator only, not a claim of final Leica stage order.
t = CPP.read_text()

t = replace_once(t,
'''    const int rr = ctx.curve[i0];
    const int gg = ctx.curve[i1];
    const int bb = ctx.curve[i2];
    rgbOut[0] = rr;
    rgbOut[1] = gg;
    rgbOut[2] = bb;
    int edge = 0;
    if (rr == 0 || rr == 255) edge++;
    if (gg == 0 || gg == 255) edge++;
    if (bb == 0 || bb == 255) edge++;
''',
'''    int rr, gg, bb;
    if (ctx.skyChromaMode1A == 11) {
        // CURVEPLACE1A structural discriminator only. The existing production path applies
        // curve02 independently to R/G/B. This alternate keeps the same SAT3 output,
        // derives exact full-range BT.601 Y/Cb/Cr in the 11-bit curve coordinate domain,
        // applies curve02 to Y only, carries Cb/Cr without a fitted gain, and reconstructs
        // RGB8 before the already-frozen exact BT.601 4:2:2 + TG1 output path.
        const int64_t y11 = clipl((4899LL * i0 + 9617LL * i1 + 1868LL * i2) >> 14, 0, LUT_MAX);
        const int64_t cb11 = (-2765LL * i0 - 5427LL * i1 + 8192LL * i2) >> 14;
        const int64_t cr11 = (8192LL * i0 - 6860LL * i1 - 1332LL * i2) >> 14;
        const double yy = static_cast<double>(ctx.curve[static_cast<size_t>(y11)]);
        const double scale11to8 = 255.0 / static_cast<double>(LUT_MAX);
        const double cb8 = static_cast<double>(cb11) * scale11to8;
        const double cr8 = static_cast<double>(cr11) * scale11to8;
        const auto clipRoundU8 = [](double v) -> int {
            if (v <= 0.0) return 0;
            if (v >= 255.0) return 255;
            return static_cast<int>(v + 0.5);
        };
        rr = clipRoundU8(yy + 1.402 * cr8);
        gg = clipRoundU8(yy - .344136 * cb8 - .714136 * cr8);
        bb = clipRoundU8(yy + 1.772 * cb8);
    } else {
        rr = ctx.curve[i0];
        gg = ctx.curve[i1];
        bb = ctx.curve[i2];
    }
    rgbOut[0] = rr;
    rgbOut[1] = gg;
    rgbOut[2] = bb;
    int edge = 0;
    if (rr == 0 || rr == 255) edge++;
    if (gg == 0 || gg == 255) edge++;
    if (bb == 0 || bb == 255) edge++;
''', 'native curve placement branch')

t = replace_once(t,
'''            // SKYDOWN1A-FIX1 + SKYSAT1A: modes 5..10 are diagnostic-only; production remains mode 0.
            || skyChromaMode1A < 0 || skyChromaMode1A > 10''',
'''            // SKYDOWN1A-FIX1 + SKYSAT1A + CURVEPLACE1A: modes 5..11 are diagnostic-only; production remains mode 0.
            || skyChromaMode1A < 0 || skyChromaMode1A > 11''', 'native mode range')

CPP.write_text(t)

j = JAVA.read_text()

j = replace_once(j,
'''                        String[] suffixes = {
                                "_SKYSAT_CONTROL_SAT3",
                                "_SKYSAT_SAT2_STANDARD",
                                "_SKYSAT_SAT4_HIGH",
                                "_SKYSAT_SAT3_BYPASS"
                        };
                        String[] bridgeProbeNames = {
                                "skysat_control_sat3",
                                "skysat_sat2_standard_gainlocked",
                                "skysat_sat4_high_gainlocked",
                                "skysat_sat3_bypass_gainlocked"
                        };
                        int[] bridgeProbeModes = {50, 51, 52, 53};
                        boolean[] selfMeterFlags = {true, false, false, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30};''',
'''                        String[] suffixes = {
                                "_SKYSAT_CONTROL_SAT3",
                                "_SKYSAT_SAT2_STANDARD",
                                "_SKYSAT_SAT4_HIGH",
                                "_SKYSAT_SAT3_BYPASS",
                                "_CURVEPLACE_SAT3_CURVE02_Y"
                        };
                        String[] bridgeProbeNames = {
                                "skysat_control_sat3",
                                "skysat_sat2_standard_gainlocked",
                                "skysat_sat4_high_gainlocked",
                                "skysat_sat3_bypass_gainlocked",
                                "curveplace_sat3_curve02_y_fixed_bt601_chroma_gainlocked"
                        };
                        int[] bridgeProbeModes = {50, 51, 52, 53, 54};
                        boolean[] selfMeterFlags = {true, false, false, false, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30, 0.30};''', 'variant bank')

j = replace_once(j,
'''            final boolean skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 53;
            final boolean skyDiagnosticEncodedAny1A =
                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A || skySatDiagnosticEncoded1A;''',
'''            final boolean skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 53;
            final boolean curvePlaceDiagnosticEncoded1A = bridgeProbeMode == 54;
            final boolean skyDiagnosticEncodedAny1A =
                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A
                            || skySatDiagnosticEncoded1A || curvePlaceDiagnosticEncoded1A;''', 'diagnostic encoding flags')

j = replace_once(j,
'''                            : (skySatDiagnosticEncoded1A
                                    ? (bridgeProbeMode == 50 ? 0
                                            : bridgeProbeMode == 51 ? 9
                                            : bridgeProbeMode == 52 ? 10 : 7)
                                    : 0));''',
'''                            : (skySatDiagnosticEncoded1A
                                    ? (bridgeProbeMode == 50 ? 0
                                            : bridgeProbeMode == 51 ? 9
                                            : bridgeProbeMode == 52 ? 10 : 7)
                                    : (curvePlaceDiagnosticEncoded1A ? 11 : 0)));''', 'mode mapping')

j = replace_once(j,
'''            case 10: return "SAT4_HIGH_M08_M09";
            default: return "CONTROL_PRODUCTION_CLIP";''',
'''            case 10: return "SAT4_HIGH_M08_M09";
            case 11: return "CURVEPLACE_SAT3_CURVE02_Y_FIXED_BT601_CHROMA";
            default: return "CONTROL_PRODUCTION_CLIP";''', 'mode name')

j = replace_once(j,
'''            d.put("skySat1A", skySatDiagnosticEncoded1A);
            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);''',
'''            d.put("skySat1A", skySatDiagnosticEncoded1A);
            d.put("curvePlace1A", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AStructuralDiscriminatorOnly", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AFirmwareStageOrderClaim", false);
            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);''', 'diagnostic metadata')

j = replace_once(j,
'''                        nativeAb1A.put("tc20GainIsolation",
                                "B_C_D_locked_to_A_exact_effective_render_gain");''',
'''                        nativeAb1A.put("tc20GainIsolation",
                                "B_C_D_E_locked_to_A_exact_effective_render_gain");
                        nativeAb1A.put("curvePlace1A", true);
                        nativeAb1A.put("curvePlace1AVariant",
                                "SAT3 -> exact BT601 YCbCr (11-bit) -> curve02 on Y only -> fixed chroma -> RGB8 -> frozen BT601_422/TG1");
                        nativeAb1A.put("curvePlace1AFirmwareStageOrderClaim", false);''', 'experiment metadata')

JAVA.write_text(j)

g = GRADLE.read_text()
g = replace_once(g,
                 '-curvedomain1b-neutralaxis1a-nativewpclip1a',
                 '-curvedomain1b-neutralaxis1a-curveplace1a-nativewpclip1a',
                 'version name')
GRADLE.write_text(g)

print('CURVEPLACE1A diagnostic applied')
print(' - primary/production mode 0 unchanged')
print(' - existing SKYSAT SAT2/SAT3/SAT4/bypass variants unchanged')
print(' - added gain-locked SAT3 curve02-on-BT601-Y structural variant (mode 11)')
print(' - no scene detector, tint correction, saturation weakening, exposure or TC20 change')
