// Inject failures only for a 4096-pixel RGB16 row. Compare every output sample.
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <vector>

using Filter = int(uint16_t*, int, int, const double*, const double*, int, int, double, double*);
extern "C" Filter m9_noisecancel1b_apply;
extern "C" Filter m9_noisecancel1b_apply_scalar_reference;
constexpr int width = 4096, height = 3072;
constexpr size_t rowBytes = width * 3 * sizeof(uint16_t);
static std::atomic<int> active{0}, peak{0};
static int limit = 1000;
struct alignas(std::max_align_t) Header { size_t size; };

void* operator new(size_t size) {
    if (size == rowBytes) {
        int count = ++active;
        if (count > limit) { --active; throw std::bad_alloc(); }
        int old = peak;
        while (count > old && !peak.compare_exchange_weak(old, count)) {}
    }
    Header* p = static_cast<Header*>(std::malloc(sizeof(Header) + size));
    if (!p) {
        if (size == rowBytes) --active;
        throw std::bad_alloc();
    }
    p->size = size;
    return p + 1;
}
void operator delete(void* ptr) noexcept {
    if (!ptr) return;
    Header* p = static_cast<Header*>(ptr) - 1;
    if (p->size == rowBytes) --active;
    std::free(p);
}
void operator delete(void* ptr, size_t) noexcept { ::operator delete(ptr); }

int main() {
    std::vector<uint16_t> input(width * height * 3);
    for (size_t i = 0; i < input.size(); ++i) input[i] = 3000 + i % 127;
    const double profile[] = {.001, .00002, .001, .00002, .001, .00002}, gains[] = {1, 1, 1, 1};
    double referenceStats[14]{};
    auto reference = input;
    if (m9_noisecancel1b_apply_scalar_reference(reference.data(), width, height, profile, gains, 1, 1, 1,
                                                 referenceStats) || reference == input) return 1;
    for (int availableRows : {1000, 42, 16, 4, 2, 1}) {
        auto actual = input;
        limit = availableRows;
        peak = 0;
        double stats[14]{};
        int result = m9_noisecancel1b_apply(actual.data(), width, height, profile, gains, 1, 1, 1, stats);
        bool exact = availableRows == 1 ? result == -2 && actual == input :
                result == 0 && actual == reference && stats[1] == referenceStats[1];
        std::printf("availableRows=%d peakRowBytes=%zu result=%d exact=%d\n",
                    availableRows, static_cast<size_t>(peak.load()) * rowBytes, result, exact);
        if (!exact || active != 0 || peak.load() * rowBytes > 1024 * 1024) return 1;
    }
}
