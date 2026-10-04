#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
GRADLE = ROOT / 'app/build.gradle'

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'CURVEDOMAIN1B-NEUTRALAXIS1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)

t = CPP.read_text()

# Read-only extension: add near-neutral green<->magenta axis diagnostics.
# Selection is based on pre-SAT relative RGB spread, not semantic sky/cloud detection.
t = replace_once(t,
'''    uint64_t hueSectorMagentaClamped[12]{};\n    uint64_t hueSectorMagentaCurve[12]{};\n    uint64_t spatialCount[9]{};''',
'''    uint64_t hueSectorMagentaClamped[12]{};\n    uint64_t hueSectorMagentaCurve[12]{};\n    uint64_t neutralBandCount[3]{};\n    uint64_t neutralBandEvenBranch[3]{};\n    double neutralBandPreGreenDeficit[3]{};\n    double neutralBandSatGreenDeficit[3]{};\n    double neutralBandCurveGreenDeficit[3]{};\n    double neutralBandPreSpread[3]{};\n    double neutralBandSatSpread[3]{};\n    double neutralBandCurveSpread[3]{};\n    uint64_t neutralBandPreMagentaSide1pct[3]{};\n    uint64_t neutralBandSatMagentaSide1pct[3]{};\n    uint64_t neutralBandCurveMagentaSide1pct[3]{};\n    uint64_t neutralBandCrossToMagentaAtSat1pct[3]{};\n    uint64_t neutralBandCrossToMagentaAtCurve1pct[3]{};\n    uint64_t spatialCount[9]{};''', 'neutral aggregate fields')

t = replace_once(t,
'''inline int satHueSector12(double hueDeg, double chroma11) {\n    // Hue is unstable close to neutral. Exclude <=2% LUT chroma from sector metrics.\n    if (chroma11 <= LUT_MAX * 0.02) return -1;\n    int sector = static_cast<int>(std::floor(hueDeg / 30.0));\n    if (sector < 0) sector = 0;\n    if (sector > 11) sector = 11;\n    return sector;\n}\n''',
'''inline int satHueSector12(double hueDeg, double chroma11) {\n    // Hue is unstable close to neutral. Exclude <=2% LUT chroma from sector metrics.\n    if (chroma11 <= LUT_MAX * 0.02) return -1;\n    int sector = static_cast<int>(std::floor(hueDeg / 30.0));\n    if (sector < 0) sector = 0;\n    if (sector > 11) sector = 11;\n    return sector;\n}\n\ninline double satRelativeSpread(double r, double g, double b) {\n    const double mean = (r + g + b) / 3.0;\n    if (mean <= 1e-9) return 0.0;\n    return satChroma(r, g, b) / mean;\n}\n\ninline double satGreenDeficitNormalized(double r, double g, double b) {\n    const double mean = (r + g + b) / 3.0;\n    if (mean <= 1e-9) return 0.0;\n    // Positive = G below the R/B average (magenta direction); negative = green direction.\n    return (((r + b) * 0.5) - g) / mean;\n}\n''', 'neutral helpers')

t = replace_once(t,
'''    if (hueSector >= 0) {\n        ++agg->hueSectorCount[hueSector];\n        agg->hueSectorMatrixShift[hueSector] += dPreClamped;\n        agg->hueSectorCurveShift[hueSector] += dClampedCurve;\n        agg->hueSectorTotalShift[hueSector] += dPreCurve;\n        if (magentaClamped) ++agg->hueSectorMagentaClamped[hueSector];\n        if (magentaCurve) ++agg->hueSectorMagentaCurve[hueSector];\n    }\n\n    if (sampleOut) {''',
'''    if (hueSector >= 0) {\n        ++agg->hueSectorCount[hueSector];\n        agg->hueSectorMatrixShift[hueSector] += dPreClamped;\n        agg->hueSectorCurveShift[hueSector] += dClampedCurve;\n        agg->hueSectorTotalShift[hueSector] += dPreCurve;\n        if (magentaClamped) ++agg->hueSectorMagentaClamped[hueSector];\n        if (magentaCurve) ++agg->hueSectorMagentaCurve[hueSector];\n    }\n\n    // CURVEDOMAIN1B-NEUTRALAXIS1A: use relative pre-SAT RGB spread because hue\n    // becomes numerically meaningless for clouds/greys near the neutral axis.\n    const double preSpread = satRelativeSpread(static_cast<double>(pre[0]), static_cast<double>(pre[1]), static_cast<double>(pre[2]));\n    const double satSpread = satRelativeSpread(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));\n    const double curveSpread = satRelativeSpread(curveRgb[0], curveRgb[1], curveRgb[2]);\n    const double preGreenDeficit = satGreenDeficitNormalized(static_cast<double>(pre[0]), static_cast<double>(pre[1]), static_cast<double>(pre[2]));\n    const double satGreenDeficit = satGreenDeficitNormalized(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));\n    const double curveGreenDeficit = satGreenDeficitNormalized(curveRgb[0], curveRgb[1], curveRgb[2]);\n    constexpr double neutralThresholds[3] = {0.05, 0.10, 0.20};\n    constexpr double magentaSideThreshold = 0.01;\n    for (int nb = 0; nb < 3; ++nb) {\n        if (preSpread > neutralThresholds[nb]) continue;\n        ++agg->neutralBandCount[nb];\n        if (pre[0] >= pre[1]) ++agg->neutralBandEvenBranch[nb];\n        agg->neutralBandPreGreenDeficit[nb] += preGreenDeficit;\n        agg->neutralBandSatGreenDeficit[nb] += satGreenDeficit;\n        agg->neutralBandCurveGreenDeficit[nb] += curveGreenDeficit;\n        agg->neutralBandPreSpread[nb] += preSpread;\n        agg->neutralBandSatSpread[nb] += satSpread;\n        agg->neutralBandCurveSpread[nb] += curveSpread;\n        const bool preMagentaSide = preGreenDeficit > magentaSideThreshold;\n        const bool satMagentaSide = satGreenDeficit > magentaSideThreshold;\n        const bool curveMagentaSide = curveGreenDeficit > magentaSideThreshold;\n        if (preMagentaSide) ++agg->neutralBandPreMagentaSide1pct[nb];\n        if (satMagentaSide) ++agg->neutralBandSatMagentaSide1pct[nb];\n        if (curveMagentaSide) ++agg->neutralBandCurveMagentaSide1pct[nb];\n        if (!preMagentaSide && satMagentaSide) ++agg->neutralBandCrossToMagentaAtSat1pct[nb];\n        if (!satMagentaSide && curveMagentaSide) ++agg->neutralBandCrossToMagentaAtCurve1pct[nb];\n    }\n\n    if (sampleOut) {''', 'neutral accumulation')

t = replace_once(t,
'''    os << "\\\"schema\\\":\\\"m9cam.curvedomain1a.v1\\\",";\n    os << "\\\"parentDiagnostic\\\":\\\"SATDOMAIN1A\\\",";''',
'''    os << "\\\"schema\\\":\\\"m9cam.curvedomain1b.neutralaxis1a.v1\\\",";\n    os << "\\\"parentDiagnostic\\\":\\\"CURVEDOMAIN1A\\\",";''', 'schema')

t = replace_once(t,
'''        os << "],\\\"magentaCurveFraction\\\":[";\n        for (int s = 0; s < 12; ++s) { if (s) os << ","; const double sd = a.hueSectorCount[s] ? static_cast<double>(a.hueSectorCount[s]) : 1.0; os << (a.hueSectorMagentaCurve[s] / sd); }\n        os << "]},";\n        os << "\\\"spatial3x3\\\":{\\\"pixelCount\\\":[";''',
'''        os << "],\\\"magentaCurveFraction\\\":[";\n        for (int s = 0; s < 12; ++s) { if (s) os << ","; const double sd = a.hueSectorCount[s] ? static_cast<double>(a.hueSectorCount[s]) : 1.0; os << (a.hueSectorMagentaCurve[s] / sd); }\n        os << "]},";\n        os << "\\\"neutralAxisAudit\\\":{\\\"selection\\\":\\\"preSAT_relative_RGB_spread\\\",\\\"greenDeficitSign\\\":\\\"positive_is_magenta_direction_negative_is_green_direction\\\",\\\"magentaSideThresholdNormalized\\\":0.01,\\\"bands\\\":[";\n        constexpr double neutralThresholdsJson[3] = {0.05, 0.10, 0.20};\n        for (int nb = 0; nb < 3; ++nb) {\n            if (nb) os << ",";\n            const double nd = a.neutralBandCount[nb] ? static_cast<double>(a.neutralBandCount[nb]) : 1.0;\n            os << "{\\\"maxPreRelativeSpread\\\":" << neutralThresholdsJson[nb] << ",";\n            os << "\\\"pixelCount\\\":" << a.neutralBandCount[nb] << ",";\n            os << "\\\"branchEvenFraction\\\":" << (a.neutralBandEvenBranch[nb] / nd) << ",";\n            os << "\\\"meanGreenDeficitNormalizedPre\\\":" << (a.neutralBandPreGreenDeficit[nb] / nd) << ",";\n            os << "\\\"meanGreenDeficitNormalizedPostSatClamp\\\":" << (a.neutralBandSatGreenDeficit[nb] / nd) << ",";\n            os << "\\\"meanGreenDeficitNormalizedPostCurve\\\":" << (a.neutralBandCurveGreenDeficit[nb] / nd) << ",";\n            os << "\\\"meanRelativeSpreadPre\\\":" << (a.neutralBandPreSpread[nb] / nd) << ",";\n            os << "\\\"meanRelativeSpreadPostSatClamp\\\":" << (a.neutralBandSatSpread[nb] / nd) << ",";\n            os << "\\\"meanRelativeSpreadPostCurve\\\":" << (a.neutralBandCurveSpread[nb] / nd) << ",";\n            os << "\\\"magentaSide1pctFractionPre\\\":" << (a.neutralBandPreMagentaSide1pct[nb] / nd) << ",";\n            os << "\\\"magentaSide1pctFractionPostSatClamp\\\":" << (a.neutralBandSatMagentaSide1pct[nb] / nd) << ",";\n            os << "\\\"magentaSide1pctFractionPostCurve\\\":" << (a.neutralBandCurveMagentaSide1pct[nb] / nd) << ",";\n            os << "\\\"crossToMagentaAtSat1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtSat1pct[nb] / nd) << ",";\n            os << "\\\"crossToMagentaAtCurve1pctFraction\\\":" << (a.neutralBandCrossToMagentaAtCurve1pct[nb] / nd) << "}";\n        }\n        os << "]},";\n        os << "\\\"spatial3x3\\\":{\\\"pixelCount\\\":[";''', 'neutral JSON')

CPP.write_text(t)

g = GRADLE.read_text()
g = replace_once(g, '-curvedomain1a-nativewpclip1a', '-curvedomain1b-neutralaxis1a-nativewpclip1a', 'version')
GRADLE.write_text(g)

print('CURVEDOMAIN1B-NEUTRALAXIS1A read-only diagnostic applied')
print(' - no rendered-pixel mutation')
print(' - near-neutral bands selected by pre-SAT relative RGB spread <=5/10/20%')
print(' - positive normalized green deficit = magenta direction')
print(' - measures pre-SAT -> post-SAT-clamp -> post-curve02')
