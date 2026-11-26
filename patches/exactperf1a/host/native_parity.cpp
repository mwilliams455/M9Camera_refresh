// EXACTPERF1A host parity: candidate native kernels versus the unchanged 3.42 parent.
// The parent sources are compiled with their exported names prefixed by parent_.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <vector>

extern "C" {
int parent_phone_noise_shaded(const uint16_t*, uint16_t*, int, int, int, double, const double*,
                              const double*, double, const float*, int, int, const double*) noexcept;
int phone_noise_shaded(const uint16_t*, uint16_t*, int, int, int, double, const double*,
                       const double*, double, const float*, int, int, const double*) noexcept;
int phone_noise_shaded_parallel(const uint16_t*, uint16_t*, int, int, int, double, const double*,
                                const double*, double, const float*, int, int, const double*, int) noexcept;
int parent_m9_dng_noise_raw16(const uint16_t*, size_t, uint16_t*, size_t, int, int, int, int,
                              const double*, const double*, const float*, int, int) noexcept;
int m9_dng_noise_raw16(const uint16_t*, size_t, uint16_t*, size_t, int, int, int, int,
                       const double*, const double*, const float*, int, int) noexcept;
int parent_phase_noise(const uint16_t*, const float*, const uint8_t*, int, int, uint16_t*, int);
int parent_phase_noise_symtile_adaptive_exact(const uint16_t*, const float*, const uint8_t*, int, int, uint16_t*, int);
int phase_noise_symtile_adaptive_exact(const uint16_t*, const float*, const uint8_t*, int, int, uint16_t*, int);
}

static int failures = 0;
static double ms(std::chrono::steady_clock::time_point t) {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t).count();
}
static void expect(bool ok, const std::string& what) {
    std::printf("%s %s\n", ok ? "PASS" : "FAIL", what.c_str());
    if (!ok) ++failures;
}

// ---------------------------------------------------------------- DNG noise stage
struct NoiseCase { int w, h, mode; unsigned seed; };

static void dng_noise_cases(bool quick) {
    std::vector<NoiseCase> cases = {{4096, 3072, 1, 1}, {4000, 3000, 1, 2}, {4096, 3072, 2, 3},
                                    {638, 431, 1, 4}, {130, 66, 2, 6}, {64, 70, 1, 5}, {6, 6, 1, 7}};
    if (quick) cases = {{638, 431, 1, 4}, {130, 66, 2, 6}};
    for (const NoiseCase& c : cases) {
        const double white = 1023 * 16;
        const double black[4] = {1024, 1040, 1024, 1008};
        const double profile[8] = {2e-4, 2e-6, 1.6e-4, 1.5e-6, 1.7e-4, 1.5e-6, 2.2e-4, 2.1e-6};
        const int gh = 13, gw = 17;
        std::vector<float> grids(4 * gh * gw);
        for (int p = 0; p < 4; p++) for (int y = 0; y < gh; y++) for (int x = 0; x < gw; x++) {
            const double dx = (x - 8) / 8.0, dy = (y - 6) / 6.0;
            grids[(p * gh + y) * gw + x] = float((1 + 1.3 * (dx * dx + dy * dy)) * (p == 0 ? 1.04 : p == 3 ? 1.07 : 1));
        }
        const double geo[4] = {1.0 / (gh - 1), 1.0 / (gw - 1), 0, 0};
        std::mt19937 rng(c.seed);
        std::normal_distribution<double> nd(0, 1);
        std::vector<uint16_t> src(size_t(c.w) * c.h);
        for (int y = 0; y < c.h; y++) for (int x = 0; x < c.w; x++) {
            double s = 0.2 + 0.15 * std::sin(x * 0.02) * std::cos(y * 0.017) + ((x / 97 + y / 53) % 3 == 0 ? 0.3 : 0);
            if ((x / 300 + y / 300) % 7 == 0) s = 1.3;
            if ((x + y) % 5000 < 3) s = 0;
            const double v = black[0] + (white - black[0]) * std::clamp(s + std::sqrt(2e-4 * std::max(s, 0.0) + 2e-6) * nd(rng), 0.0, 1.0);
            src[size_t(y) * c.w + x] = uint16_t(std::round(v) / 16) * 16;
        }
        std::vector<uint16_t> want(src.size()), got(src.size());
        auto t = std::chrono::steady_clock::now();
        const int rcWant = parent_phone_noise_shaded(src.data(), want.data(), c.w, c.h, c.mode, 1.0, profile, black, white, grids.data(), gh, gw, geo);
        const double parentMs = ms(t);
        size_t changed = 0;
        for (size_t i = 0; i < src.size(); i++) changed += want[i] != src[i];
        const int rcSerial = phone_noise_shaded(src.data(), got.data(), c.w, c.h, c.mode, 1.0, profile, black, white, grids.data(), gh, gw, geo);
        expect(rcSerial == rcWant && got == want, "dng-noise serial oracle unchanged " + std::to_string(c.w) + "x" + std::to_string(c.h) + " mode " + std::to_string(c.mode));
        for (int workers : {1, 2, 3, 4, 7, 8, 64}) {
            std::fill(got.begin(), got.end(), 0xdead);
            t = std::chrono::steady_clock::now();
            const int rc = phone_noise_shaded_parallel(src.data(), got.data(), c.w, c.h, c.mode, 1.0, profile, black, white, grids.data(), gh, gw, geo, workers);
            const double parMs = ms(t);
            char label[200];
            std::snprintf(label, sizeof label, "dng-noise parallel %dx%d mode %d workers %d (changed %zu; parent %.1f ms, parallel %.1f ms)",
                          c.w, c.h, c.mode, workers, changed, parentMs, parMs);
            expect(rc == rcWant && got == want, label);
        }
    }
    // End-to-end RAW16 adapter (production JNI entry): 10-bit Camera2 RAW scaled by 16.
    const int w = quick ? 642 : 4096, h = quick ? 482 : 3072, white = 1023, scale = 16, gw = 17, gh = 13;
    const double black[4] = {64, 65, 64, 63};
    const double profile[8] = {2e-4, 2e-6, 1.6e-4, 1.5e-6, 1.7e-4, 1.5e-6, 2.2e-4, 2.1e-6};
    std::vector<float> grids(4 * gh * gw);
    for (size_t i = 0; i < grids.size(); i++) grids[i] = float(1.0 + 0.6 * ((i * 7919) % 101) / 100.0);
    std::mt19937 rng(99);
    std::vector<uint16_t> src(size_t(w) * h), want(src.size()), got(src.size());
    for (auto& v : src) v = uint16_t(64 + rng() % 960);
    const int a = parent_m9_dng_noise_raw16(src.data(), src.size() * 2, want.data(), want.size() * 2, w, h, white, scale, black, profile, grids.data(), gw, gh);
    const int b = m9_dng_noise_raw16(src.data(), src.size() * 2, got.data(), got.size() * 2, w, h, white, scale, black, profile, grids.data(), gw, gh);
    expect(a == 0 && a == b && want == got, "dng-noise production RAW16 adapter end-to-end " + std::to_string(w) + "x" + std::to_string(h));
}

// ---------------------------------------------------------------- phase noise
static void phase_noise_cases(bool quick) {
    struct Case { int w, h; unsigned seed; bool clustered; };
    std::vector<Case> cases = {{4096, 3072, 11, true}, {1024, 768, 12, false}, {777, 515, 13, true}, {64, 64, 14, true}, {16, 16, 15, false}};
    if (quick) cases = {{777, 515, 13, true}, {64, 64, 14, true}};
    for (const Case& c : cases) {
        const size_t n = size_t(c.w) * c.h;
        std::mt19937 rng(c.seed);
        std::normal_distribution<double> nd(0, 1);
        std::vector<uint16_t> raw(n);
        std::vector<float> variance(n);
        std::vector<uint8_t> clipped(n);
        for (int y = 0; y < c.h; y++) for (int x = 0; x < c.w; x++) {
            const size_t i = size_t(y) * c.w + x;
            const double s = 0.25 + 0.2 * std::sin(x * 0.01) * std::cos(y * 0.013) + (((x / 64) + (y / 64)) % 2 ? 0.08 : 0);
            const double sigma = std::sqrt(2e-4 * s + 2e-6);
            raw[i] = uint16_t(std::clamp(std::round((s + sigma * nd(rng)) * 40000), 0.0, 65535.0));
            variance[i] = float(std::pow(sigma * 40000, 2) * (0.8 + 0.4 * ((x * 13 + y * 7) % 11) / 10.0));
            const bool window = c.clustered && x > c.w * 0.7 && x < c.w * 0.78 && y > c.h * 0.15 && y < c.h * 0.26;
            clipped[i] = window || (i % 4093 == 0);
            if ((x * 31 + y * 17) % 997 == 0) variance[i] = 0;
        }
        std::vector<uint16_t> scalar(n), want(n), got(n);
        parent_phase_noise(raw.data(), variance.data(), clipped.data(), c.w, c.h, scalar.data(), 4);
        auto t = std::chrono::steady_clock::now();
        const int rcWant = parent_phase_noise_symtile_adaptive_exact(raw.data(), variance.data(), clipped.data(), c.w, c.h, want.data(), 4);
        const double parentMs = ms(t);
        expect(rcWant == 0 && want == scalar, "phase-noise parent adaptive equals scalar oracle " + std::to_string(c.w) + "x" + std::to_string(c.h));
        for (int workers : {1, 2, 3, 4, 8}) {
            std::fill(got.begin(), got.end(), 0xbeef);
            t = std::chrono::steady_clock::now();
            const int rc = phase_noise_symtile_adaptive_exact(raw.data(), variance.data(), clipped.data(), c.w, c.h, got.data(), workers);
            const double candMs = ms(t);
            char label[200];
            std::snprintf(label, sizeof label, "phase-noise dynamic %dx%d workers %d (parent static 4w %.1f ms, candidate %.1f ms)",
                          c.w, c.h, workers, parentMs, candMs);
            expect(rc == rcWant && got == want, label);
        }
    }
}

int main(int argc, char** argv) {
    const std::string mode = argc > 1 ? argv[1] : "";
    if (mode == "--dng-quick") {
        dng_noise_cases(true);  // ThreadSanitizer build: std::thread kernel only.
    } else {
        const bool quick = mode == "--quick";
        dng_noise_cases(quick);
        phase_noise_cases(quick);
    }
    std::printf("%s %d failure(s)\n", failures ? "FAILED" : "ALL_EXACT", failures);
    return failures ? 1 : 0;
}
