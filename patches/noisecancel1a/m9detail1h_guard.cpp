// DETAIL1G: native research port of the accepted DETAIL1F confidence guard.
// Mobile engineering, not recovered Leica logic. No production/JNI integration.
// Build without fast-math/FMA contraction; float narrowing is part of the port.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <new>
#include <vector>

static int32_t floor4(int64_t x) {
    return static_cast<int32_t>(x >= 0 ? x / 4 : -((-x + 3) / 4));
}
static int32_t round_even(double x) {
    const double q = std::floor(x), r = x - q;
    return static_cast<int32_t>(q + (r > .5 || (r == .5 && std::fmod(q, 2.) != 0.)));
}
static double unit(double x) { return std::clamp(x, 0., 1.); }

// NOISECANCEL1A_QUIETCHROMA: preserve the existing strength=1 noise/detail
// classifier, but apply a little more of the already-approved smoothing target
// only where that classifier is highly confident the residual is noise.
// This changes no green/luma samples and never crosses the mode1 target.
static double noisecancel1a_quiet_confidence(double base) {
    const double c=unit(base);
    if(c<=.65 || c>=1.) return c;
    const double t=unit((c-.65)/.25);
    const double gate=t*t*(3.-2.*t);
    return unit(c + .50*gate*(1.-c));
}
#ifdef M9NOISECANCEL1A_HOST
extern "C" double noisecancel1a_test_confidence(double c) {
    return noisecancel1a_quiet_confidence(c);
}
#endif

// Explicit CFA-position -> RGB packing for *fresh* four-pair Camera2 profiles.
// Does not reinterpret or repair already packed historical DNG NoiseProfile tags.
extern "C" int noise2_profile_rgb(const double* cfa_pairs, int cfa, double* rgb) {
    if (!cfa_pairs || !rgb || cfa < 0 || cfa > 3) return -1;
    for (int i = 0; i < 8; ++i)
        if (!std::isfinite(cfa_pairs[i]) || cfa_pairs[i] < 0) return -1;
    const int rx = cfa == 1 || cfa == 3, ry = cfa == 2 || cfa == 3;
    const int red = 2 * ry + rx, blue = 3 - red;
    for (int k = 0; k < 2; ++k) {
        rgb[k] = cfa_pairs[2 * red + k];
        rgb[2 + k] = .5 * cfa_pairs[2 * (red ^ 1) + k] + .5 * cfa_pairs[2 * (blue ^ 1) + k];
        rgb[4 + k] = cfa_pairs[2 * blue + k];
    }
    return 0;
}

struct Tap { int dy, dx; double squared; };
static std::vector<Tap> variance_taps() {
    // K uses exact dyadic coefficients. Combine K-H*K before squaring.
    double k[5][5] = {}, l[9][9] = {};
    const int dy[4] = {-1, 1, 0, 0}, dx[4] = {0, 0, -1, 1};
    for (int y : {1, 3}) for (int x : {1, 3}) {
        k[y][x] += .25;
        for (int j = 0; j < 4; ++j) k[y + dy[j]][x + dx[j]] -= 1. / 16;
    }
    const int h[5] = {1, 0, 2, 0, 1};
    for (int y = 0; y < 5; ++y) for (int x = 0; x < 5; ++x) {
        l[y + 2][x + 2] += k[y][x];
        for (int j = 0; j < 5; ++j) for (int i = 0; i < 5; ++i)
            l[y + j][x + i] -= k[y][x] * h[j] * h[i] / 16.;
    }
    std::vector<Tap> taps;
    for (int y = 0; y < 9; ++y) for (int x = 0; x < 9; ++x)
        if (l[y][x] != 0) taps.push_back({y - 4, x - 4, l[y][x] * l[y][x]});
    return taps;
}

// All buffers are non-overlapping row-major w*h samples. A null censor mask
// means no flagged samples. Diagnostics are required for this research ABI.
// Returns -1 for invalid input, -2 for allocation failure. Inputs are read-only.
extern "C" int noise2_guard_native(const int32_t* c, const double* raw_variance14,
        const uint8_t* censored, int w, int h, int cfa, double nr, double nb,
        double strength, int32_t* out, int32_t* smooth, float* vr, float* confidence) {
    if (!c || !raw_variance14 || !out || !smooth || !vr || !confidence ||
        w < 24 || h < 24 || w > 16384 || h > 16384 || cfa < 0 || cfa > 3 ||
        !std::isfinite(nr) || !std::isfinite(nb) || nr < .0625 || nr > 16 || nb < .0625 || nb > 16 ||
        !(strength == .5 || strength == 1. || strength == 2.)) return -1;
    const size_t n = size_t(w) * h;
    for (size_t i = 0; i < n; ++i)
        if (c[i] < -262144 || c[i] > 262144 || !std::isfinite(raw_variance14[i]) ||
            raw_variance14[i] < 0 || raw_variance14[i] > 1e30) return -1;
    try {
        const int rx = cfa == 1 || cfa == 3, ry = cfa == 2 || cfa == 3;
        const auto is_rb = [=](int y, int x) { return ((x & 1) == rx) == ((y & 1) == ry); };
        std::memcpy(out, c, n * sizeof(*c));
        std::memcpy(smooth, c, n * sizeof(*c));
        std::fill(confidence, confidence + n, 0.f);
        {
            std::vector<int32_t> horizontal(n, 0);
            for (int y = 3; y < h - 3; ++y) for (int x = 5; x < w - 5; ++x) {
                if (!is_rb(y, x)) continue;
                const int i = y * w + x;
                horizontal[i] = floor4(int64_t(c[i - 2]) + 2 * int64_t(c[i]) + c[i + 2]);
            }
            for (int y = 5; y < h - 5; ++y) for (int x = 5; x < w - 5; ++x) {
                if (!is_rb(y, x)) continue;
                const int i = y * w + x;
                smooth[i] = floor4(int64_t(horizontal[i - 2 * w]) + 2 * int64_t(horizontal[i]) + horizontal[i + 2 * w]);
            }
        }
        {
            std::vector<double> v(raw_variance14, raw_variance14 + n);
            for (int y = 0; y < h; ++y) for (int x = 0; x < w; ++x) {
                if (!is_rb(y, x)) continue;
                const double neutral = (y & 1) == ry ? nr : nb;
                v[y * w + x] /= neutral * neutral;
            }
            const auto taps = variance_taps();
            for (int y = 0; y < h; ++y) for (int x = 0; x < w; ++x) {
                double sum = 0;
                for (const auto& t : taps) {
                    const int sy = y + t.dy, sx = x + t.dx;
                    if (sy >= 0 && sy < h && sx >= 0 && sx < w) sum += v[sy * w + sx] * t.squared;
                }
                vr[y * w + x] = static_cast<float>(sum) * static_cast<float>(strength);
            }
        }
        std::vector<uint8_t> clipped(n, 0);
        if (censored) {
            std::vector<uint8_t> horizontal(n, 0);
            for (int y = 0; y < h; ++y) {
                int count = 0;
                for (int x = 0; x < w + 6; ++x) {
                    if (x < w) count += censored[y * w + x] != 0;
                    if (x >= 13) count -= censored[y * w + x - 13] != 0;
                    if (x >= 6) horizontal[y * w + x - 6] = count > 0;
                }
            }
            for (int x = 0; x < w; ++x) {
                int count = 0;
                for (int y = 0; y < h + 6; ++y) {
                    if (y < h) count += horizontal[y * w + x];
                    if (y >= 13) count -= horizontal[(y - 13) * w + x];
                    if (y >= 6) clipped[(y - 6) * w + x] = count > 0;
                }
            }
        }
        for (int phase = 0; phase < 2; ++phase) {
            const int py = phase ? 1 - ry : ry, px = phase ? 1 - rx : rx;
            const int ph = (h - py + 1) / 2, pw = (w - px + 1) / 2;
            const auto index = [=](int y, int x) { return (2 * y + py) * w + 2 * x + px; };
            std::vector<double> energy(size_t(ph) * pw), expected(size_t(ph) * pw);
            // Same constant-padded, vertical-then-horizontal running sums as F.
            for (int x = 0; x < pw; ++x) {
                double e = 0, v = 0;
                const auto add = [&](int y, double sign) {
                    if (y < 0 || y >= ph) return;
                    const int i = index(y, x); const double r = double(c[i]) - smooth[i];
                    e += sign * r * r; v += sign * vr[i];
                };
                for (int y = 0; y < 3; ++y) add(y, 1.);
                for (int y = 0; y < ph; ++y) {
                    energy[y * pw + x] = e / 5.; expected[y * pw + x] = v / 5.;
                    // Difference first, matching scipy's running update order.
                    const int a = y + 3, b = y - 2;
                    double ae = 0, av = 0, be = 0, bv = 0;
                    if (a < ph) { const int i = index(a, x); const double r = double(c[i]) - smooth[i]; ae = r * r; av = vr[i]; }
                    if (b >= 0) { const int i = index(b, x); const double r = double(c[i]) - smooth[i]; be = r * r; bv = vr[i]; }
                    e += ae - be; v += av - bv;
                }
            }
            for (int y = 0; y < ph; ++y) {
                double e = 0, v = 0;
                for (int x = 0; x < 3; ++x) { e += energy[y * pw + x]; v += expected[y * pw + x]; }
                for (int x = 0; x < pw; ++x) {
                    const int iy = 2 * y + py, ix = 2 * x + px, i = index(y, x);
                    if (iy >= 10 && iy < h - 10 && ix >= 10 && ix < w - 10 && !clipped[i] && vr[i] > 0) {
                        const double r = double(c[i]) - smooth[i];
                        const double trust = unit(2. - (e / 5.) / std::max(v / 5., 1e-12));
                        const double weight = unit(1. - std::abs(r) / (2. * std::sqrt(std::max(double(vr[i]), 1e-12))));
                        const double baseConfidence=trust*weight;
                        const double appliedConfidence=noisecancel1a_quiet_confidence(baseConfidence);
                        confidence[i] = static_cast<float>(appliedConfidence);
                        out[i] = c[i] + round_even(-appliedConfidence * r);
                    }
                    const int a = x + 3, b = x - 2;
                    e += (a < pw ? energy[y * pw + a] : 0.) - (b >= 0 ? energy[y * pw + b] : 0.);
                    v += (a < pw ? expected[y * pw + a] : 0.) - (b >= 0 ? expected[y * pw + b] : 0.);
                }
            }
        }
    } catch (const std::bad_alloc&) { return -2; }
    return 0;
}

// NOISECANCEL1A_QUIETCHROMA: confidence-only chroma carrier boost; green/luma path frozen.
