#pragma once
#include <algorithm>
#include <cmath>

struct M9Tg2Chroma1A {
    double cb;
    double cr;
};

inline double m9Tg2Smoothstep1A(double a, double b, double x) {
    if (x <= a) return 0.0;
    if (x >= b) return 1.0;
    const double t = (x - a) / (b - a);
    return t * t * (3.0 - 2.0 * t);
}

inline M9Tg2Chroma1A m9Tg2NeutralChroma1A(double cb, double cr, double weight) {
    const double w = std::max(0.0, std::min(1.0, weight));
    const double chroma = std::sqrt(cb * cb + cr * cr);
    const double neutralGate = 1.0 - m9Tg2Smoothstep1A(38.0, 78.0, chroma);
    const double yellowGate = m9Tg2Smoothstep1A(2.0, 22.0, -cb);
    const double orangeGate = yellowGate * m9Tg2Smoothstep1A(2.0, 20.0, cr);
    const double greenGate = m9Tg2Smoothstep1A(2.0, 18.0, -cr);
    if (cb < 0.0) cb *= 1.0 - w * yellowGate * ((1.0 - neutralGate) * 0.18 + neutralGate * 0.58);
    if (cr > 0.0) cr *= 1.0 - w * orangeGate * (0.42 * neutralGate);
    else if (cr < 0.0) cr *= 1.0 - w * greenGate * ((1.0 - neutralGate) * 0.10 + neutralGate * 0.22);
    return {cb, cr};
}
