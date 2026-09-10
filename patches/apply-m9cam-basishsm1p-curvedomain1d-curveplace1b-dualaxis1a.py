#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
GRADLE = ROOT / 'app/build.gradle'

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'CURVEPLACE1B-DUALAXIS1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)

t = CPP.read_text()

# CURVEPLACE1B-DUALAXIS1A is telemetry-only. It evaluates, on the same sampled
# post-SAT pixels used by CURVEDOMAIN1B NEUTRALAXIS1A, both:
#   A) current production curve02 independently on RGB
#   B) CURVEPLACE1A curve02 on exact BT.601 Y with Cb/Cr carried unchanged
# It does not mutate production pixels, diagnostic JPEG pixels, gain, meter,
# exposure, HSM, saturation, shading, curve tables, BT.601 output, or TG1.

t = replace_once(t,
'''    uint64_t neutralBandCrossToMagentaAtSat1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurve1pct[3]{};
    uint64_t spatialCount[9]{};''',
'''    uint64_t neutralBandCrossToMagentaAtSat1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurve1pct[3]{};
    double neutralBandCurveYGreenDeficit[3]{};
    double neutralBandCurveYSpread[3]{};
    uint64_t neutralBandCurveYMagentaSide1pct[3]{};
    uint64_t neutralBandCrossToMagentaAtCurveY1pct[3]{};
    uint64_t neutralBandCurveYClipAny[3]{};
    uint64_t spatialCount[9]{};''', 'dual-axis aggregate fields')

t = replace_once(t,
'''inline double satGreenDeficitNormalized(double r, double g, double b) {
    const double mean = (r + g + b) / 3.0;
    if (mean <= 1e-9) return 0.0;
    // Positive = G below the R/B average (magenta direction); negative = green direction.
    return (((r + b) * 0.5) - g) / mean;
}
''',
'''inline double satGreenDeficitNormalized(double r, double g, double b) {
    const double mean = (r + g + b) / 3.0;
    if (mean <= 1e-9) return 0.0;
    // Positive = G below the R/B average (magenta direction); negative = green direction.
    return (((r + b) * 0.5) - g) / mean;
}

inline bool satCurvePlaceYRgb8(const std::array<uint8_t, 2048>& curve,
                               const int64_t rgb11[3],
                               double outRgb8[3]) {
    // Exact arithmetic mirror of CURVEPLACE1A mode 11. Read-only audit helper.
    const int64_t y11 = clipl((4899LL * rgb11[0] + 9617LL * rgb11[1] + 1868LL * rgb11[2]) >> 14, 0, LUT_MAX);
    const int64_t cb11 = (-2765LL * rgb11[0] - 5427LL * rgb11[1] + 8192LL * rgb11[2]) >> 14;
    const int64_t cr11 = (8192LL * rgb11[0] - 6860LL * rgb11[1] - 1332LL * rgb11[2]) >> 14;
    const double yy = static_cast<double>(curve[static_cast<size_t>(y11)]);
    const double scale11to8 = 255.0 / static_cast<double>(LUT_MAX);
    const double cb8 = static_cast<double>(cb11) * scale11to8;
    const double cr8 = static_cast<double>(cr11) * scale11to8;
    const auto clipRoundU8Audit = [](double v) -> double {
        if (v <= 0.0) return 0.0;
        if (v >= 255.0) return 255.0;
        return static_cast<double>(static_cast<int>(v + 0.5));
    };
    const double rrRaw = yy + 1.402 * cr8;
    const double ggRaw = yy - .344136 * cb8 - .714136 * cr8;
    const double bbRaw = yy + 1.772 * cb8;
    outRgb8[0] = clipRoundU8Audit(rrRaw);
    outRgb8[1] = clipRoundU8Audit(ggRaw);
    outRgb8[2] = clipRoundU8Audit(bbRaw);
    return rrRaw <= 0.0 || rrRaw >= 255.0 || ggRaw <= 0.0 || ggRaw >= 255.0 || bbRaw <= 0.0 || bbRaw >= 255.0;
}
''', 'CURVEPLACE1A arithmetic mirror helper')

t = replace_once(t,
'''    const double curveSpread = satRelativeSpread(curveRgb[0], curveRgb[1], curveRgb[2]);
    const double preGreenDeficit = satGreenDeficitNormalized(static_cast<double>(pre[0]), static_cast<double>(pre[1]), static_cast<double>(pre[2]));
    const double satGreenDeficit = satGreenDeficitNormalized(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));
    const double curveGreenDeficit = satGreenDeficitNormalized(curveRgb[0], curveRgb[1], curveRgb[2]);
    constexpr double neutralThresholds[3] = {0.05, 0.10, 0.20};''',
'''    const double curveSpread = satRelativeSpread(curveRgb[0], curveRgb[1], curveRgb[2]);
    const double preGreenDeficit = satGreenDeficitNormalized(static_cast<double>(pre[0]), static_cast<double>(pre[1]), static_cast<double>(pre[2]));
    const double satGreenDeficit = satGreenDeficitNormalized(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));
    const double curveGreenDeficit = satGreenDeficitNormalized(curveRgb[0], curveRgb[1], curveRgb[2]);
    double curveYRgb[3] = {0.0, 0.0, 0.0};
    const bool curveYClipAny = satCurvePlaceYRgb8(curve, clamped, curveYRgb);
    const double curveYSpread = satRelativeSpread(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    const double curveYGreenDeficit = satGreenDeficitNormalized(curveYRgb[0], curveYRgb[1], curveYRgb[2]);
    constexpr double neutralThresholds[3] = {0.05, 0.10, 0.20};''', 'dual-axis per-pixel values')

t = replace_once(t,
'''        agg->neutralBandCurveGreenDeficit[nb] += curveGreenDeficit;
        agg->neutralBandPreSpread[nb] += preSpread;
        agg->neutralBandSatSpread[nb] += satSpread;
        agg->neutralBandCurveSpread[nb] += curveSpread;
        const bool preMagentaSide = preGreenDeficit > magentaSideThreshold;
        const bool satMagentaSide = satGreenDeficit > magentaSideThreshold;
        const bool curveMagentaSide = curveGreenDeficit > magentaSideThreshold;
        if (preMagentaSide) ++agg->neutralBandPreMagentaSide1pct[nb];
        if (satMagentaSide) ++agg->neutralBandSatMagentaSide1pct[nb];
        if (curveMagentaSide) ++agg->neutralBandCurveMagentaSide1pct[nb];
        if (!preMagentaSide && satMagentaSide) ++agg->neutralBandCrossToMagentaAtSat1pct[nb];
        if (!satMagentaSide && curveMagentaSide) ++agg->neutralBandCrossToMagentaAtCurve1pct[nb];''',
'''        agg->neutralBandCurveGreenDeficit[nb] += curveGreenDeficit;
        agg->neutralBandCurveYGreenDeficit[nb] += curveYGreenDeficit;
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
        if (!satMagentaSide && curveYMagentaSide) ++agg->neutralBandCrossToMagentaAtCurveY1pct[nb];''', 'dual-axis neutral accumulation')

t = replace_once(t,
'''    os << "\\\"schema\\\":\\\"m9cam.curvedomain1b.neutralaxis1a.v1\\\",";
    os << "\\\"parentDiagnostic\\\":\\\"CURVEDOMAIN1A\\\",";''',
'''    os << "\\\"schema\\\":\\\"m9cam.curveplace1b.dualaxis1a.v1\\\",";
    os << "\\\"parentDiagnostic\\\":\\\"CURVEPLACE1A_plus_CURVEDOMAIN1B_NEUTRALAXIS1A\\\",";
    os << "\\\"dualAxisAuditReadOnly\\\":true,\\\"curvePlace1AFirmwareStageOrderClaim\\\":false,";''', 'dual-axis schema')

t = replace_once(t,
'''            os << "\\\"meanGreenDeficitNormalizedPostCurve\\\":" << (a.neutralBandCurveGreenDeficit[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPre\\\":" << (a.neutralBandPreSpread[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPostSatClamp\\\":" << (a.neutralBandSatSpread[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPostCurve\\\":" << (a.neutralBandCurveSpread[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPre\\\":" << (a.neutralBandPreMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostSatClamp\\\":" << (a.neutralBandSatMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostCurve\\\":" << (a.neutralBandCurveMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtSat1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtSat1pct[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtCurve1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurve1pct[nb] / nd) << "}";''',
'''            os << "\\\"meanGreenDeficitNormalizedPostCurve\\\":" << (a.neutralBandCurveGreenDeficit[nb] / nd) << ",";
            os << "\\\"meanGreenDeficitNormalizedPostCurveY\\\":" << (a.neutralBandCurveYGreenDeficit[nb] / nd) << ",";
            os << "\\\"curveYMinusRgbMeanGreenDeficit\\\":" << ((a.neutralBandCurveYGreenDeficit[nb] - a.neutralBandCurveGreenDeficit[nb]) / nd) << ",";
            os << "\\\"meanRelativeSpreadPre\\\":" << (a.neutralBandPreSpread[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPostSatClamp\\\":" << (a.neutralBandSatSpread[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPostCurve\\\":" << (a.neutralBandCurveSpread[nb] / nd) << ",";
            os << "\\\"meanRelativeSpreadPostCurveY\\\":" << (a.neutralBandCurveYSpread[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPre\\\":" << (a.neutralBandPreMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostSatClamp\\\":" << (a.neutralBandSatMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostCurve\\\":" << (a.neutralBandCurveMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"magentaSide1pctFractionPostCurveY\\\":" << (a.neutralBandCurveYMagentaSide1pct[nb] / nd) << ",";
            os << "\\\"curveYClipAnyFraction\\\":" << (a.neutralBandCurveYClipAny[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtSat1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtSat1pct[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtCurve1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurve1pct[nb] / nd) << ",";
            os << "\\\"crossToMagentaAtCurveY1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurveY1pct[nb] / nd) << "}";''', 'dual-axis neutral JSON')

CPP.write_text(t)

g = GRADLE.read_text()
g = replace_once(g,
                 '-curvedomain1b-neutralaxis1a-curveplace1a-nativewpclip1a',
                 '-curvedomain1b-neutralaxis1a-curveplace1b-dualaxis1a-nativewpclip1a',
                 'version marker')
GRADLE.write_text(g)

print('CURVEPLACE1B-DUALAXIS1A read-only audit applied')
print(' - same pre-SAT neutral bands as CURVEDOMAIN1B')
print(' - compares production RGB curve02 against CURVEPLACE1A Y-only curve02')
print(' - exact CURVEPLACE1A Y/Cb/Cr arithmetic mirrored in telemetry')
print(' - no production or diagnostic JPEG pixel mutation')
