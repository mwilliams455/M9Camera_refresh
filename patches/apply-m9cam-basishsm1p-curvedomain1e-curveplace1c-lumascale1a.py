#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'CURVEPLACE1C-LUMASCALE1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)

# CURVEPLACE1C / LUMASCALE1A remains diagnostic-only. It adds a sixth
# gain-locked same-RAW render that evaluates curve02 from exact BT.601 Y,
# derives one common output-domain scale curve02(Y)/Y, and applies that same
# scale to post-SAT R/G/B. This preserves RGB chromaticity before clipping and
# avoids CURVEPLACE1A's fixed-Cb/Cr reconstruction. Production mode 0 and the
# existing CURVEPLACE1A mode 11 remain frozen.

t = CPP.read_text()

t = replace_once(t,
'''        bb = clipRoundU8(yy + 1.772 * cb8);
    } else {
        rr = ctx.curve[i0];
        gg = ctx.curve[i1];
        bb = ctx.curve[i2];
    }''',
'''        bb = clipRoundU8(yy + 1.772 * cb8);
    } else if (ctx.skyChromaMode1A == 12) {
        // CURVEPLACE1C / LUMASCALE1A structural candidate. Evaluate curve02 on
        // exact BT.601 Y in the same 11-bit coordinate domain, then apply one
        // common output-domain scale to all three post-SAT channels. No fitted
        // chroma term and no fixed-Cb/Cr reconstruction are used here.
        const int64_t y11 = clipl((4899LL * i0 + 9617LL * i1 + 1868LL * i2) >> 14, 0, LUT_MAX);
        const double yCurve8 = static_cast<double>(ctx.curve[static_cast<size_t>(y11)]);
        const auto clipRoundU8 = [](double v) -> int {
            if (v <= 0.0) return 0;
            if (v >= 255.0) return 255;
            return static_cast<int>(v + 0.5);
        };
        if (y11 <= 0) {
            const int black = static_cast<int>(ctx.curve[0]);
            rr = black;
            gg = black;
            bb = black;
        } else {
            const double lumaScale = yCurve8 / static_cast<double>(y11);
            rr = clipRoundU8(static_cast<double>(i0) * lumaScale);
            gg = clipRoundU8(static_cast<double>(i1) * lumaScale);
            bb = clipRoundU8(static_cast<double>(i2) * lumaScale);
        }
    } else {
        rr = ctx.curve[i0];
        gg = ctx.curve[i1];
        bb = ctx.curve[i2];
    }''', 'native LUMASCALE mode12 branch')

t = replace_once(t,
'''            // SKYDOWN1A-FIX1 + SKYSAT1A + CURVEPLACE1A: modes 5..11 are diagnostic-only; production remains mode 0.
            || skyChromaMode1A < 0 || skyChromaMode1A > 11''',
'''            // SKYDOWN1A-FIX1 + SKYSAT1A + CURVEPLACE1A + LUMASCALE1A: modes 5..12 are diagnostic-only; production remains mode 0.
            || skyChromaMode1A < 0 || skyChromaMode1A > 12''', 'native mode range')

# Extend the existing read-only neutral-axis audit with the common-scale path.
t = replace_once(t,
'''    uint64_t neutralBandCurveYMagentaSide1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurveY1pct[3]{};
    uint64_t neutralBandCurveYClipAny[3]{};
    uint64_t spatialCount[9]{};''',
'''    uint64_t neutralBandCurveYMagentaSide1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurveY1pct[3]{};
    uint64_t neutralBandCurveYClipAny[3]{};
    double neutralBandCurveLumaScaleGreenDeficit[3]{};
    double neutralBandCurveLumaScaleSpread[3]{};
    uint64_t neutralBandCurveLumaScaleMagentaSide1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurveLumaScale1pct[3]{};
    uint64_t neutralBandCurveLumaScaleClipAny[3]{};
    uint64_t spatialCount[9]{};''', 'LUMASCALE aggregate fields')

t = replace_once(t,
'''inline bool satCurvePlaceYRgb8(const std::array<uint8_t, 2048>& curve,
                               const int64_t rgb11[3],
                               double outRgb8[3]) {''',
'''inline bool satCurvePlaceLumaScaleRgb8(const std::array<uint8_t, 2048>& curve,
                                       const int64_t rgb11[3],
                                       double outRgb8[3]) {
    const int64_t y11 = clipl((4899LL * rgb11[0] + 9617LL * rgb11[1] + 1868LL * rgb11[2]) >> 14, 0, LUT_MAX);
    const double yCurve8 = static_cast<double>(curve[static_cast<size_t>(y11)]);
    if (y11 <= 0) {
        const double black = static_cast<double>(curve[0]);
        outRgb8[0] = black;
        outRgb8[1] = black;
        outRgb8[2] = black;
        return black <= 0.0 || black >= 255.0;
    }
    const double lumaScale = yCurve8 / static_cast<double>(y11);
    bool clipped = false;
    for (int c = 0; c < 3; ++c) {
        const double raw = static_cast<double>(rgb11[c]) * lumaScale;
        if (raw <= 0.0 || raw >= 255.0) clipped = true;
        outRgb8[c] = raw <= 0.0 ? 0.0 : (raw >= 255.0 ? 255.0 : static_cast<double>(static_cast<int>(raw + 0.5)));
    }
    return clipped;
}

inline bool satCurvePlaceYRgb8(const std::array<uint8_t, 2048>& curve,
                               const int64_t rgb11[3],
                               double outRgb8[3]) {''', 'LUMASCALE audit helper')

t = replace_once(t,
'''    const bool curveYClipAny = satCurvePlaceYRgb8(curve, clamped, curveYRgb);
    const double curveYSpread = satRelativeSpread(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    const double curveYGreenDeficit = satGreenDeficitNormalized(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    constexpr double neutralThresholds[3] = {0.05, 0.10, 0.20};''',
'''    const bool curveYClipAny = satCurvePlaceYRgb8(curve, clamped, curveYRgb);
    const double curveYSpread = satRelativeSpread(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    const double curveYGreenDeficit = satGreenDeficitNormalized(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    double curveLumaScaleRgb[3] = {0.0, 0.0, 0.0};
    const bool curveLumaScaleClipAny = satCurvePlaceLumaScaleRgb8(curve, clamped, curveLumaScaleRgb);
    const double curveLumaScaleSpread = satRelativeSpread(curveLumaScaleRgb[0], curveLumaScaleRgb[1], curveLumaScaleRgb[2]);
    const double curveLumaScaleGreenDeficit = satGreenDeficitNormalized(curveLumaScaleRgb[0], curveLumaScaleRgb[1], curveLumaScaleRgb[2]);
    constexpr double neutralThresholds[3] = {0.05, 0.10, 0.20};''', 'LUMASCALE per-pixel values')

t = replace_once(t,
'''        agg->neutralBandCurveYGreenDeficit[nb] += curveYGreenDeficit;
        agg->neutralBandPreSpread[nb] += preSpread;
        agg->neutralBandSatSpread[nb] += satSpread;
        agg->neutralBandCurveSpread[nb] += curveSpread;
        agg->neutralBandCurveYSpread[nb] += curveYSpread;
        const bool preMagentaSide = preGreenDeficit > magentaSideThreshold;
        const bool satMagentaSide = satGreenDeficit > magentaSideThreshold;
        const bool curveMagentaSide = curveGreenDeficit > magentaSideThreshold;
        const bool curveYMagentaSide = curveYGreenDeficit > magentaSideThreshold;
        if (preMagentaSide) ++agg->neutralBandPreMagentaSide1pct[nb];
        if (satMagentaSide) ++agg->neutralBandSatMagentaSide1pct[nb];
        if (curveMagentaSide) ++agg->neutralBandCurveMagentaSide1pct[nb];
        if (curveYMagentaSide) ++agg->neutralBandCurveYMagentaSide1pct[nb];
        if (curveYClipAny) ++agg->neutralBandCurveYClipAny[nb];
        if (!preMagentaSide && satMagentaSide) ++agg->neutralBandCrossToMagentaAtSat1pct[nb];
        if (!satMagentaSide && curveMagentaSide) ++agg->neutralBandCrossToMagentaAtCurve1pct[nb];
        if (!satMagentaSide && curveYMagentaSide) ++agg->neutralBandCrossToMagentaAtCurveY1pct[nb];''',
'''        agg->neutralBandCurveYGreenDeficit[nb] += curveYGreenDeficit;
        agg->neutralBandCurveLumaScaleGreenDeficit[nb] += curveLumaScaleGreenDeficit;
        agg->neutralBandPreSpread[nb] += preSpread;
        agg->neutralBandSatSpread[nb] += satSpread;
        agg->neutralBandCurveSpread[nb] += curveSpread;
        agg->neutralBandCurveYSpread[nb] += curveYSpread;
        agg->neutralBandCurveLumaScaleSpread[nb] += curveLumaScaleSpread;
        const bool preMagentaSide = preGreenDeficit > magentaSideThreshold;
        const bool satMagentaSide = satGreenDeficit > magentaSideThreshold;
        const bool curveMagentaSide = curveGreenDeficit > magentaSideThreshold;
        const bool curveYMagentaSide = curveYGreenDeficit > magentaSideThreshold;
        const bool curveLumaScaleMagentaSide = curveLumaScaleGreenDeficit > magentaSideThreshold;
        if (preMagentaSide) ++agg->neutralBandPreMagentaSide1pct[nb];
        if (satMagentaSide) ++agg->neutralBandSatMagentaSide1pct[nb];
        if (curveMagentaSide) ++agg->neutralBandCurveMagentaSide1pct[nb];
        if (curveYMagentaSide) ++agg->neutralBandCurveYMagentaSide1pct[nb];
        if (curveLumaScaleMagentaSide) ++agg->neutralBandCurveLumaScaleMagentaSide1pct[nb];
        if (curveYClipAny) ++agg->neutralBandCurveYClipAny[nb];
        if (curveLumaScaleClipAny) ++agg->neutralBandCurveLumaScaleClipAny[nb];
        if (!preMagentaSide && satMagentaSide) ++agg->neutralBandCrossToMagentaAtSat1pct[nb];
        if (!satMagentaSide && curveMagentaSide) ++agg->neutralBandCrossToMagentaAtCurve1pct[nb];
        if (!satMagentaSide && curveYMagentaSide) ++agg->neutralBandCrossToMagentaAtCurveY1pct[nb];
        if (!satMagentaSide && curveLumaScaleMagentaSide) ++agg->neutralBandCrossToMagentaAtCurveLumaScale1pct[nb];''', 'LUMASCALE neutral accumulation')

t = replace_once(t,
'''    os << "\\\"schema\\\":\\\"m9cam.curveplace1b.dualaxis1a.v1\\\",";
    os << "\\\"parentDiagnostic\\\":\\\"CURVEPLACE1A_plus_CURVEDOMAIN1B_NEUTRALAXIS1A\\\",";
    os << "\\\"dualAxisAuditReadOnly\\\":true,\\\"curvePlace1AFirmwareStageOrderClaim\\\":false,";''',
'''    os << "\\\"schema\\\":\\\"m9cam.curveplace1c.lumascale1a.v1\\\",";
    os << "\\\"parentDiagnostic\\\":\\\"CURVEPLACE1B_DUALAXIS1A\\\",";
    os << "\\\"triplePathAuditReadOnly\\\":true,\\\"curvePlace1AFirmwareStageOrderClaim\\\":false,\\\"lumaScaleFirmwareStageOrderClaim\\\":false,";''', 'LUMASCALE telemetry schema')

t = replace_once(t,
'''            os << "\\\"crossToMagentaAtCurveY1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurveY1pct[nb] / nd) << "}";''',
'''            os << "\\\"crossToMagentaAtCurveY1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurveY1pct[nb] / nd) << ",";
            os << "\\\"meanGreenDeficitNormalizedPostCurveLumaScale\\\":" << (a.neutralBandCurveLumaScaleGreenDeficit[nb] / nd) << ",";
            os << "\\\"curveLumaScaleMinusRgbMeanGreenDeficit\\\":" << ((a.neutralBandCurveLumaScaleGreenDeficit[nb] - a.neutralBandCurveGreenDeficit[nb]) / nd) << ",";
            os << "\\\"meanRelativeSpreadPostCurveLumaScale\\\":" << (a.neutralBandCurveLumaScaleSpread[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostCurveLumaScale\\\":" << (a.neutralBandCurveLumaScaleMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"curveLumaScaleClipAnyFraction\\\":" << (a.neutralBandCurveLumaScaleClipAny[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtCurveLumaScale1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurveLumaScale1pct[nb] / nd) << "}";''', 'LUMASCALE neutral JSON')

CPP.write_text(t)

j = JAVA.read_text()

j = replace_once(j,
'''                                "_SKYSAT_SAT3_BYPASS",
                                "_CURVEPLACE_SAT3_CURVE02_Y"
                        };''',
'''                                "_SKYSAT_SAT3_BYPASS",
                                "_CURVEPLACE_SAT3_CURVE02_Y",
                                "_CURVEPLACE_SAT3_CURVE02_LUMASCALE"
                        };''', 'sixth JPEG suffix')

j = replace_once(j,
'''                                "skysat_sat3_bypass_gainlocked",
                                "curveplace_sat3_curve02_y_fixed_bt601_chroma_gainlocked"
                        };''',
'''                                "skysat_sat3_bypass_gainlocked",
                                "curveplace_sat3_curve02_y_fixed_bt601_chroma_gainlocked",
                                "curveplace_sat3_curve02_lumascale_gainlocked"
                        };''', 'sixth probe name')

j = replace_once(j,
'''                        int[] bridgeProbeModes = {50, 51, 52, 53, 54};
                        boolean[] selfMeterFlags = {true, false, false, false, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30, 0.30};''',
'''                        int[] bridgeProbeModes = {50, 51, 52, 53, 54, 55};
                        boolean[] selfMeterFlags = {true, false, false, false, false, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true, true, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30, 0.30, 0.30};''', 'six diagnostic modes and flags')

j = replace_once(j,
'''            final boolean curvePlaceDiagnosticEncoded1A = bridgeProbeMode == 54;
            final boolean skyDiagnosticEncodedAny1A =
                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A
                            || skySatDiagnosticEncoded1A || curvePlaceDiagnosticEncoded1A;''',
'''            final boolean curvePlaceDiagnosticEncoded1A = bridgeProbeMode == 54;
            final boolean curvePlaceLumaScaleDiagnostic1A = bridgeProbeMode == 55;
            final boolean skyDiagnosticEncodedAny1A =
                    skyChromaDiagnosticEncoded1A || skyDownDiagnosticEncoded1A
                            || skySatDiagnosticEncoded1A || curvePlaceDiagnosticEncoded1A
                            || curvePlaceLumaScaleDiagnostic1A;''', 'LUMASCALE encoding flag')

j = replace_once(j,
'''                                    : (curvePlaceDiagnosticEncoded1A ? 11 : 0)));''',
'''                                    : (curvePlaceDiagnosticEncoded1A ? 11
                                            : (curvePlaceLumaScaleDiagnostic1A ? 12 : 0))));''', 'mode55-to-native12 mapping')

j = replace_once(j,
'''            case 11: return "CURVEPLACE_SAT3_CURVE02_Y_FIXED_BT601_CHROMA";
            default: return "CONTROL_PRODUCTION_CLIP";''',
'''            case 11: return "CURVEPLACE_SAT3_CURVE02_Y_FIXED_BT601_CHROMA";
            case 12: return "CURVEPLACE_SAT3_CURVE02_LUMASCALE";
            default: return "CONTROL_PRODUCTION_CLIP";''', 'mode12 name')

j = replace_once(j,
'''            d.put("curvePlace1A", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AStructuralDiscriminatorOnly", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AFirmwareStageOrderClaim", false);
            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);''',
'''            d.put("curvePlace1A", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AStructuralDiscriminatorOnly", curvePlaceDiagnosticEncoded1A);
            d.put("curvePlace1AFirmwareStageOrderClaim", false);
            d.put("curvePlaceLumaScale1A", curvePlaceLumaScaleDiagnostic1A);
            d.put("curvePlaceLumaScaleChromaticityPreservingBeforeClip", curvePlaceLumaScaleDiagnostic1A);
            d.put("curvePlaceLumaScaleFirmwareStageOrderClaim", false);
            d.put("skyDiagnosticAny1A", skyDiagnosticEncodedAny1A);''', 'LUMASCALE metadata')

j = replace_once(j,
'''                        nativeAb1A.put("tc20GainIsolation",
                                "B_C_D_E_locked_to_A_exact_effective_render_gain");
                        nativeAb1A.put("curvePlace1A", true);''',
'''                        nativeAb1A.put("tc20GainIsolation",
                                "B_C_D_E_F_locked_to_A_exact_effective_render_gain");
                        nativeAb1A.put("curvePlace1A", true);
                        nativeAb1A.put("curvePlaceLumaScale1A", true);
                        nativeAb1A.put("curvePlaceLumaScaleVariant",
                                "SAT3 -> exact BT601 Y11 -> curve02(Y) -> common RGB output scale curve02(Y)/Y -> frozen BT601_422/TG1");''', 'experiment metadata and gain lock')

JAVA.write_text(j)

g = GRADLE.read_text()
g = replace_once(g,
                 '-curvedomain1b-neutralaxis1a-curveplace1b-dualaxis1a-nativewpclip1a',
                 '-curvedomain1b-neutralaxis1a-curveplace1c-lumascale1a-nativewpclip1a',
                 'version marker')
GRADLE.write_text(g)

print('CURVEPLACE1C-LUMASCALE1A diagnostic applied')
print(' - production mode 0 unchanged')
print(' - CURVEPLACE1A fixed-chroma mode 11 retained unchanged')
print(' - added gain-locked SAT3 common-RGB-scale curve02(Y) mode 12')
print(' - telemetry now compares RGB curve, fixed-chroma Y, and LUMASCALE on identical neutral samples')
print(' - no scene detector, tint correction, saturation weakening, exposure, TC20, HSM, or shading change')
