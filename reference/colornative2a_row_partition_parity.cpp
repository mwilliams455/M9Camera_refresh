#include <cassert>
#include <cstdint>
#include <iostream>
#include <random>
#include <thread>
#include <vector>

// Include the production translation unit so this test exercises the exact frozen scalar kernel.
#include "../payload/app/src/main/cpp/m9color_jni.cpp"

int main() {
    ColorContext ctx;
    ctx.cw = {1.0, 1.0, 1.0};
    ctx.camToPp = {1,0,0, 0,1,0, 0,0,1};
    ctx.ppToM9 = {1,0,0, 0,1,0, 0,0,1};
    ctx.adapt50To65 = {1,0,0, 0,1,0, 0,0,1};
    ctx.ppToXyz = {1,0,0, 0,1,0, 0,0,1};
    ctx.xyz2Srgb = {1,0,0, 0,1,0, 0,0,1};
    ctx.hueDivisions = 6;
    ctx.satDivisions = 2;
    ctx.hsm.resize(static_cast<size_t>(ctx.hueDivisions * ctx.satDivisions * 3));
    for (int h=0; h<ctx.hueDivisions; ++h) {
        for (int s=0; s<ctx.satDivisions; ++s) {
            const size_t i = static_cast<size_t>((h * ctx.satDivisions + s) * 3);
            ctx.hsm[i+0] = 0.0;
            ctx.hsm[i+1] = 1.0;
            ctx.hsm[i+2] = 1.0;
        }
    }
    for (int i=0; i<2048; ++i) ctx.curve[static_cast<size_t>(i)] = static_cast<uint8_t>((i * 255) / 2047);

    constexpr int width = 64;
    constexpr int rows = 48;
    constexpr int pixels = width * rows;
    std::vector<jshort> cam(static_cast<size_t>(pixels) * 3u);
    std::mt19937 rng(1234567);
    std::uniform_int_distribution<int> dist(0, 65535);
    for (auto& v : cam) v = static_cast<jshort>(static_cast<uint16_t>(dist(rng)));

    std::vector<jint> sequential(pixels);
    int64_t seqStats[3]{};
    renderStripScalar(ctx, cam.data(), pixels, width, sequential.data(), 1.17, 0.94, 0.96, seqStats);

    for (int workers : {1,2,3,4,7,8}) {
        const int wc = std::max(1, std::min(workers, rows));
        std::vector<jint> parallel(pixels);
        std::vector<std::array<int64_t,3>> stats(static_cast<size_t>(wc));
        std::vector<std::thread> threads;
        for (int w=0; w<wc; ++w) {
            const int y0 = (rows * w) / wc;
            const int y1 = (rows * (w+1)) / wc;
            threads.emplace_back([&,w,y0,y1]() {
                const int localRows = y1-y0;
                const int localPixels = localRows * width;
                const size_t pixOff = static_cast<size_t>(y0) * width;
                renderStripScalar(ctx,
                                  cam.data() + pixOff * 3u,
                                  localPixels,
                                  width,
                                  parallel.data() + pixOff,
                                  1.17, 0.94, 0.96,
                                  stats[static_cast<size_t>(w)].data());
            });
        }
        for (auto& t : threads) t.join();
        assert(parallel == sequential);
        int64_t sum[3]{};
        for (const auto& st : stats) for (int k=0;k<3;++k) sum[k] += st[k];
        assert(sum[0] == seqStats[0]);
        assert(sum[1] == seqStats[1]);
        assert(sum[2] == seqStats[2]);
    }
    std::cout << "COLORNATIVE2A row-partition scalar parity PASS\n";
    return 0;
}
