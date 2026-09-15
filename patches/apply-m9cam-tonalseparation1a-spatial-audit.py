#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
RENDERER = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'TONALSEPARATION1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)


c = CPP.read_text()
if 'TONALSEPARATION1A_BEGIN' in c:
    raise SystemExit('TONALSEPARATION1A already applied')

helpers = r'''
// TONALSEPARATION1A_BEGIN
// Read-only spatial tonal audit. This code executes only inside auditSatDomainJson;
// it never writes cam, ColorContext, meter gain, or rendered output buffers.
static constexpr int TONAL1A_COLS = 12;
static constexpr int TONAL1A_ROWS = 8;
static constexpr int TONAL1A_CELLS = TONAL1A_COLS * TONAL1A_ROWS;
static constexpr int TONAL1A_BINS = 64;
static constexpr int TONAL1A_STAGES = 6;
static constexpr int TONAL1A_SAMPLE_STRIDE = 4;
static constexpr double TONAL1A_HIST_MAX = 1.25;

struct Tonal1AStageAccum {
    uint64_t count = 0;
    double lumaSum = 0.0;
    double rgbSum[3]{};
    uint64_t below005 = 0;
    uint64_t below010 = 0;
    uint64_t above090 = 0;
    uint64_t above100 = 0;
    uint64_t hist[TONAL1A_BINS]{};
};

struct Tonal1ACell {
    Tonal1AStageAccum stage[TONAL1A_STAGES]{};
};

inline double tonal1ALuma601(double r, double g, double b) {
    return 0.299 * r + 0.587 * g + 0.114 * b;
}

inline void tonal1AAccumulate(Tonal1AStageAccum* a, double r, double g, double b) {
    if (!a) return;
    const double y = tonal1ALuma601(r, g, b);
    ++a->count;
    a->lumaSum += y;
    a->rgbSum[0] += r;
    a->rgbSum[1] += g;
    a->rgbSum[2] += b;
    if (y < 0.05) ++a->below005;
    if (y < 0.10) ++a->below010;
    if (y > 0.90) ++a->above090;
    if (y > 1.00) ++a->above100;
    double yh = y;
    if (!std::isfinite(yh)) yh = 0.0;
    if (yh < 0.0) yh = 0.0;
    if (yh > TONAL1A_HIST_MAX) yh = TONAL1A_HIST_MAX;
    int bin = static_cast<int>((yh / TONAL1A_HIST_MAX) * TONAL1A_BINS);
    if (bin < 0) bin = 0;
    if (bin >= TONAL1A_BINS) bin = TONAL1A_BINS - 1;
    ++a->hist[bin];
}

inline double tonal1AQuantile(const Tonal1AStageAccum& a, double q) {
    if (!a.count) return 0.0;
    uint64_t target = static_cast<uint64_t>(std::ceil(q * static_cast<double>(a.count)));
    if (target < 1) target = 1;
    uint64_t seen = 0;
    for (int i = 0; i < TONAL1A_BINS; ++i) {
        seen += a.hist[i];
        if (seen >= target) {
            return (static_cast<double>(i) + 0.5) * TONAL1A_HIST_MAX / TONAL1A_BINS;
        }
    }
    return TONAL1A_HIST_MAX;
}

inline void tonal1AEvalSat(const std::array<int64_t, 9>& q,
                           const int64_t pre[3],
                           const ColorContext& ctx,
                           double satOut[3],
                           double curveOut[3]) {
    const int64_t a0 = q[0] * pre[0] + q[1] * pre[1] + q[2] * pre[2];
    const int64_t a1 = q[3] * pre[0] + q[4] * pre[1] + q[5] * pre[2];
    const int64_t a2 = q[6] * pre[0] + q[7] * pre[1] + q[8] * pre[2];
    const int64_t shifted[3] = {a0 >> 16, a1 >> 16, a2 >> 16};
    for (int ch = 0; ch < 3; ++ch) {
        const int64_t idx = clipl(shifted[ch], 0, LUT_MAX);
        satOut[ch] = static_cast<double>(idx) / static_cast<double>(LUT_MAX);
        curveOut[ch] = static_cast<double>(ctx.curve[static_cast<size_t>(idx)]);
    }
}

inline void tonal1AWriteStageJson(std::ostringstream& os, const Tonal1AStageAccum& a) {
    const double den = a.count ? static_cast<double>(a.count) : 1.0;
    os << "{\"count\":" << a.count;
    os << ",\"meanLuma601\":" << (a.lumaSum / den);
    os << ",\"p10Luma601\":" << tonal1AQuantile(a, 0.10);
    os << ",\"p50Luma601\":" << tonal1AQuantile(a, 0.50);
    os << ",\"p90Luma601\":" << tonal1AQuantile(a, 0.90);
    os << ",\"p90MinusP10\":" << (tonal1AQuantile(a, 0.90) - tonal1AQuantile(a, 0.10));
    os << ",\"meanRGB\":[" << (a.rgbSum[0] / den) << "," << (a.rgbSum[1] / den) << "," << (a.rgbSum[2] / den) << "]";
    os << ",\"below005Fraction\":" << (a.below005 / den);
    os << ",\"below010Fraction\":" << (a.below010 / den);
    os << ",\"above090Fraction\":" << (a.above090 / den);
    os << ",\"above100Fraction\":" << (a.above100 / den) << "}";
}
// TONALSEPARATION1A_END
'''

marker = 'std::string auditSatDomainJson(const ColorContext& ctx,'
pos = c.find(marker)
if pos < 0:
    raise SystemExit('TONALSEPARATION1A auditSatDomainJson marker not found')
c = c[:pos] + helpers + '\n' + c[pos:]

# Work only inside auditSatDomainJson so render arithmetic remains untouched.
start = c.find(marker)
ret = c.find('    return os.str();', start)
if ret < 0:
    raise SystemExit('TONALSEPARATION1A audit return anchor not found')
func = c[start:ret + len('    return os.str();')]

func = replace_once(func,
'''    double hsm[3]{};\n    double m9[3]{};''',
'''    double hsm[3]{};\n    double m9[3]{};\n    Tonal1ACell* tonal1AGrid = new Tonal1ACell[TONAL1A_CELLS]();''',
'audit grid allocation')

acc_anchor = '''        const int bin = by * 3 + bx;\n        SatDomainSample s3{};'''
acc_code = '''        const int bin = by * 3 + bx;\n\n        if ((x % TONAL1A_SAMPLE_STRIDE) == 0 && (y % TONAL1A_SAMPLE_STRIDE) == 0) {\n            const int tx = std::min(TONAL1A_COLS - 1, (x * TONAL1A_COLS) / std::max(1, width));\n            const int ty = std::min(TONAL1A_ROWS - 1, (y * TONAL1A_ROWS) / std::max(1, height));\n            Tonal1ACell& tc = tonal1AGrid[ty * TONAL1A_COLS + tx];\n\n            const double camRgb[3] = {\n                static_cast<double>(cam[c + 0]) / static_cast<double>(RAW_MAX),\n                static_cast<double>(cam[c + 1]) / static_cast<double>(RAW_MAX),\n                static_cast<double>(cam[c + 2]) / static_cast<double>(RAW_MAX)\n            };\n            const double preRgb[3] = {\n                static_cast<double>(pre[0]) / static_cast<double>(RAW_MAX),\n                static_cast<double>(pre[1]) / static_cast<double>(RAW_MAX),\n                static_cast<double>(pre[2]) / static_cast<double>(RAW_MAX)\n            };\n            double sat2[3]{}, sat3[3]{}, curve2[3]{}, curve3[3]{};\n            tonal1AEvalSat(even ? Q2E : Q2O, pre, ctx, sat2, curve2);\n            tonal1AEvalSat(even ? QE : QO, pre, ctx, sat3, curve3);\n\n            tonal1AAccumulate(&tc.stage[0], camRgb[0], camRgb[1], camRgb[2]);\n            tonal1AAccumulate(&tc.stage[1], preRgb[0], preRgb[1], preRgb[2]);\n            tonal1AAccumulate(&tc.stage[2], sat2[0], sat2[1], sat2[2]);\n            tonal1AAccumulate(&tc.stage[3], sat3[0], sat3[1], sat3[2]);\n            tonal1AAccumulate(&tc.stage[4], curve2[0], curve2[1], curve2[2]);\n            tonal1AAccumulate(&tc.stage[5], curve3[0], curve3[1], curve3[2]);\n        }\n\n        SatDomainSample s3{};'''
func = replace_once(func, acc_anchor, acc_code, 'spatial accumulation')

return_old = '    return os.str();'
return_new = r'''    std::string tonal1ABase = os.str();
    if (tonal1ABase.empty() || tonal1ABase.back() != '}') {
        delete[] tonal1AGrid;
        return tonal1ABase;
    }
    tonal1ABase.pop_back();
    std::ostringstream tonal1AJson;
    tonal1AJson << std::fixed << std::setprecision(8);
    tonal1AJson << tonal1ABase;
    tonal1AJson << ",\"tonalSeparation1A\":{";
    tonal1AJson << "\"schema\":\"m9cam.tonalseparation1a.v1\",";
    tonal1AJson << "\"measurementOnly\":true,\"renderedPixelsModified\":false,";
    tonal1AJson << "\"pixelPath\":\"LEICARB1B_RBANCHOR1A_CONTROL\",";
    tonal1AJson << "\"gridCols\":" << TONAL1A_COLS << ",\"gridRows\":" << TONAL1A_ROWS << ",";
    tonal1AJson << "\"sampleStrideXY\":" << TONAL1A_SAMPLE_STRIDE << ",";
    tonal1AJson << "\"lumaDefinition\":\"BT601_0.299R_0.587G_0.114B\",";
    tonal1AJson << "\"histogramRange\":[0.0," << TONAL1A_HIST_MAX << "],\"histogramBins\":" << TONAL1A_BINS << ",";
    tonal1AJson << "\"stageNames\":[\"cameraInput_postDemosaic_Q14\",\"preSat_postCameraToM9_HSM_TC20\",\"postSAT2_preCurve\",\"postSAT3_preCurve\",\"postCurve02_fromSAT2\",\"postCurve02_fromSAT3\"],";
    tonal1AJson << "\"saturationPolicy\":\"SAT2_and_SAT3_measured_side_by_side_read_only_no_active_bank_assumed\",";
    tonal1AJson << "\"cells\":[";
    for (int ty = 0; ty < TONAL1A_ROWS; ++ty) {
        for (int tx = 0; tx < TONAL1A_COLS; ++tx) {
            const int ci = ty * TONAL1A_COLS + tx;
            if (ci) tonal1AJson << ",";
            const Tonal1ACell& tc = tonal1AGrid[ci];
            tonal1AJson << "{\"x\":" << tx << ",\"y\":" << ty;
            tonal1AJson << ",\"x0Norm\":" << (static_cast<double>(tx) / TONAL1A_COLS);
            tonal1AJson << ",\"x1Norm\":" << (static_cast<double>(tx + 1) / TONAL1A_COLS);
            tonal1AJson << ",\"y0Norm\":" << (static_cast<double>(ty) / TONAL1A_ROWS);
            tonal1AJson << ",\"y1Norm\":" << (static_cast<double>(ty + 1) / TONAL1A_ROWS);
            tonal1AJson << ",\"stages\":[";
            for (int s = 0; s < TONAL1A_STAGES; ++s) {
                if (s) tonal1AJson << ",";
                tonal1AWriteStageJson(tonal1AJson, tc.stage[s]);
            }
            tonal1AJson << "]}";
        }
    }
    tonal1AJson << "]}}";
    delete[] tonal1AGrid;
    return tonal1AJson.str();'''
func = replace_once(func, return_old, return_new, 'JSON append')

c = c[:start] + func + c[ret + len('    return os.str();'):]
CPP.write_text(c)

r = RENDERER.read_text()
# Run the already-read-only native audit for every eligible frame in this diagnostic APK.
r = replace_once(r,
'''            if (skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A) {''',
'''            if (satDomainAuditInputEligible1A) {''',
'force read-only audit for eligible frame')

# Label the diagnostics next to the existing SATDOMAIN metadata; no pixel arithmetic is changed.
r = replace_once(r,
'''            d.put("satDomainAuditReadOnly", true);''',
'''            d.put("satDomainAuditReadOnly", true);\n            d.put("tonalSeparationExperiment", "TONALSEPARATION1A_MEASUREMENT_ONLY");\n            d.put("tonalSeparationRenderedPixelsModified", false);\n            d.put("tonalSeparationPixelPath", "LEICARB1B_RBANCHOR1A_CONTROL");''',
'renderer diagnostic labels')
RENDERER.write_text(r)

print('TONALSEPARATION1A spatial audit applied')
print(' - LEICARB1B/RBANCHOR1A rendered pixel path unchanged')
print(' - existing read-only SAT/CURVE audit runs for every eligible frame')
print(' - 12x8 grid, stride 4, six tonal stages, BT.601 luma quantiles')
print(' - SAT2 and SAT3 measured side-by-side; no active saturation bank assumed')
