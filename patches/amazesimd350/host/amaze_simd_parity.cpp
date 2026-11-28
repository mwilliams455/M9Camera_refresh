// AMAZESIMD350 parity driver. The test frame is built with integer arithmetic only, so
// every build (x86 SSE2, x86 portable, arm64 portable, scalar) sees identical input.
// Usage: amaze_simd_parity OUT.bin W H CFA NOISE(0|1) WORKERS REPEATS
// Writes the RGB16 result and prints the compiled AMaZE path and the best stage timings.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
extern "C" int trial_variance_parallel(const uint16_t*,int,int,int,int,const float*,int,const double*,const double*,int,int,double,float*,uint8_t*,int);
extern "C" int trial_reconstruct_perf(const uint16_t*,const float*,const uint8_t*,int,int,int,double,double,double,uint16_t*,int,double*,double*);
// Weak: 3.49 sources do not define it.
extern "C" const char* m9_amaze_simd_path() __attribute__((weak));

static uint32_t state = 350;
static uint32_t next() { state ^= state << 13; state ^= state >> 17; state ^= state << 5; return state; }

int main(int argc, char** argv) {
    if (argc != 8) { std::fprintf(stderr, "usage\n"); return 2; }
    const char* out = argv[1];
    const int w = std::atoi(argv[2]), h = std::atoi(argv[3]), cfa = std::atoi(argv[4]);
    const bool noise = std::atoi(argv[5]) != 0;
    const int workers = std::atoi(argv[6]), repeats = std::atoi(argv[7]);
    const int white = 1023, mw = 17, mh = 13;
    const float black[4] = {64, 64, 64, 64};
    std::vector<double> gains(mw * mh * 4);
    double scale = 0;
    for (int gy = 0; gy < mh; gy++) for (int gx = 0; gx < mw; gx++) {
        const double g = 1 + 1.2 * (((gx - 8) / 8.0) * ((gx - 8) / 8.0) + ((gy - 6) / 6.0) * ((gy - 6) / 6.0));
        const double v[4] = {g * 1.05, g, g, g * 1.08};
        for (int c = 0; c < 4; c++) { gains[(gy * mw + gx) * 4 + c] = v[c]; scale = std::max(scale, v[c]); }
    }
    const double profile[6] = {2e-4, 2e-6, 1.6e-4, 1.5e-6, 2.2e-4, 2.1e-6};
    // Scene in 1/1000 of full scale: gradient, checker edges, blown patches, thin dark lines on a blown band.
    std::vector<uint16_t> sensor(size_t(w) * h), norm(size_t(w) * h);
    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
        int s = 250 + (x * 7 + y * 3) % 200;
        if (((x / 256) + (y / 256)) & 1) s += 350;
        if (y < h / 5) s = 1500;
        if (y < h / 5 && (x % 100) < 3) s = 40;
        if (((x / 300) % 3 == 1) && ((y / 230) % 4 == 2)) s = 1500;
        const int r2 = (x - w * 3 / 4) * (x - w * 3 / 4) + (y - h * 3 / 4) * (y - h * 3 / 4);
        if (r2 > 280 * 280 && r2 < 284 * 284) s = 30;
        int n = 0; for (int k = 0; k < 4; k++) n += int(next() % 41) - 20;   // integer noise, +-80 per mille max
        const int level = std::clamp(s + n / 4, 0, 1000);                     // clipped to full scale
        sensor[size_t(y) * w + x] = uint16_t(64 + (level * (white - 64)) / 1000);
        norm[size_t(y) * w + x] = uint16_t((uint32_t(level) * 65535u / 1000u) * 10u / 23u);
    }
    std::vector<float> variance(noise ? size_t(w) * h : 0);
    std::vector<uint8_t> censored(noise ? size_t(w) * h : 0);
    if (noise && trial_variance_parallel(sensor.data(), w, h, cfa, 0, black, white, profile, gains.data(), mw, mh, scale,
                                         variance.data(), censored.data(), workers)) return 3;
    std::vector<uint16_t> rgb(size_t(w) * h * 3);
    double best[5] = {1e30, 1e30, 1e30, 1e30, 1e30};
    for (int r = 0; r < repeats; r++) {
        double stats[4], perf[5];
        if (trial_reconstruct_perf(norm.data(), noise ? variance.data() : nullptr, noise ? censored.data() : nullptr,
                                   w, h, cfa, 0.55, 0.62, scale, rgb.data(), workers, stats, perf)) return 4;
        for (int i = 0; i < 5; i++) best[i] = std::min(best[i], perf[i]);
    }
    FILE* f = std::fopen(out, "wb");
    if (!f || std::fwrite(rgb.data(), 2, rgb.size(), f) != rgb.size()) return 5;
    std::fclose(f);
    std::printf("path=%s size=%dx%d cfa=%d noise=%d phaseNoiseMs=%.1f amazeCoreMs=%.1f quantizeMs=%.1f\n",
                m9_amaze_simd_path ? m9_amaze_simd_path() : "SCALAR_349", w, h, cfa, int(noise), noise ? best[0] : 0.0, best[3], best[4]);
    return 0;
}
