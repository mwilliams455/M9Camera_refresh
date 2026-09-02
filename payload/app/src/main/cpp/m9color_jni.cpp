#include <jni.h>
#include <android/bitmap.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <chrono>
#include <thread>
#include <new>
#include <vector>

namespace {

constexpr int RAW_MAX = 16383;
constexpr int LUT_MAX = 2047;
constexpr double HSM_H = 0.25;
constexpr double HSM_S = 0.85;
constexpr double HSM_V = 1.00;

constexpr std::array<int64_t, 9> QE = {
        16754, -7632, -922,
        -3124, 14774, -3458,
        -567, -9579, 18330
};
constexpr std::array<int64_t, 9> QO = {
        18160, -9034, -922,
        -3422, 15080, -3458,
        137, -10264, 18330
};

struct ColorContext {
    std::array<double, 3> cw{};
    std::array<double, 9> camToPp{};
    std::vector<double> hsm;
    std::array<double, 9> ppToM9{};
    std::array<double, 9> adapt50To65{};
    std::array<double, 9> ppToXyz{};
    std::array<double, 9> xyz2Srgb{};
    std::array<uint8_t, 2048> curve{};
    int hueDivisions = 0;
    int satDivisions = 0;
};

inline double clampd(double v, double lo, double hi) {
    const double t = v < hi ? v : hi;
    return lo > t ? lo : t;
}

inline int64_t clipl(int64_t v, int64_t lo, int64_t hi) {
    const int64_t t = v < hi ? v : hi;
    return lo > t ? lo : t;
}

inline uint16_t u16(jshort v) {
    return static_cast<uint16_t>(v);
}

inline void hsv6ToRgbWrapped(double h, double s, double v, double* out) {
    const int i = static_cast<int>(h);
    const double f = h - i;
    const double p = v * (1.0 - s);
    const double q = v * (1.0 - s * f);
    const double t = v * (1.0 - s * (1.0 - f));
    switch (i) {
        case 0: out[0] = v; out[1] = t; out[2] = p; break;
        case 1: out[0] = q; out[1] = v; out[2] = p; break;
        case 2: out[0] = p; out[1] = v; out[2] = t; break;
        case 3: out[0] = p; out[1] = q; out[2] = v; break;
        case 4: out[0] = t; out[1] = p; out[2] = v; break;
        default: out[0] = v; out[1] = p; out[2] = q; break;
    }
}

// Literal PRIMARY2.2 HSMFAST1 arithmetic. Keep operation order aligned with Java.
inline void applyHsm(double r, double g, double b, const ColorContext& ctx, double* out) {
    const double rgMax = r > g ? r : g;
    const double v = rgMax > b ? rgMax : b;
    const double rgMin = r < g ? r : g;
    const double mn = rgMin < b ? rgMin : b;
    const double gap = v - mn;
    double h = 0.0;
    double s = 0.0;
    if (gap > 1e-12) {
        if (r == v) {
            h = (g - b) / gap;
            if (h < 0.0) h += 6.0;
        } else if (g == v) {
            h = 2.0 + (b - r) / gap;
        } else {
            h = 4.0 + (r - g) / gap;
        }
        s = gap / v;
    }

    const int hd = ctx.hueDivisions;
    const int sd = ctx.satDivisions;
    const double hp = h * (static_cast<double>(hd) / 6.0);
    const double sp = s * static_cast<double>(sd - 1);
    int h0 = static_cast<int>(hp);
    int s0 = static_cast<int>(sp);
    if (s0 > sd - 2) s0 = sd - 2;
    int h1 = h0 + 1;
    if (h0 >= hd - 1) {
        h0 = hd - 1;
        h1 = 0;
    }
    const double hf = hp - h0;
    const double sf = sp - s0;
    const double oneMinusHf = 1.0 - hf;
    const double oneMinusSf = 1.0 - sf;
    const int e00 = (h0 * sd + s0) * 3;
    const int e01 = (h1 * sd + s0) * 3;
    const int e10 = e00 + 3;
    const int e11 = e01 + 3;
    const double* hsm = ctx.hsm.data();

    const double a0 = oneMinusHf * hsm[e00] + hf * hsm[e01];
    const double c0 = oneMinusHf * hsm[e10] + hf * hsm[e11];
    const double d0 = oneMinusSf * a0 + sf * c0;
    const double a1 = oneMinusHf * hsm[e00 + 1] + hf * hsm[e01 + 1];
    const double c1 = oneMinusHf * hsm[e10 + 1] + hf * hsm[e11 + 1];
    const double d1 = oneMinusSf * a1 + sf * c1;
    const double a2 = oneMinusHf * hsm[e00 + 2] + hf * hsm[e01 + 2];
    const double c2 = oneMinusHf * hsm[e10 + 2] + hf * hsm[e11 + 2];
    const double d2 = oneMinusSf * a2 + sf * c2;

    double hue = h + HSM_H * d0 * (6.0 / 360.0);
    if (hue < 0.0) hue += 6.0;
    else if (hue >= 6.0) hue -= 6.0;
    const double sat0 = s * (1.0 + HSM_S * (d1 - 1.0));
    const double sat = sat0 < 1.0 ? sat0 : 1.0;
    const double val = clampd(v * (1.0 + HSM_V * (d2 - 1.0)), 0.0, 1.0);
    hsv6ToRgbWrapped(hue, sat, val, out);
}

inline double cameraToSrgbLuma(const jshort* cam, int c, const ColorContext& ctx, double* hsmOut) {
    double r = static_cast<double>(u16(cam[c])) / 65535.0;
    double g = static_cast<double>(u16(cam[c + 1])) / 65535.0;
    double b = static_cast<double>(u16(cam[c + 2])) / 65535.0;
    if (r > ctx.cw[0]) r = ctx.cw[0];
    if (g > ctx.cw[1]) g = ctx.cw[1];
    if (b > ctx.cw[2]) b = ctx.cw[2];

    const double pr0 = ctx.camToPp[0] * r + ctx.camToPp[1] * g + ctx.camToPp[2] * b;
    const double pg0 = ctx.camToPp[3] * r + ctx.camToPp[4] * g + ctx.camToPp[5] * b;
    const double pb0 = ctx.camToPp[6] * r + ctx.camToPp[7] * g + ctx.camToPp[8] * b;
    const double pr = clampd(pr0, 0.0, 1.0);
    const double pg = clampd(pg0, 0.0, 1.0);
    const double pb = clampd(pb0, 0.0, 1.0);
    applyHsm(pr, pg, pb, ctx, hsmOut);

    const double x50 = ctx.ppToXyz[0] * hsmOut[0] + ctx.ppToXyz[1] * hsmOut[1] + ctx.ppToXyz[2] * hsmOut[2];
    const double y50 = ctx.ppToXyz[3] * hsmOut[0] + ctx.ppToXyz[4] * hsmOut[1] + ctx.ppToXyz[5] * hsmOut[2];
    const double z50 = ctx.ppToXyz[6] * hsmOut[0] + ctx.ppToXyz[7] * hsmOut[1] + ctx.ppToXyz[8] * hsmOut[2];
    const double x65 = ctx.adapt50To65[0] * x50 + ctx.adapt50To65[1] * y50 + ctx.adapt50To65[2] * z50;
    const double y65 = ctx.adapt50To65[3] * x50 + ctx.adapt50To65[4] * y50 + ctx.adapt50To65[5] * z50;
    const double z65 = ctx.adapt50To65[6] * x50 + ctx.adapt50To65[7] * y50 + ctx.adapt50To65[8] * z50;
    const double sr = ctx.xyz2Srgb[0] * x65 + ctx.xyz2Srgb[1] * y65 + ctx.xyz2Srgb[2] * z65;
    const double sg = ctx.xyz2Srgb[3] * x65 + ctx.xyz2Srgb[4] * y65 + ctx.xyz2Srgb[5] * z65;
    const double sb = ctx.xyz2Srgb[6] * x65 + ctx.xyz2Srgb[7] * y65 + ctx.xyz2Srgb[8] * z65;
    const double luma = .2126 * sr + .7152 * sg + .0722 * sb;
    return luma > 0.0 ? luma : 0.0;
}

inline double meterWeightForIndex(int idx,
                                  int width,
                                  const double* rowWeights,
                                  const double* colWeights) {
    return rowWeights[idx / width] * colWeights[idx % width];
}

inline void partitionIndicesByValue(std::vector<int>& indices,
                                    size_t lo,
                                    size_t hi,
                                    double pivot,
                                    const std::vector<double>& y,
                                    size_t* ltOut,
                                    size_t* gtOut) {
    size_t lt = lo;
    size_t i = lo;
    size_t gt = hi;
    while (i < gt) {
        const double v = y[static_cast<size_t>(indices[i])];
        if (v < pivot) {
            std::swap(indices[lt], indices[i]);
            ++lt;
            ++i;
        } else if (v > pivot) {
            --gt;
            std::swap(indices[i], indices[gt]);
        } else {
            ++i;
        }
    }
    *ltOut = lt;
    *gtOut = gt;
}

inline double selectValueAtRank(std::vector<int>& indices,
                                const std::vector<double>& y,
                                size_t rank) {
    size_t lo = 0;
    size_t hi = indices.size();
    while (true) {
        if (hi - lo == 1) return y[static_cast<size_t>(indices[lo])];
        const size_t mid = lo + ((hi - lo) >> 1u);
        const double pivot = y[static_cast<size_t>(indices[mid])];
        size_t lt = lo;
        size_t gt = hi;
        partitionIndicesByValue(indices, lo, hi, pivot, y, &lt, &gt);
        if (rank < lt) {
            hi = lt;
        } else if (rank >= gt) {
            lo = gt;
        } else {
            return pivot;
        }
    }
}

void meterTc20WeightedSelectScalar(const ColorContext& ctx,
                                   const jshort* cam,
                                   int pixelCount,
                                   int width,
                                   int height,
                                   const double* rowWeights,
                                   const double* colWeights,
                                   double* statsOut,
                                   int64_t* timingOut) {
    const auto scalarStarted = std::chrono::steady_clock::now();
    thread_local std::vector<double> y;
    thread_local std::vector<int> order;
    thread_local std::vector<int> rankWork;
    y.resize(static_cast<size_t>(pixelCount));
    order.clear();
    if (order.capacity() < static_cast<size_t>(pixelCount)) {
        order.reserve(static_cast<size_t>(pixelCount));
    }
    // PERF3C TC20LUMA8A: cameraToSrgbLuma() is strictly pixel-local. Compute only
    // the frozen H25/HSM -> sRGB-linear luma values in disjoint contiguous ranges.
    // Rebuild `order` afterward in the original ascending pixel-index sequence so the
    // weighted-selection pivoting, comparisons, weight accumulation and P98 ranks see
    // exactly the same input ordering as TC20NATIVE1B.
    const int lumaWorkerCount = std::max(1, std::min(8, pixelCount));
    // `y` is thread_local to the JNI caller. Freeze its populated storage pointer
    // before spawning; child std::threads have distinct TLS instances.
    double* const yBase = y.data();
    const auto lumaStarted = std::chrono::steady_clock::now();
    const auto lumaComputeStarted = lumaStarted;
    std::vector<std::thread> lumaThreads;
    lumaThreads.reserve(static_cast<size_t>(lumaWorkerCount));
    for (int worker = 0; worker < lumaWorkerCount; ++worker) {
        const int p0 = (pixelCount * worker) / lumaWorkerCount;
        const int p1 = (pixelCount * (worker + 1)) / lumaWorkerCount;
        lumaThreads.emplace_back([&, p0, p1]() {
            double hsmLocal[3]{};
            for (int p = p0; p < p1; ++p) {
                const int c = p * 3;
                yBase[static_cast<size_t>(p)] = cameraToSrgbLuma(cam, c, ctx, hsmLocal);
            }
        });
    }
    for (auto& thread : lumaThreads) thread.join();
    const auto lumaComputeEnded = std::chrono::steady_clock::now();

    const auto orderBuildStarted = lumaComputeEnded;
    for (int p = 0; p < pixelCount; ++p) {
        if (y[static_cast<size_t>(p)] > 1e-5) order.push_back(p);
    }
    const auto orderBuildEnded = std::chrono::steady_clock::now();
    const auto lumaEnded = orderBuildEnded;
    timingOut[0] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(lumaEnded - lumaStarted).count());
    timingOut[5] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(lumaComputeEnded - lumaComputeStarted).count());
    timingOut[6] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(orderBuildEnded - orderBuildStarted).count());
    timingOut[7] = static_cast<int64_t>(lumaWorkerCount);

    if (order.empty()) {
        statsOut[0] = 0.0;
        statsOut[1] = 0.0;
        statsOut[2] = 0.0;
        timingOut[1] = 0;
        timingOut[2] = 0;
        timingOut[3] = 0;
        timingOut[4] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(lumaEnded - scalarStarted).count());
        return;
    }

    const auto totalWeightStarted = std::chrono::steady_clock::now();
    double totalWeight = 0.0;
    for (int idx : order) {
        totalWeight += meterWeightForIndex(idx, width, rowWeights, colWeights);
    }
    const auto totalWeightEnded = std::chrono::steady_clock::now();
    timingOut[1] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(totalWeightEnded - totalWeightStarted).count());
    const auto medianStarted = std::chrono::steady_clock::now();
    double targetWeight = totalWeight * .5;
    size_t lo = 0;
    size_t hi = order.size();
    double median = y[static_cast<size_t>(order.back())];
    while (true) {
        if (hi - lo == 1) {
            median = y[static_cast<size_t>(order[lo])];
            break;
        }
        const size_t mid = lo + ((hi - lo) >> 1u);
        const double pivot = y[static_cast<size_t>(order[mid])];
        size_t lt = lo;
        size_t gt = hi;
        partitionIndicesByValue(order, lo, hi, pivot, y, &lt, &gt);

        double lessWeight = 0.0;
        for (size_t i = lo; i < lt; ++i) {
            lessWeight += meterWeightForIndex(order[i], width, rowWeights, colWeights);
        }
        double equalWeight = 0.0;
        for (size_t i = lt; i < gt; ++i) {
            equalWeight += meterWeightForIndex(order[i], width, rowWeights, colWeights);
        }

        if (targetWeight <= lessWeight) {
            hi = lt;
            continue;
        }
        if (targetWeight <= lessWeight + equalWeight) {
            median = pivot;
            break;
        }
        targetWeight -= (lessWeight + equalWeight);
        lo = gt;
    }

    const auto medianEnded = std::chrono::steady_clock::now();
    timingOut[2] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(medianEnded - medianStarted).count());
    const auto p98Started = std::chrono::steady_clock::now();
    const int64_t lowCount = static_cast<int64_t>(pixelCount) - static_cast<int64_t>(order.size());
    const double p = static_cast<double>(pixelCount - 1) * .98;
    double p98 = 0.0;
    if (p >= static_cast<double>(lowCount)) {
        const double pos = p - static_cast<double>(lowCount);
        const size_t last = order.size() - 1u;
        const size_t loRank = std::min(last, static_cast<size_t>(std::max(0.0, std::floor(pos))));
        const size_t hiRank = std::min(last, static_cast<size_t>(std::max(0.0, std::ceil(pos))));
        const double frac = pos - std::floor(pos);
        rankWork.assign(order.begin(), order.end());
        const double vlo = selectValueAtRank(rankWork, y, loRank);
        double vhi = vlo;
        if (hiRank != loRank) {
            rankWork.assign(order.begin(), order.end());
            vhi = selectValueAtRank(rankWork, y, hiRank);
        }
        p98 = vlo + frac * (vhi - vlo);
    }

    const auto p98Ended = std::chrono::steady_clock::now();
    timingOut[3] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(p98Ended - p98Started).count());
    statsOut[0] = median;
    statsOut[1] = p98;
    statsOut[2] = static_cast<double>(order.size());
    timingOut[4] = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(p98Ended - scalarStarted).count());
}

inline void cameraToM9(const jshort* cam, int c, const ColorContext& ctx, double* hsmOut, double* m9Out) {
    double r = static_cast<double>(u16(cam[c])) / 65535.0;
    double g = static_cast<double>(u16(cam[c + 1])) / 65535.0;
    double b = static_cast<double>(u16(cam[c + 2])) / 65535.0;
    if (r > ctx.cw[0]) r = ctx.cw[0];
    if (g > ctx.cw[1]) g = ctx.cw[1];
    if (b > ctx.cw[2]) b = ctx.cw[2];

    const double pr0 = ctx.camToPp[0] * r + ctx.camToPp[1] * g + ctx.camToPp[2] * b;
    const double pg0 = ctx.camToPp[3] * r + ctx.camToPp[4] * g + ctx.camToPp[5] * b;
    const double pb0 = ctx.camToPp[6] * r + ctx.camToPp[7] * g + ctx.camToPp[8] * b;
    const double pr = clampd(pr0, 0.0, 1.0);
    const double pg = clampd(pg0, 0.0, 1.0);
    const double pb = clampd(pb0, 0.0, 1.0);
    applyHsm(pr, pg, pb, ctx, hsmOut);

    const double hr = hsmOut[0];
    const double hg = hsmOut[1];
    const double hb = hsmOut[2];
    const double r0 = ctx.ppToM9[0] * hr + ctx.ppToM9[1] * hg + ctx.ppToM9[2] * hb;
    const double g0 = ctx.ppToM9[3] * hr + ctx.ppToM9[4] * hg + ctx.ppToM9[5] * hb;
    const double b0 = ctx.ppToM9[6] * hr + ctx.ppToM9[7] * hg + ctx.ppToM9[8] * hb;
    m9Out[0] = r0 > 0.0 ? r0 : 0.0;
    m9Out[1] = g0 > 0.0 ? g0 : 0.0;
    m9Out[2] = b0 > 0.0 ? b0 : 0.0;
}

// Return PRIMARY2.2 diagnostics: bit 2 = M06/even branch, low two bits = edge count.
inline int m9CurvePixel(const double* m9, double gain, const ColorContext& ctx, int* rgbOut) {
    const int64_t r = clipl(static_cast<int64_t>(std::rint(m9[0] * gain * RAW_MAX)), 0, RAW_MAX);
    const int64_t g = clipl(static_cast<int64_t>(std::rint(m9[1] * gain * RAW_MAX)), 0, RAW_MAX);
    const int64_t b = clipl(static_cast<int64_t>(std::rint(m9[2] * gain * RAW_MAX)), 0, RAW_MAX);
    const bool evenBranch = r >= g;
    const auto& q = evenBranch ? QE : QO;
    const int64_t a0 = q[0] * r + q[1] * g + q[2] * b;
    const int64_t a1 = q[3] * r + q[4] * g + q[5] * b;
    const int64_t a2 = q[6] * r + q[7] * g + q[8] * b;
    const int i0 = static_cast<int>(clipl(a0 >> 16, 0, LUT_MAX));
    const int i1 = static_cast<int>(clipl(a1 >> 16, 0, LUT_MAX));
    const int i2 = static_cast<int>(clipl(a2 >> 16, 0, LUT_MAX));
    const int rr = ctx.curve[i0];
    const int gg = ctx.curve[i1];
    const int bb = ctx.curve[i2];
    rgbOut[0] = rr;
    rgbOut[1] = gg;
    rgbOut[2] = bb;
    int edge = 0;
    if (rr == 0 || rr == 255) edge++;
    if (gg == 0 || gg == 255) edge++;
    if (bb == 0 || bb == 255) edge++;
    return (evenBranch ? 4 : 0) | edge;
}

inline int roundU8(double v) {
    const double unit = clampd(v / 255.0, 0.0, 1.0);
    return static_cast<int>(unit * 255.0 + 0.5);
}

inline jint packArgb(int r, int g, int b) {
    const uint32_t bits = 0xff000000u | (static_cast<uint32_t>(r) << 16)
            | (static_cast<uint32_t>(g) << 8) | static_cast<uint32_t>(b);
    return static_cast<jint>(bits);
}

void renderStripScalar(const ColorContext& ctx,
                       const jshort* cam,
                       int pixelCount,
                       int width,
                       jint* argb,
                       double gain,
                       double tgCbGain,
                       double tgCrGain,
                       int64_t* statsOut) {
    int64_t even = 0;
    int64_t edge = 0;
    int64_t nearWhite = 0;
    const int rows = pixelCount / width;
    const int w2 = width - (width & 1);
    double hsm0[3]{};
    double hsm1[3]{};
    double m90[3]{};
    double m91[3]{};
    int rgb0[3]{};
    int rgb1[3]{};

    for (int sy = 0; sy < rows; ++sy) {
        const int stripRow = sy * width;
        for (int x = 0; x < w2; x += 2) {
            const int p0 = stripRow + x;
            const int p1 = p0 + 1;
            const int c0 = p0 * 3;
            const int c1 = p1 * 3;

            cameraToM9(cam, c0, ctx, hsm0, m90);
            cameraToM9(cam, c1, ctx, hsm1, m91);
            const int f0 = m9CurvePixel(m90, gain, ctx, rgb0);
            const int f1 = m9CurvePixel(m91, gain, ctx, rgb1);
            even += (f0 >> 2) & 1;
            even += (f1 >> 2) & 1;
            edge += f0 & 3;
            edge += f1 & 3;

            const int64_t r0 = rgb0[0], g0 = rgb0[1], b0 = rgb0[2];
            const int64_t r1 = rgb1[0], g1 = rgb1[1], b1 = rgb1[2];
            const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;
            const int64_t yy1 = (4899 * r1 + 9617 * g1 + 1868 * b1) >> 14;
            const int64_t rs = r0 + r1;
            const int64_t gs = g0 + g1;
            const int64_t bs = b0 + b1;
            const int64_t cbS = ((((-2765 * rs + 1) >> 1) - ((5427 * gs) >> 1)
                    + ((8192 * bs) >> 1))) >> 14;
            const int64_t crS = ((((8192 * rs) >> 1) - ((6860 * gs) >> 1)
                    - ((1332 * bs) >> 1))) >> 14;
            const int cb = static_cast<int>((cbS + 128) & 0xff) - 128;
            const int cr = static_cast<int>((crS + 128) & 0xff) - 128;
            const double cbModern = cb < 0 ? cb * tgCbGain : static_cast<double>(cb);
            const double crModern = cr < 0 ? cr * tgCrGain : static_cast<double>(cr);
            const int rr0 = roundU8(yy0 + 1.402 * crModern);
            const int gg0 = roundU8(yy0 - .344136 * cbModern - .714136 * crModern);
            const int bb0 = roundU8(yy0 + 1.772 * cbModern);
            const int rr1 = roundU8(yy1 + 1.402 * crModern);
            const int gg1 = roundU8(yy1 - .344136 * cbModern - .714136 * crModern);
            const int bb1 = roundU8(yy1 + 1.772 * cbModern);
            argb[p0] = packArgb(rr0, gg0, bb0);
            argb[p1] = packArgb(rr1, gg1, bb1);
            const int max0 = std::max(rr0, std::max(gg0, bb0));
            const int max1 = std::max(rr1, std::max(gg1, bb1));
            if (max0 >= 250) nearWhite++;
            if (max1 >= 250) nearWhite++;
        }
        if (w2 != width) {
            const int p = stripRow + w2;
            const int c = p * 3;
            cameraToM9(cam, c, ctx, hsm0, m90);
            const int f = m9CurvePixel(m90, gain, ctx, rgb0);
            even += (f >> 2) & 1;
            edge += f & 3;
            const int rr = rgb0[0], gg = rgb0[1], bb = rgb0[2];
            argb[p] = packArgb(rr, gg, bb);
            if (std::max(rr, std::max(gg, bb)) >= 250) nearWhite++;
        }
    }
    statsOut[0] = even;
    statsOut[1] = edge;
    statsOut[2] = nearWhite;
}

// NORMNATIVE1A: PRIMARY2's exact Java normalization formula, moved into native C++.
// Input is explicitly decoded as little-endian RAW16 bytes so direct-buffer alignment and
// host endianness cannot silently change the source values.  CFA plane selection, clipping
// histogram semantics and float operation order mirror normalizeRange() exactly.
struct NormalizeNativeResult {
    uint64_t clipped = 0;
};

inline void normalizeRangeNative(const uint8_t* rawBytes,
                                 jshort* normalized,
                                 int width,
                                 int y0,
                                 int y1,
                                 const std::array<float, 4>& black,
                                 int whiteLevel,
                                 uint64_t* histogram,
                                 uint64_t* clippedOut) {
    uint64_t clipped = 0;
    for (int y = y0; y < y1; ++y) {
        const int row = y * width;
        const int py = y & 1;
        for (int x = 0; x < width; ++x) {
            const int i = row + x;
            const int plane = py * 2 + (x & 1);
            const size_t byteIndex = static_cast<size_t>(i) * 2u;
            const uint16_t rv = static_cast<uint16_t>(rawBytes[byteIndex])
                    | static_cast<uint16_t>(static_cast<uint16_t>(rawBytes[byteIndex + 1]) << 8u);
            if (rv >= static_cast<uint16_t>(whiteLevel)) {
                ++clipped;
            } else {
                ++histogram[static_cast<size_t>(plane) * static_cast<size_t>(whiteLevel) + rv];
            }

            const float bl = black[static_cast<size_t>(plane)];
            const float denomRaw = static_cast<float>(whiteLevel) - bl;
            const float denom = 1.0f > denomRaw ? 1.0f : denomRaw;
            float v = (static_cast<float>(rv) - bl) / denom;
            if (v < 0.0f) v = 0.0f;
            if (v > 1.0f) v = 1.0f;
            const float scaled = v * 65535.0f + 0.5f;
            const int nv = static_cast<int>(std::floor(static_cast<double>(scaled)));
            normalized[i] = static_cast<jshort>(static_cast<uint16_t>(nv));
        }
    }
    *clippedOut = clipped;
}

// ORIENT1A: rearrange completed RGB pixels only after the exact source-horizontal
// BT.601 4:2:2 pair kernel has finished.  The output remains a strip-sized array, but
// for 90/270 degrees it is row-major for a destination rectangle of rows x sourceWidth.
// This keeps chroma pairing in source space while eliminating Android's full-frame rotate.
void orientCompletedStrip(const jint* sourceArgb,
                          jint* destinationArgb,
                          int rows,
                          int width,
                          int cameraRotation) {
    int rotation = cameraRotation % 360;
    if (rotation < 0) rotation += 360;
    if (rotation == 0) {
        std::copy(sourceArgb, sourceArgb + static_cast<size_t>(rows) * width, destinationArgb);
        return;
    }
    if (rotation == 90) {
        for (int y = 0; y < rows; ++y) {
            const int sourceRow = y * width;
            const int destX = rows - 1 - y;
            for (int x = 0; x < width; ++x) {
                destinationArgb[x * rows + destX] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    if (rotation == 180) {
        for (int y = 0; y < rows; ++y) {
            const int sourceRow = y * width;
            const int destRow = (rows - 1 - y) * width;
            for (int x = 0; x < width; ++x) {
                destinationArgb[destRow + (width - 1 - x)] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    if (rotation == 270) {
        for (int y = 0; y < rows; ++y) {
            const int sourceRow = y * width;
            for (int x = 0; x < width; ++x) {
                destinationArgb[(width - 1 - x) * rows + y] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    // Unknown rotation preserves the source layout just like the old Java orient() default.
    std::copy(sourceArgb, sourceArgb + static_cast<size_t>(rows) * width, destinationArgb);
}

// PERF3G ORIENTFUSE8A: exact ORIENT1A mapping for one disjoint source-row range.
// Each COLOR8A worker calls this only after renderStripScalar has completed its own rows.
// The destination regions are disjoint for 0/90/180/270, so workers can copy concurrently
// without changing source-horizontal BT.601 pair math or any completed ARGB pixel value.
void orientCompletedSubrange(const jint* sourceArgb,
                             jint* destinationArgb,
                             int rows,
                             int width,
                             int y0,
                             int y1,
                             int cameraRotation) {
    int rotation = cameraRotation % 360;
    if (rotation < 0) rotation += 360;
    if (rotation == 0) {
        const size_t begin = static_cast<size_t>(y0) * static_cast<size_t>(width);
        const size_t end = static_cast<size_t>(y1) * static_cast<size_t>(width);
        std::copy(sourceArgb + begin, sourceArgb + end, destinationArgb + begin);
        return;
    }
    if (rotation == 90) {
        for (int y = y0; y < y1; ++y) {
            const int sourceRow = y * width;
            const int destX = rows - 1 - y;
            for (int x = 0; x < width; ++x) {
                destinationArgb[x * rows + destX] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    if (rotation == 180) {
        for (int y = y0; y < y1; ++y) {
            const int sourceRow = y * width;
            const int destRow = (rows - 1 - y) * width;
            for (int x = 0; x < width; ++x) {
                destinationArgb[destRow + (width - 1 - x)] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    if (rotation == 270) {
        for (int y = y0; y < y1; ++y) {
            const int sourceRow = y * width;
            for (int x = 0; x < width; ++x) {
                destinationArgb[(width - 1 - x) * rows + y] = sourceArgb[sourceRow + x];
            }
        }
        return;
    }
    const size_t begin = static_cast<size_t>(y0) * static_cast<size_t>(width);
    const size_t end = static_cast<size_t>(y1) * static_cast<size_t>(width);
    std::copy(sourceArgb + begin, sourceArgb + end, destinationArgb + begin);
}

// PERF3I BITMAPDIRECT1A: component-exact equivalent of Java Bitmap.setPixels() for
// mutable ARGB_8888 / native RGBA_8888 storage. The scalar renderer still produces
// Java-style 0xAARRGGBB jint pixels; this helper writes their R,G,B,A components
// into the AndroidBitmap row/stride layout after all photographic math is complete.
inline void storeArgbAsRgba8888(uint8_t* destination, jint argb) {
    destination[0] = static_cast<uint8_t>((static_cast<uint32_t>(argb) >> 16) & 0xffu);
    destination[1] = static_cast<uint8_t>((static_cast<uint32_t>(argb) >> 8) & 0xffu);
    destination[2] = static_cast<uint8_t>(static_cast<uint32_t>(argb) & 0xffu);
    destination[3] = static_cast<uint8_t>((static_cast<uint32_t>(argb) >> 24) & 0xffu);
}

void writeCompletedSubrangeToBitmap(const jint* sourceArgb,
                                    uint8_t* bitmapPixels,
                                    uint32_t bitmapStride,
                                    int blockRows,
                                    int width,
                                    int blockY0,
                                    int sourceHeight,
                                    int y0,
                                    int y1,
                                    int cameraRotation) {
    int rotation = cameraRotation % 360;
    if (rotation < 0) rotation += 360;
    for (int y = y0; y < y1; ++y) {
        const int sourceRow = y * width;
        const int globalY = blockY0 + y;
        for (int x = 0; x < width; ++x) {
            int dx;
            int dy;
            if (rotation == 90) {
                dx = sourceHeight - 1 - globalY;
                dy = x;
            } else if (rotation == 180) {
                dx = width - 1 - x;
                dy = sourceHeight - 1 - globalY;
            } else if (rotation == 270) {
                dx = globalY;
                dy = width - 1 - x;
            } else {
                dx = x;
                dy = globalY;
            }
            uint8_t* destination = bitmapPixels
                    + static_cast<size_t>(dy) * static_cast<size_t>(bitmapStride)
                    + static_cast<size_t>(dx) * 4u;
            storeArgbAsRgba8888(destination, sourceArgb[sourceRow + x]);
        }
    }
}

void throwIllegalArgument(JNIEnv* env, const char* message) {
    jclass cls = env->FindClass("java/lang/IllegalArgumentException");
    if (cls) env->ThrowNew(cls, message);
}

void throwIllegalState(JNIEnv* env, const char* message) {
    jclass cls = env->FindClass("java/lang/IllegalStateException");
    if (cls) env->ThrowNew(cls, message);
}

}  // namespace

extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_createContext(
        JNIEnv* env, jclass,
        jdoubleArray cwArray,
        jdoubleArray camToPpArray,
        jdoubleArray hsmArray,
        jdoubleArray ppToM9Array,
        jdoubleArray adapt50To65Array,
        jdoubleArray ppToXyzArray,
        jdoubleArray xyz2SrgbArray,
        jbyteArray curveArray,
        jint hueDivisions,
        jint satDivisions) {
    if (!cwArray || !camToPpArray || !hsmArray || !ppToM9Array || !adapt50To65Array
            || !ppToXyzArray || !xyz2SrgbArray || !curveArray) {
        throwIllegalArgument(env, "M9 JNI context arrays must be non-null");
        return 0;
    }
    const jsize cwLen = env->GetArrayLength(cwArray);
    const jsize camLen = env->GetArrayLength(camToPpArray);
    const jsize hsmLen = env->GetArrayLength(hsmArray);
    const jsize m9Len = env->GetArrayLength(ppToM9Array);
    const jsize adaptLen = env->GetArrayLength(adapt50To65Array);
    const jsize ppXyzLen = env->GetArrayLength(ppToXyzArray);
    const jsize xyzSrgbLen = env->GetArrayLength(xyz2SrgbArray);
    const jsize curveLen = env->GetArrayLength(curveArray);
    if (cwLen != 3 || camLen != 9 || m9Len != 9 || adaptLen != 9 || ppXyzLen != 9
            || xyzSrgbLen != 9 || curveLen != 2048
            || hueDivisions < 2 || satDivisions < 2
            || hsmLen != hueDivisions * satDivisions * 3) {
        throwIllegalArgument(env, "M9 JNI context dimensions do not match PRIMARY2.2 calibration");
        return 0;
    }

    auto* ctx = new (std::nothrow) ColorContext();
    if (!ctx) {
        throwIllegalState(env, "M9 JNI context allocation failed");
        return 0;
    }
    ctx->hueDivisions = hueDivisions;
    ctx->satDivisions = satDivisions;
    ctx->hsm.resize(static_cast<size_t>(hsmLen));

    env->GetDoubleArrayRegion(cwArray, 0, 3, ctx->cw.data());
    env->GetDoubleArrayRegion(camToPpArray, 0, 9, ctx->camToPp.data());
    env->GetDoubleArrayRegion(hsmArray, 0, hsmLen, ctx->hsm.data());
    env->GetDoubleArrayRegion(ppToM9Array, 0, 9, ctx->ppToM9.data());
    env->GetDoubleArrayRegion(adapt50To65Array, 0, 9, ctx->adapt50To65.data());
    env->GetDoubleArrayRegion(ppToXyzArray, 0, 9, ctx->ppToXyz.data());
    env->GetDoubleArrayRegion(xyz2SrgbArray, 0, 9, ctx->xyz2Srgb.data());
    std::array<jbyte, 2048> curveSigned{};
    env->GetByteArrayRegion(curveArray, 0, 2048, curveSigned.data());
    if (env->ExceptionCheck()) {
        delete ctx;
        return 0;
    }
    for (size_t i = 0; i < ctx->curve.size(); ++i) {
        ctx->curve[i] = static_cast<uint8_t>(curveSigned[i]);
    }
    return reinterpret_cast<jlong>(ctx);
}

extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_destroyContext(
        JNIEnv*, jclass, jlong handle) {
    delete reinterpret_cast<ColorContext*>(handle);
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect(
        JNIEnv* env, jclass,
        jobject rawBuffer,
        jint pixelCount,
        jint width,
        jint height,
        jfloatArray blackArray,
        jint whiteLevel,
        jint workers,
        jshortArray normArray,
        jlongArray histogramArray,
        jlongArray statsArray) {
    if (!rawBuffer || !normArray || !histogramArray || !statsArray
            || pixelCount <= 0 || width <= 0 || height <= 0
            || pixelCount != width * height || whiteLevel < 2 || workers <= 0) {
        throwIllegalArgument(env, "Invalid M9 NORMNATIVE1A arguments");
        return 0;
    }
    auto* rawBytes = static_cast<uint8_t*>(env->GetDirectBufferAddress(rawBuffer));
    const jlong rawCapacity = env->GetDirectBufferCapacity(rawBuffer);
    const jlong expectedBytes = static_cast<jlong>(pixelCount) * 2LL;
    if (!rawBytes || rawCapacity < expectedBytes) {
        throwIllegalArgument(env, "M9 NORMNATIVE1A requires direct RAW ByteBuffer with full frame capacity");
        return 0;
    }
    if (env->GetArrayLength(normArray) < pixelCount
            || env->GetArrayLength(histogramArray) < 4 * whiteLevel
            || env->GetArrayLength(statsArray) < 3) {
        throwIllegalArgument(env, "M9 NORMNATIVE1A output buffers are too small");
        return 0;
    }

    std::array<float, 4> black = {64.0f, 64.0f, 64.0f, 64.0f};
    if (blackArray && env->GetArrayLength(blackArray) >= 4) {
        env->GetFloatArrayRegion(blackArray, 0, 4, black.data());
        if (env->ExceptionCheck()) return 0;
    }

    const int workerCount = std::max(1, std::min(static_cast<int>(workers), static_cast<int>(height)));
    const size_t histogramBins = static_cast<size_t>(4) * static_cast<size_t>(whiteLevel);

    // The outer M9 render queue is single-worker. Reuse the 25 MB normalized scratch there
    // rather than allocating/freeing a native frame buffer on every shutter press.
    thread_local std::vector<jshort> normalizedScratch;
    thread_local std::vector<uint64_t> workerHistograms;
    thread_local std::vector<uint64_t> workerClipped;
    normalizedScratch.resize(static_cast<size_t>(pixelCount));
    workerHistograms.assign(histogramBins * static_cast<size_t>(workerCount), 0u);
    workerClipped.assign(static_cast<size_t>(workerCount), 0u);

    jshort* normalizedOut = normalizedScratch.data();
    uint64_t* histogramBase = workerHistograms.data();
    uint64_t* clippedBase = workerClipped.data();
    const auto computeStart = std::chrono::steady_clock::now();
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (height * worker) / workerCount;
        const int y1 = (height * (worker + 1)) / workerCount;
        threads.emplace_back([=, &black]() {
            normalizeRangeNative(rawBytes, normalizedOut, width, y0, y1, black, whiteLevel,
                                 histogramBase + static_cast<size_t>(worker) * histogramBins,
                                 &clippedBase[static_cast<size_t>(worker)]);
        });
    }
    for (auto& thread : threads) thread.join();

    std::vector<jlong> flatHistogram(histogramBins, 0);
    uint64_t clipped = 0;
    for (int worker = 0; worker < workerCount; ++worker) {
        clipped += workerClipped[static_cast<size_t>(worker)];
        const uint64_t* local = workerHistograms.data() + static_cast<size_t>(worker) * histogramBins;
        for (size_t bin = 0; bin < histogramBins; ++bin) {
            flatHistogram[bin] += static_cast<jlong>(local[bin]);
        }
    }
    const auto computeEnd = std::chrono::steady_clock::now();

    const auto outputStart = std::chrono::steady_clock::now();
    env->SetShortArrayRegion(normArray, 0, pixelCount, normalizedScratch.data());
    if (env->ExceptionCheck()) return 0;
    const auto outputEnd = std::chrono::steady_clock::now();
    env->SetLongArrayRegion(histogramArray, 0, static_cast<jsize>(histogramBins), flatHistogram.data());
    if (env->ExceptionCheck()) return 0;

    const jlong stats[3] = {
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(computeEnd - computeStart).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(outputEnd - outputStart).count()),
            static_cast<jlong>(workerCount)
    };
    env->SetLongArrayRegion(statsArray, 0, 3, stats);
    return static_cast<jlong>(clipped);
}

extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelect(
        JNIEnv* env, jclass,
        jlong handle,
        jshortArray camArray,
        jint pixelCount,
        jint width,
        jint height,
        jdoubleArray rowWeightsArray,
        jdoubleArray colWeightsArray,
        jdoubleArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    if (!ctx || !camArray || !rowWeightsArray || !colWeightsArray || !statsArray
            || pixelCount < 0 || width <= 0 || height <= 0 || pixelCount != width * height) {
        throwIllegalArgument(env, "Invalid M9 TC20NATIVE1B-ORIENT1A meter arguments");
        return;
    }
    const jsize camLen = env->GetArrayLength(camArray);
    const jsize rowLen = env->GetArrayLength(rowWeightsArray);
    const jsize colLen = env->GetArrayLength(colWeightsArray);
    const jsize statsLen = env->GetArrayLength(statsArray);
    if (camLen < pixelCount * 3 || rowLen != height || colLen != width || statsLen < 3) {
        throwIllegalArgument(env, "M9 TC20NATIVE1B-ORIENT1A meter buffers have invalid dimensions");
        return;
    }

    // Reuse meter scratch on the single primary-render worker to avoid ~30 MB of
    // allocator churn between consecutive captures. This does not change TC20 math.
    thread_local std::vector<jshort> cam;
    thread_local std::vector<double> rowWeights;
    thread_local std::vector<double> colWeights;
    const auto scratchStarted = std::chrono::steady_clock::now();
    cam.resize(static_cast<size_t>(pixelCount) * 3u);
    rowWeights.resize(static_cast<size_t>(height));
    colWeights.resize(static_cast<size_t>(width));
    const auto scratchEnded = std::chrono::steady_clock::now();
    const auto copyStarted = std::chrono::steady_clock::now();
    env->GetShortArrayRegion(camArray, 0, static_cast<jsize>(cam.size()), cam.data());
    if (env->ExceptionCheck()) return;
    env->GetDoubleArrayRegion(rowWeightsArray, 0, height, rowWeights.data());
    if (env->ExceptionCheck()) return;
    env->GetDoubleArrayRegion(colWeightsArray, 0, width, colWeights.data());
    if (env->ExceptionCheck()) return;
    const auto copyEnded = std::chrono::steady_clock::now();

    double stats[3]{};
    int64_t timings[8]{};
    meterTc20WeightedSelectScalar(*ctx, cam.data(), pixelCount, width, height,
                            rowWeights.data(), colWeights.data(), stats, timings);
    const jdouble out[13] = {
            stats[0], stats[1], stats[2],
            static_cast<jdouble>(std::chrono::duration_cast<std::chrono::nanoseconds>(scratchEnded - scratchStarted).count()),
            static_cast<jdouble>(std::chrono::duration_cast<std::chrono::nanoseconds>(copyEnded - copyStarted).count()),
            static_cast<jdouble>(timings[0]), static_cast<jdouble>(timings[1]),
            static_cast<jdouble>(timings[2]), static_cast<jdouble>(timings[3]),
            static_cast<jdouble>(timings[4]), static_cast<jdouble>(timings[5]),
            static_cast<jdouble>(timings[6]), static_cast<jdouble>(timings[7])
    };
    if (statsLen >= 13) {
        env->SetDoubleArrayRegion(statsArray, 0, 13, out);
    } else {
        // Retain compatibility with the existing three-value host parity harness.
        env->SetDoubleArrayRegion(statsArray, 0, 3, out);
    }
}

// PERF3H CVDIRECT1A: exact TC20 path reading packed CV_16UC3 storage directly.
// Java validates Mat continuity/type/stride and keeps the Mat alive for this call.
extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelectDirect(
        JNIEnv* env, jclass,
        jlong handle,
        jlong camAddress,
        jint pixelCount,
        jint width,
        jint height,
        jdoubleArray rowWeightsArray,
        jdoubleArray colWeightsArray,
        jdoubleArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    const auto* cam = reinterpret_cast<const jshort*>(static_cast<uintptr_t>(camAddress));
    if (!ctx || !cam || !rowWeightsArray || !colWeightsArray || !statsArray
            || pixelCount < 0 || width <= 0 || height <= 0 || pixelCount != width * height) {
        throwIllegalArgument(env, "Invalid M9 PERF3H direct TC20 arguments");
        return;
    }
    const jsize rowLen = env->GetArrayLength(rowWeightsArray);
    const jsize colLen = env->GetArrayLength(colWeightsArray);
    const jsize statsLen = env->GetArrayLength(statsArray);
    if (rowLen != height || colLen != width || statsLen < 3) {
        throwIllegalArgument(env, "M9 PERF3H direct TC20 buffers have invalid dimensions");
        return;
    }

    thread_local std::vector<double> rowWeights;
    thread_local std::vector<double> colWeights;
    const auto scratchStarted = std::chrono::steady_clock::now();
    rowWeights.resize(static_cast<size_t>(height));
    colWeights.resize(static_cast<size_t>(width));
    const auto scratchEnded = std::chrono::steady_clock::now();
    const auto copyStarted = std::chrono::steady_clock::now();
    env->GetDoubleArrayRegion(rowWeightsArray, 0, height, rowWeights.data());
    if (env->ExceptionCheck()) return;
    env->GetDoubleArrayRegion(colWeightsArray, 0, width, colWeights.data());
    if (env->ExceptionCheck()) return;
    const auto copyEnded = std::chrono::steady_clock::now();

    double stats[3]{};
    int64_t timings[8]{};
    meterTc20WeightedSelectScalar(*ctx, cam, pixelCount, width, height,
                            rowWeights.data(), colWeights.data(), stats, timings);
    const jdouble out[13] = {
            stats[0], stats[1], stats[2],
            static_cast<jdouble>(std::chrono::duration_cast<std::chrono::nanoseconds>(scratchEnded - scratchStarted).count()),
            static_cast<jdouble>(std::chrono::duration_cast<std::chrono::nanoseconds>(copyEnded - copyStarted).count()),
            static_cast<jdouble>(timings[0]), static_cast<jdouble>(timings[1]),
            static_cast<jdouble>(timings[2]), static_cast<jdouble>(timings[3]),
            static_cast<jdouble>(timings[4]), static_cast<jdouble>(timings[5]),
            static_cast<jdouble>(timings[6]), static_cast<jdouble>(timings[7])
    };
    if (statsLen >= 13) env->SetDoubleArrayRegion(statsArray, 0, 13, out);
    else env->SetDoubleArrayRegion(statsArray, 0, 3, out);
}

extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderStrip(
        JNIEnv* env, jclass,
        jlong handle,
        jshortArray camArray,
        jint pixelCount,
        jint width,
        jintArray argbArray,
        jdouble gain,
        jdouble tgCbGain,
        jdouble tgCrGain,
        jint cameraRotation,
        jlongArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    if (!ctx || !camArray || !argbArray || !statsArray || pixelCount < 0 || width <= 0
            || (pixelCount % width) != 0) {
        throwIllegalArgument(env, "Invalid M9 JNI strip arguments");
        return;
    }
    const jsize camLen = env->GetArrayLength(camArray);
    const jsize argbLen = env->GetArrayLength(argbArray);
    const jsize statsLen = env->GetArrayLength(statsArray);
    if (camLen < pixelCount * 3 || argbLen < pixelCount || statsLen < 3) {
        throwIllegalArgument(env, "M9 JNI strip buffers are too small");
        return;
    }

    // FIX4: do not hold ART primitive arrays in a JNI critical region while running the
    // full H25/HSM strip kernel.  Each Java colour worker maps to one native thread, so
    // thread_local scratch amortizes allocation while Get/SetArrayRegion keeps GC free to
    // move the managed arrays during the relatively long scalar render.
    thread_local std::vector<jshort> camScratch;
    thread_local std::vector<jint> argbScratch;
    thread_local std::vector<jint> orientedScratch;
    const size_t camCount = static_cast<size_t>(pixelCount) * 3u;
    const size_t outCount = static_cast<size_t>(pixelCount);
    camScratch.resize(camCount);
    argbScratch.resize(outCount);
    orientedScratch.resize(outCount);

    env->GetShortArrayRegion(camArray, 0, static_cast<jsize>(camCount), camScratch.data());
    if (env->ExceptionCheck()) return;

    int64_t statsNative[3]{};
    renderStripScalar(*ctx, camScratch.data(), pixelCount, width, argbScratch.data(),
                      gain, tgCbGain, tgCrGain, statsNative);

    const int rows = pixelCount / width;
    orientCompletedStrip(argbScratch.data(), orientedScratch.data(), rows, width, cameraRotation);
    env->SetIntArrayRegion(argbArray, 0, pixelCount, orientedScratch.data());
    if (env->ExceptionCheck()) return;
    const jlong stats[3] = {static_cast<jlong>(statsNative[0]), static_cast<jlong>(statsNative[1]), static_cast<jlong>(statsNative[2])};
    env->SetLongArrayRegion(statsArray, 0, 3, stats);
}
extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallel(
        JNIEnv* env, jclass,
        jlong handle,
        jshortArray camArray,
        jint pixelCount,
        jint width,
        jintArray argbArray,
        jdouble gain,
        jdouble tgCbGain,
        jdouble tgCrGain,
        jint cameraRotation,
        jint workers,
        jlongArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    if (!ctx || !camArray || !argbArray || !statsArray || pixelCount < 0 || width <= 0
            || (pixelCount % width) != 0 || workers <= 0) {
        throwIllegalArgument(env, "Invalid M9 COLORNATIVE2A block arguments");
        return;
    }
    const jsize camLen = env->GetArrayLength(camArray);
    const jsize argbLen = env->GetArrayLength(argbArray);
    const jsize statsLen = env->GetArrayLength(statsArray);
    if (camLen < pixelCount * 3 || argbLen < pixelCount || statsLen < 12) {
        throwIllegalArgument(env, "M9 COLORNATIVE2A block buffers are too small");
        return;
    }

    // Deliberately retain Get/SetArrayRegion rather than pinning ART primitive arrays for
    // the full scalar render. This preserves FIX4's GC-safety property while reducing the
    // 12 MP colour path from 128 JNI calls to eight 384-row calls.
    const auto nativeStarted = std::chrono::steady_clock::now();
    thread_local std::vector<jshort> camScratch;
    thread_local std::vector<jint> argbScratch;
    thread_local std::vector<jint> orientedScratch;
    const size_t camCount = static_cast<size_t>(pixelCount) * 3u;
    const size_t outCount = static_cast<size_t>(pixelCount);
    const auto scratchStarted = std::chrono::steady_clock::now();
    camScratch.resize(camCount);
    argbScratch.resize(outCount);
    orientedScratch.resize(outCount);
    const auto scratchEnded = std::chrono::steady_clock::now();

    const auto inputCopyStarted = std::chrono::steady_clock::now();
    env->GetShortArrayRegion(camArray, 0, static_cast<jsize>(camCount), camScratch.data());
    if (env->ExceptionCheck()) return;
    const auto inputCopyEnded = std::chrono::steady_clock::now();

    const int rows = pixelCount / width;
    const int workerCount = std::max(1, std::min(static_cast<int>(workers), rows));
    std::vector<std::array<int64_t, 3>> workerStats(static_cast<size_t>(workerCount));
    std::vector<int64_t> workerElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> orientationElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> combinedElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));

    // COLORNATIVE2A FIX1: camScratch/argbScratch/orientedScratch are thread_local to the JNI caller.
    // Child std::threads have distinct, empty thread_local vector instances, so referring
    // to camScratch.data()/argbScratch.data() inside the worker lambda resolves to null on
    // those child threads. Freeze the populated caller-thread storage pointers before
    // spawning workers, then capture the ordinary pointers by value. The vectors are not
    // resized until every worker has joined, so these addresses remain stable for the call.
    const jshort* const camBase = camScratch.data();
    jint* const argbBase = argbScratch.data();
    jint* const orientedBase = orientedScratch.data();

    const auto workerWallStarted = std::chrono::steady_clock::now();
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (rows * worker) / workerCount;
        const int y1 = (rows * (worker + 1)) / workerCount;
        threads.emplace_back([&, worker, y0, y1, camBase, argbBase, orientedBase]() {
            const int localRows = y1 - y0;
            const int localPixels = localRows * width;
            const size_t pixelOffset = static_cast<size_t>(y0) * static_cast<size_t>(width);
            const size_t camOffset = pixelOffset * 3u;
            const auto started = std::chrono::steady_clock::now();
            renderStripScalar(*ctx,
                              camBase + camOffset,
                              localPixels,
                              width,
                              argbBase + pixelOffset,
                              gain, tgCbGain, tgCrGain,
                              workerStats[static_cast<size_t>(worker)].data());
            const auto renderEnded = std::chrono::steady_clock::now();
            // ORIENTFUSE8A moves only completed ARGB pixels. Each worker owns a disjoint
            // source-row range and therefore a disjoint destination region for every
            // supported rotation. The exact ORIENT1A mapping is unchanged.
            orientCompletedSubrange(argbBase, orientedBase, rows, width, y0, y1, cameraRotation);
            const auto ended = std::chrono::steady_clock::now();
            workerElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(renderEnded - started).count());
            orientationElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - renderEnded).count());
            combinedElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count());
        });
    }
    for (auto& thread : threads) thread.join();
    const auto workerWallEnded = std::chrono::steady_clock::now();

    int64_t even = 0;
    int64_t edge = 0;
    int64_t nearWhite = 0;
    int64_t workerNsSum = 0;
    int64_t workerNsMax = 0;
    int64_t orientationNsSum = 0;
    for (int worker = 0; worker < workerCount; ++worker) {
        const auto& local = workerStats[static_cast<size_t>(worker)];
        even += local[0];
        edge += local[1];
        nearWhite += local[2];
        workerNsSum += workerElapsedNs[static_cast<size_t>(worker)];
        orientationNsSum += orientationElapsedNs[static_cast<size_t>(worker)];
        workerNsMax = std::max(workerNsMax, combinedElapsedNs[static_cast<size_t>(worker)]);
    }

    // PERF3G ORIENTFUSE8A: no serial post-worker orientation pass remains here.
    // stats[9] reports summed per-worker exact orientation-copy time; workerWallNs and
    // maxWorkerNs include the fused copy and therefore continue to describe critical wall.
    const auto outputCopyStarted = std::chrono::steady_clock::now();
    env->SetIntArrayRegion(argbArray, 0, pixelCount, orientedScratch.data());
    if (env->ExceptionCheck()) return;
    const auto outputCopyEnded = std::chrono::steady_clock::now();
    const auto nativeEnded = std::chrono::steady_clock::now();

    const jlong stats[12] = {
            static_cast<jlong>(even),
            static_cast<jlong>(edge),
            static_cast<jlong>(nearWhite),
            static_cast<jlong>(workerNsSum),
            static_cast<jlong>(workerCount),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(scratchEnded - scratchStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(inputCopyEnded - inputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(workerWallEnded - workerWallStarted).count()),
            static_cast<jlong>(workerNsMax),
            static_cast<jlong>(orientationNsSum),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(outputCopyEnded - outputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(nativeEnded - nativeStarted).count())
    };
    env->SetLongArrayRegion(statsArray, 0, 12, stats);
}


// PERF3H CVDIRECT1A: exact full-color input read directly from packed CV_16UC3 Mat storage.
// Java validates continuity/type/stride and passes the address of the first row in this block.
extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirect(
        JNIEnv* env, jclass,
        jlong handle,
        jlong camAddress,
        jint pixelCount,
        jint width,
        jintArray argbArray,
        jdouble gain,
        jdouble tgCbGain,
        jdouble tgCrGain,
        jint cameraRotation,
        jint workers,
        jlongArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    const auto* camBase = reinterpret_cast<const jshort*>(static_cast<uintptr_t>(camAddress));
    if (!ctx || !camBase || !argbArray || !statsArray || pixelCount < 0 || width <= 0
            || (pixelCount % width) != 0 || workers <= 0
            || (static_cast<uintptr_t>(camAddress) & (alignof(jshort) - 1u)) != 0u) {
        throwIllegalArgument(env, "Invalid M9 PERF3H direct COLOR block arguments");
        return;
    }
    const jsize argbLen = env->GetArrayLength(argbArray);
    const jsize statsLen = env->GetArrayLength(statsArray);
    if (argbLen < pixelCount || statsLen < 12) {
        throwIllegalArgument(env, "M9 PERF3H direct COLOR output buffers are too small");
        return;
    }

    const auto nativeStarted = std::chrono::steady_clock::now();
    thread_local std::vector<jint> argbScratch;
    thread_local std::vector<jint> orientedScratch;
    const size_t outCount = static_cast<size_t>(pixelCount);
    const auto scratchStarted = std::chrono::steady_clock::now();
    argbScratch.resize(outCount);
    orientedScratch.resize(outCount);
    const auto scratchEnded = std::chrono::steady_clock::now();
    // There is deliberately no camera-input copy in CVDIRECT1A. Mat lifetime is owned by
    // the Java renderer and extends beyond this synchronous JNI call.
    const auto inputCopyStarted = std::chrono::steady_clock::now();
    const auto inputCopyEnded = inputCopyStarted;

    const int rows = pixelCount / width;
    const int workerCount = std::max(1, std::min(static_cast<int>(workers), rows));
    std::vector<std::array<int64_t, 3>> workerStats(static_cast<size_t>(workerCount));
    std::vector<int64_t> workerElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> orientationElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> combinedElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));

    jint* const argbBase = argbScratch.data();
    jint* const orientedBase = orientedScratch.data();
    const auto workerWallStarted = std::chrono::steady_clock::now();
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (rows * worker) / workerCount;
        const int y1 = (rows * (worker + 1)) / workerCount;
        threads.emplace_back([&, worker, y0, y1, camBase, argbBase, orientedBase]() {
            const int localRows = y1 - y0;
            const int localPixels = localRows * width;
            const size_t pixelOffset = static_cast<size_t>(y0) * static_cast<size_t>(width);
            const size_t camOffset = pixelOffset * 3u;
            const auto started = std::chrono::steady_clock::now();
            renderStripScalar(*ctx,
                              camBase + camOffset,
                              localPixels,
                              width,
                              argbBase + pixelOffset,
                              gain, tgCbGain, tgCrGain,
                              workerStats[static_cast<size_t>(worker)].data());
            const auto renderEnded = std::chrono::steady_clock::now();
            orientCompletedSubrange(argbBase, orientedBase, rows, width, y0, y1, cameraRotation);
            const auto ended = std::chrono::steady_clock::now();
            workerElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(renderEnded - started).count());
            orientationElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - renderEnded).count());
            combinedElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count());
        });
    }
    for (auto& thread : threads) thread.join();
    const auto workerWallEnded = std::chrono::steady_clock::now();

    int64_t even = 0;
    int64_t edge = 0;
    int64_t nearWhite = 0;
    int64_t workerNsSum = 0;
    int64_t workerNsMax = 0;
    int64_t orientationNsSum = 0;
    for (int worker = 0; worker < workerCount; ++worker) {
        const auto& local = workerStats[static_cast<size_t>(worker)];
        even += local[0];
        edge += local[1];
        nearWhite += local[2];
        workerNsSum += workerElapsedNs[static_cast<size_t>(worker)];
        orientationNsSum += orientationElapsedNs[static_cast<size_t>(worker)];
        workerNsMax = std::max(workerNsMax, combinedElapsedNs[static_cast<size_t>(worker)]);
    }

    const auto outputCopyStarted = std::chrono::steady_clock::now();
    env->SetIntArrayRegion(argbArray, 0, pixelCount, orientedScratch.data());
    if (env->ExceptionCheck()) return;
    const auto outputCopyEnded = std::chrono::steady_clock::now();
    const auto nativeEnded = std::chrono::steady_clock::now();

    const jlong stats[12] = {
            static_cast<jlong>(even),
            static_cast<jlong>(edge),
            static_cast<jlong>(nearWhite),
            static_cast<jlong>(workerNsSum),
            static_cast<jlong>(workerCount),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(scratchEnded - scratchStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(inputCopyEnded - inputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(workerWallEnded - workerWallStarted).count()),
            static_cast<jlong>(workerNsMax),
            static_cast<jlong>(orientationNsSum),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(outputCopyEnded - outputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(nativeEnded - nativeStarted).count())
    };
    env->SetLongArrayRegion(statsArray, 0, 12, stats);
}


// PERF3I BITMAPDIRECT1A: exact CVDIRECT1A scalar input plus direct mutable
// ARGB_8888 Bitmap destination. All Bitmap validation and locking occurs before
// rendering; false means no pixels were modified and Java must use PERF3H fallback.
extern "C" JNIEXPORT jboolean JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirectBitmap(
        JNIEnv* env, jclass,
        jlong handle,
        jlong camAddress,
        jint pixelCount,
        jint width,
        jobject bitmap,
        jint blockY0,
        jint sourceHeight,
        jdouble gain,
        jdouble tgCbGain,
        jdouble tgCrGain,
        jint cameraRotation,
        jint workers,
        jlongArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    const auto* camBase = reinterpret_cast<const jshort*>(static_cast<uintptr_t>(camAddress));
    if (!ctx || !camBase || !bitmap || !statsArray || pixelCount < 0 || width <= 0
            || sourceHeight <= 0 || blockY0 < 0 || (pixelCount % width) != 0 || workers <= 0
            || (static_cast<uintptr_t>(camAddress) & (alignof(jshort) - 1u)) != 0u) {
        throwIllegalArgument(env, "Invalid M9 PERF3I direct Bitmap COLOR arguments");
        return JNI_FALSE;
    }
    const int rows = pixelCount / width;
    if (blockY0 + rows > sourceHeight || env->GetArrayLength(statsArray) < 12) {
        throwIllegalArgument(env, "M9 PERF3I direct Bitmap bounds/stats are invalid");
        return JNI_FALSE;
    }

    int rotation = cameraRotation % 360;
    if (rotation < 0) rotation += 360;
    const uint32_t expectedWidth = static_cast<uint32_t>(
            (rotation == 90 || rotation == 270) ? sourceHeight : width);
    const uint32_t expectedHeight = static_cast<uint32_t>(
            (rotation == 90 || rotation == 270) ? width : sourceHeight);

    AndroidBitmapInfo info{};
    if (AndroidBitmap_getInfo(env, bitmap, &info) != ANDROID_BITMAP_RESULT_SUCCESS
            || info.format != ANDROID_BITMAP_FORMAT_RGBA_8888
            || info.width != expectedWidth
            || info.height != expectedHeight
            || info.stride < expectedWidth * 4u) {
        return JNI_FALSE;
    }
    void* rawPixels = nullptr;
    if (AndroidBitmap_lockPixels(env, bitmap, &rawPixels) != ANDROID_BITMAP_RESULT_SUCCESS
            || rawPixels == nullptr) {
        return JNI_FALSE;
    }

    const auto nativeStarted = std::chrono::steady_clock::now();
    thread_local std::vector<jint> argbScratch;
    const size_t outCount = static_cast<size_t>(pixelCount);
    const auto scratchStarted = std::chrono::steady_clock::now();
    argbScratch.resize(outCount);
    const auto scratchEnded = std::chrono::steady_clock::now();
    const auto inputCopyStarted = std::chrono::steady_clock::now();
    const auto inputCopyEnded = inputCopyStarted;

    const int workerCount = std::max(1, std::min(static_cast<int>(workers), rows));
    std::vector<std::array<int64_t, 3>> workerStats(static_cast<size_t>(workerCount));
    std::vector<int64_t> workerElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> orientationElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> combinedElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));

    jint* const argbBase = argbScratch.data();
    auto* const bitmapBase = static_cast<uint8_t*>(rawPixels);
    const auto workerWallStarted = std::chrono::steady_clock::now();
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (rows * worker) / workerCount;
        const int y1 = (rows * (worker + 1)) / workerCount;
        threads.emplace_back([&, worker, y0, y1, camBase, argbBase, bitmapBase]() {
            const int localRows = y1 - y0;
            const int localPixels = localRows * width;
            const size_t pixelOffset = static_cast<size_t>(y0) * static_cast<size_t>(width);
            const size_t camOffset = pixelOffset * 3u;
            const auto started = std::chrono::steady_clock::now();
            renderStripScalar(*ctx,
                              camBase + camOffset,
                              localPixels,
                              width,
                              argbBase + pixelOffset,
                              gain, tgCbGain, tgCrGain,
                              workerStats[static_cast<size_t>(worker)].data());
            const auto renderEnded = std::chrono::steady_clock::now();
            writeCompletedSubrangeToBitmap(argbBase, bitmapBase, info.stride,
                                           rows, width, blockY0, sourceHeight,
                                           y0, y1, cameraRotation);
            const auto ended = std::chrono::steady_clock::now();
            workerElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(renderEnded - started).count());
            orientationElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - renderEnded).count());
            combinedElapsedNs[static_cast<size_t>(worker)] =
                    static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count());
        });
    }
    for (auto& thread : threads) thread.join();
    const auto workerWallEnded = std::chrono::steady_clock::now();

    int64_t even = 0;
    int64_t edge = 0;
    int64_t nearWhite = 0;
    int64_t workerNsSum = 0;
    int64_t workerNsMax = 0;
    int64_t orientationNsSum = 0;
    for (int worker = 0; worker < workerCount; ++worker) {
        const auto& local = workerStats[static_cast<size_t>(worker)];
        even += local[0];
        edge += local[1];
        nearWhite += local[2];
        workerNsSum += workerElapsedNs[static_cast<size_t>(worker)];
        orientationNsSum += orientationElapsedNs[static_cast<size_t>(worker)];
        workerNsMax = std::max(workerNsMax, combinedElapsedNs[static_cast<size_t>(worker)]);
    }

    const auto outputCopyStarted = std::chrono::steady_clock::now();
    const auto outputCopyEnded = outputCopyStarted; // direct Bitmap destination: no JNI jint[] output copy
    const int unlockResult = AndroidBitmap_unlockPixels(env, bitmap);
    const auto nativeEnded = std::chrono::steady_clock::now();
    if (unlockResult != ANDROID_BITMAP_RESULT_SUCCESS) {
        throwIllegalArgument(env, "M9 PERF3I could not unlock direct Bitmap");
        return JNI_FALSE;
    }

    const jlong stats[12] = {
            static_cast<jlong>(even),
            static_cast<jlong>(edge),
            static_cast<jlong>(nearWhite),
            static_cast<jlong>(workerNsSum),
            static_cast<jlong>(workerCount),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(scratchEnded - scratchStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(inputCopyEnded - inputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(workerWallEnded - workerWallStarted).count()),
            static_cast<jlong>(workerNsMax),
            static_cast<jlong>(orientationNsSum),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(outputCopyEnded - outputCopyStarted).count()),
            static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(nativeEnded - nativeStarted).count())
    };
    env->SetLongArrayRegion(statsArray, 0, 12, stats);
    return env->ExceptionCheck() ? JNI_FALSE : JNI_TRUE;
}
