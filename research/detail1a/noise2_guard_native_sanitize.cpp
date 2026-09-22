// Standalone arithmetic/memory contract checks; not included in the shared ABI.
#include "noise2_guard_native.cpp"
#include <cassert>
#include <iostream>
int main() {
    for (int i = -100; i <= 100; ++i) {
        assert(round_even(i + .5) == (i % 2 == 0 ? i : i + 1));
        assert(round_even(i + .499) == i);
        assert(round_even(i + .501) == i + 1);
    }
    uint32_t random = 92171; size_t samples = 0;
    for (int cfa = 0; cfa < 4; ++cfa) for (int h : {24, 35, 96}) for (int w : {25, 32, 73}) {
        const size_t n = size_t(h) * w;
        std::vector<int32_t> c(n), out(n), smooth(n);
        std::vector<double> v(n);
        std::vector<uint8_t> mask(n);
        std::vector<float> vr(n), confidence(n);
        for (size_t i = 0; i < n; ++i) {
            random = random * 1664525 + 1013904223;
            c[i] = int(random % 524289) - 262144;
            v[i] = random % 1000000;
            mask[i] = random % 499 == 0;
        }
        for (double factor : {.5, 1., 2.}) {
            assert(noise2_guard_native(c.data(),v.data(),mask.data(),w,h,cfa,.0625,16.,factor,
                out.data(),smooth.data(),vr.data(),confidence.data()) == 0);
            for (size_t i = 0; i < n; ++i) {
                assert(out[i] >= std::min(c[i],smooth[i]) && out[i] <= std::max(c[i],smooth[i]));
                assert(std::abs(double(out[i])-c[i]) <= std::sqrt(vr[i])*.5+.50001);
            }
            samples += n;
        }
        assert(noise2_guard_native(nullptr,v.data(),nullptr,w,h,cfa,.37,.61,1.,
            out.data(),smooth.data(),vr.data(),confidence.data()) == -1);
    }
    std::cout << "ASan/UBSan contract samples: " << samples << "; signed ties: 201\n";
}
