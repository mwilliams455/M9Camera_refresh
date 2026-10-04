// M9DETAIL1P research primitive: conservative clipped-anchor R/B carrier repair.
// Engineering safety rule, not recovered Leica firmware.
//
// A positive DETAIL1D carrier is halved only when:
//  * its target R/B AsShotNeutral ratio is <= 0.78,
//  * exactly one of the four same-colour diagonal source anchors is RAW-white
//    censored, and
//  * all three surviving measured colour differences are <= 0.
//
// The function never touches green, RAW samples, sharpening, colour or tone.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

extern "C" int m9_fringe_half_guard(
        const int32_t* difference,
        const uint16_t* sensor,
        int fullWidth,
        int fullHeight,
        int sourceX,
        int sourceY,
        int width,
        int height,
        int cfa,
        int white,
        double neutralR,
        double neutralB,
        int32_t* carrier,
        uint8_t* active,
        int32_t* reduction) {
    if (!difference || !sensor || !carrier || fullWidth < 1 || fullHeight < 1 ||
        width < 7 || height < 7 || sourceX < 0 || sourceY < 0 ||
        sourceX + width > fullWidth || sourceY + height > fullHeight ||
        cfa < 0 || cfa > 3 || white < 1 ||
        !std::isfinite(neutralR) || !std::isfinite(neutralB) ||
        neutralR <= 0.0 || neutralB <= 0.0) return -1;

    const size_t n = size_t(width) * height;
    if (active) std::memset(active, 0, n * sizeof(*active));
    if (reduction) std::memset(reduction, 0, n * sizeof(*reduction));

    const int rx = cfa & 1;
    const int ry = cfa >> 1;
    int changed = 0;
    constexpr double kMaxTargetNeutral = 0.78;

    const int dy[4] = {-1, -1, 1, 1};
    const int dx[4] = {-1, 1, -1, 1};

    for (int y = 3; y < height - 3; ++y) {
        for (int x = 3; x < width - 3; ++x) {
            const bool red = ((x & 1) == rx) && ((y & 1) == ry);
            const bool blue = ((x & 1) != rx) && ((y & 1) != ry);
            if (!red && !blue) continue;

            // Carrier at a blue CFA site is built from red diagonal anchors and
            // is consumed by R. Carrier at a red site is consumed by B.
            const double targetNeutral = blue ? neutralR : neutralB;
            if (targetNeutral > kMaxTargetNeutral) continue;

            const int i = y * width + x;
            const int32_t before = carrier[i];
            if (before <= 0) continue;

            int valid = 0;
            bool survivorsNonPositive = true;
            for (int k = 0; k < 4; ++k) {
                const int yy = y + dy[k], xx = x + dx[k];
                const int gy = sourceY + yy, gx = sourceX + xx;
                if (sensor[gy * fullWidth + gx] >= white) continue;
                ++valid;
                if (difference[yy * width + xx] > 0) survivorsNonPositive = false;
            }
            if (valid != 3 || !survivorsNonPositive) continue;

            const int32_t after = before / 2; // before > 0: exact floor-half.
            carrier[i] = after;
            if (active) active[i] = 1;
            if (reduction) reduction[i] = before - after;
            ++changed;
        }
    }
    return changed;
}
