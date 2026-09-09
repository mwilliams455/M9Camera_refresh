#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
cp = root/'app/src/main/cpp/m9color_jni.cpp'
np = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
rp = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
bp = root/'app/build.gradle'

def replace1(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'SATDOMAIN1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

c = cp.read_text()
c = replace1(c,
'''#include <new>
#include <vector>''',
'''#include <new>
#include <vector>
#include <sstream>
#include <iomanip>''',
'includes')

native_helpers = r'''
// SATDOMAIN1A: read-only saturation-domain audit. This code never writes rendered pixels.
// It reuses the exact post-bridge M9 vectors and frozen TC20 gain, then evaluates the
// recovered SAT2/SAT3/SAT4 families side-by-side before and after the first required
// 11-bit curve02-coordinate clamp.
struct SatDomainFamilyAgg {
    uint64_t under[3]{};
    uint64_t over[3]{};
    uint64_t anyBoundary = 0;
    uint64_t boundaryMask[8]{};
    uint64_t dominantBoundary[4]{};
    double maxUnder[3]{};
    double maxOver[3]{};
    double sumHuePreToUnclamped = 0.0;
    double sumHueUnclampedToClamped = 0.0;
    double sumHuePreToClamped = 0.0;
    double maxHueUnclampedToClamped = 0.0;
    double sumChromaPre = 0.0;
    double sumChromaUnclamped = 0.0;
    double sumChromaClamped = 0.0;
    uint64_t magentaUnclamped = 0;
    uint64_t magentaClamped = 0;
    uint64_t spatialCount[9]{};
    uint64_t spatialBoundary[9]{};
    double spatialClampHueShift[9]{};
};

struct SatDomainSample {
    double excursion = -1.0;
    int x = 0;
    int y = 0;
    int branchEven = 0;
    int64_t pre[3]{};
    double unclamped[3]{};
    int64_t clamped[3]{};
    int mask = 0;
};

inline double satHueDegrees(double r, double g, double b) {
    const double mx = std::max(r, std::max(g, b));
    const double mn = std::min(r, std::min(g, b));
    const double d = mx - mn;
    if (d <= 1e-12) return 0.0;
    double h;
    if (mx == r) {
        h = std::fmod((g - b) / d, 6.0);
        if (h < 0.0) h += 6.0;
    } else if (mx == g) {
        h = ((b - r) / d) + 2.0;
    } else {
        h = ((r - g) / d) + 4.0;
    }
    return h * 60.0;
}

inline double satHueDistance(double a, double b) {
    double d = std::fabs(a - b);
    if (d > 180.0) d = 360.0 - d;
    return d;
}

inline double satChroma(double r, double g, double b) {
    return std::max(r, std::max(g, b)) - std::min(r, std::min(g, b));
}

inline bool satMagentaProxy(double r, double g, double b) {
    constexpr double k = LUT_MAX * 0.02;
    return g <= r && g <= b && (r - g) > k && (b - g) > k;
}

inline void satDomainPushSample(std::array<SatDomainSample, 6>& samples,
                                const SatDomainSample& candidate) {
    size_t slot = samples.size();
    double lowest = candidate.excursion;
    for (size_t i = 0; i < samples.size(); ++i) {
        if (samples[i].excursion < lowest) {
            lowest = samples[i].excursion;
            slot = i;
        }
    }
    if (slot < samples.size()) samples[slot] = candidate;
}

inline void satDomainAccumulateFamily(const std::array<int64_t, 9>& q,
                                      const int64_t pre[3],
                                      double huePre,
                                      double chromaPre,
                                      int spatialBin,
                                      SatDomainFamilyAgg* agg,
                                      SatDomainSample* sampleOut) {
    const int64_t a0 = q[0] * pre[0] + q[1] * pre[1] + q[2] * pre[2];
    const int64_t a1 = q[3] * pre[0] + q[4] * pre[1] + q[5] * pre[2];
    const int64_t a2 = q[6] * pre[0] + q[7] * pre[1] + q[8] * pre[2];
    const int64_t shifted[3] = {a0 >> 16, a1 >> 16, a2 >> 16};
    const double unclamped[3] = {
        static_cast<double>(a0) / 65536.0,
        static_cast<double>(a1) / 65536.0,
        static_cast<double>(a2) / 65536.0
    };
    const int64_t clamped[3] = {
        clipl(shifted[0], 0, LUT_MAX),
        clipl(shifted[1], 0, LUT_MAX),
        clipl(shifted[2], 0, LUT_MAX)
    };

    int mask = 0;
    double excursion[3]{};
    for (int ch = 0; ch < 3; ++ch) {
        if (shifted[ch] < 0) {
            ++agg->under[ch];
            mask |= (1 << ch);
            const double u = static_cast<double>(-shifted[ch]);
            excursion[ch] = u;
            if (u > agg->maxUnder[ch]) agg->maxUnder[ch] = u;
        } else if (shifted[ch] > LUT_MAX) {
            ++agg->over[ch];
            mask |= (1 << ch);
            const double o = static_cast<double>(shifted[ch] - LUT_MAX);
            excursion[ch] = o;
            if (o > agg->maxOver[ch]) agg->maxOver[ch] = o;
        }
    }
    if (mask != 0) {
        ++agg->anyBoundary;
        ++agg->boundaryMask[mask];
        ++agg->spatialBoundary[spatialBin];
        int dominant = 3;
        if (excursion[0] > excursion[1] && excursion[0] > excursion[2]) dominant = 0;
        else if (excursion[1] > excursion[0] && excursion[1] > excursion[2]) dominant = 1;
        else if (excursion[2] > excursion[0] && excursion[2] > excursion[1]) dominant = 2;
        ++agg->dominantBoundary[dominant];
    }
    ++agg->spatialCount[spatialBin];

    const double hueUnclamped = satHueDegrees(unclamped[0], unclamped[1], unclamped[2]);
    const double hueClamped = satHueDegrees(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));
    const double dPreUnclamped = satHueDistance(huePre, hueUnclamped);
    const double dUnclampedClamped = satHueDistance(hueUnclamped, hueClamped);
    const double dPreClamped = satHueDistance(huePre, hueClamped);
    agg->sumHuePreToUnclamped += dPreUnclamped;
    agg->sumHueUnclampedToClamped += dUnclampedClamped;
    agg->sumHuePreToClamped += dPreClamped;
    if (dUnclampedClamped > agg->maxHueUnclampedToClamped) agg->maxHueUnclampedToClamped = dUnclampedClamped;
    agg->spatialClampHueShift[spatialBin] += dUnclampedClamped;
    agg->sumChromaPre += chromaPre;
    agg->sumChromaUnclamped += satChroma(unclamped[0], unclamped[1], unclamped[2]);
    agg->sumChromaClamped += satChroma(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]));
    if (satMagentaProxy(unclamped[0], unclamped[1], unclamped[2])) ++agg->magentaUnclamped;
    if (satMagentaProxy(static_cast<double>(clamped[0]), static_cast<double>(clamped[1]), static_cast<double>(clamped[2]))) ++agg->magentaClamped;

    if (sampleOut) {
        sampleOut->mask = mask;
        sampleOut->unclamped[0] = unclamped[0];
        sampleOut->unclamped[1] = unclamped[1];
        sampleOut->unclamped[2] = unclamped[2];
        sampleOut->clamped[0] = clamped[0];
        sampleOut->clamped[1] = clamped[1];
        sampleOut->clamped[2] = clamped[2];
        sampleOut->excursion = std::max(excursion[0], std::max(excursion[1], excursion[2]));
    }
}

std::string auditSatDomainJson(const ColorContext& ctx,
                               const jshort* cam,
                               int pixelCount,
                               int width,
                               int height,
                               double gain) {
    SatDomainFamilyAgg fam[3]{};
    std::array<SatDomainSample, 6> sat3Samples{};
    uint64_t preHigh[3]{};
    uint64_t branchEven = 0;
    double sumPreLuma709 = 0.0;
    double sumPreAxis = 0.0;
    double hsm[3]{};
    double m9[3]{};
    for (int p = 0; p < pixelCount; ++p) {
        const int c = p * 3;
        cameraToM9(cam, c, ctx, hsm, m9);
        const double u[3] = {m9[0] * gain * RAW_MAX, m9[1] * gain * RAW_MAX, m9[2] * gain * RAW_MAX};
        int64_t pre[3]{};
        for (int ch = 0; ch < 3; ++ch) {
            if (u[ch] > RAW_MAX) ++preHigh[ch];
            pre[ch] = clipl(static_cast<int64_t>(std::rint(u[ch])), 0, RAW_MAX);
        }
        const bool even = pre[0] >= pre[1];
        if (even) ++branchEven;
        const double pre11[3] = {static_cast<double>(pre[0]) / 8.0, static_cast<double>(pre[1]) / 8.0, static_cast<double>(pre[2]) / 8.0};
        const double huePre = satHueDegrees(pre11[0], pre11[1], pre11[2]);
        const double chromaPre = satChroma(pre11[0], pre11[1], pre11[2]);
        sumPreLuma709 += (0.2126 * pre[0] + 0.7152 * pre[1] + 0.0722 * pre[2]) / RAW_MAX;
        sumPreAxis += (pre[0] + pre[1] + pre[2]) / (3.0 * RAW_MAX);
        const int y = p / width;
        const int x = p - y * width;
        const int bx = std::min(2, (x * 3) / std::max(1, width));
        const int by = std::min(2, (y * 3) / std::max(1, height));
        const int bin = by * 3 + bx;
        SatDomainSample s3{};
        s3.x = x; s3.y = y; s3.branchEven = even ? 1 : 0;
        s3.pre[0] = pre[0]; s3.pre[1] = pre[1]; s3.pre[2] = pre[2];
        satDomainAccumulateFamily(even ? Q2E : Q2O, pre, huePre, chromaPre, bin, &fam[0], nullptr);
        satDomainAccumulateFamily(even ? QE : QO, pre, huePre, chromaPre, bin, &fam[1], &s3);
        satDomainAccumulateFamily(even ? Q4E : Q4O, pre, huePre, chromaPre, bin, &fam[2], nullptr);
        if (s3.mask != 0) satDomainPushSample(sat3Samples, s3);
    }

    const char* names[3] = {"SAT2_STANDARD_M04_M05", "SAT3_M06_M07", "SAT4_HIGH_M08_M09"};
    const double den = pixelCount > 0 ? static_cast<double>(pixelCount) : 1.0;
    std::ostringstream os;
    os << std::fixed << std::setprecision(8);
    os << "{";
    os << "\"schema\":\"m9cam.satdomain1a.v1\",";
    os << "\"readOnly\":true,\"renderedPixelsModified\":false,";
    os << "\"pixelCount\":" << pixelCount << ",\"gain\":" << gain << ",";
    os << "\"inputDomain\":\"post_M9_bridge_post_TC20_14bit_clamped\",";
    os << "\"matrixAccumulatorDomain\":\"signed_int64_Q_family_dot_product\",";
    os << "\"firstSatClamp\":\"arithmetic_shift_16_then_independent_0_2047_curve02_index_clamp\",";
    os << "\"branchDecision\":\"r>=g => even M04/M06/M08; else odd M05/M07/M09\",";
    os << "\"magentaProxyDefinition\":\"G_is_min_and_R-G_gt_2pct_LUT_and_B-G_gt_2pct_LUT\",";
    os << "\"preSat\":{";
    os << "\"highClampCountRGB\":[" << preHigh[0] << "," << preHigh[1] << "," << preHigh[2] << "],";
    os << "\"branchEvenCount\":" << branchEven << ",\"branchOddCount\":" << (static_cast<uint64_t>(pixelCount) - branchEven) << ",";
    os << "\"branchEvenFraction\":" << (branchEven / den) << ",";
    os << "\"meanLuma709Normalized\":" << (sumPreLuma709 / den) << ",\"meanNeutralAxisNormalized\":" << (sumPreAxis / den) << "},";
    os << "\"families\":[";
    for (int fi = 0; fi < 3; ++fi) {
        if (fi) os << ",";
        const SatDomainFamilyAgg& a = fam[fi];
        os << "{\"name\":\"" << names[fi] << "\",";
        os << "\"underflowCountRGB\":[" << a.under[0] << "," << a.under[1] << "," << a.under[2] << "],";
        os << "\"overflowCountRGB\":[" << a.over[0] << "," << a.over[1] << "," << a.over[2] << "],";
        os << "\"anyBoundaryCount\":" << a.anyBoundary << ",\"anyBoundaryFraction\":" << (a.anyBoundary / den) << ",";
        os << "\"maxUnderflowRGB\":[" << a.maxUnder[0] << "," << a.maxUnder[1] << "," << a.maxUnder[2] << "],";
        os << "\"maxOvershootRGB\":[" << a.maxOver[0] << "," << a.maxOver[1] << "," << a.maxOver[2] << "],";
        os << "\"boundaryMaskCount\":[";
        for (int m = 0; m < 8; ++m) { if (m) os << ","; os << a.boundaryMask[m]; }
        os << "],\"dominantBoundaryChannelCountRGBTie\":[" << a.dominantBoundary[0] << "," << a.dominantBoundary[1] << "," << a.dominantBoundary[2] << "," << a.dominantBoundary[3] << "],";
        os << "\"meanAbsHuePreToUnclampedDeg\":" << (a.sumHuePreToUnclamped / den) << ",";
        os << "\"meanAbsHueUnclampedToClampedDeg\":" << (a.sumHueUnclampedToClamped / den) << ",";
        os << "\"meanAbsHuePreToClampedDeg\":" << (a.sumHuePreToClamped / den) << ",";
        os << "\"maxAbsHueUnclampedToClampedDeg\":" << a.maxHueUnclampedToClamped << ",";
        os << "\"meanChromaPre11\":" << (a.sumChromaPre / den) << ",\"meanChromaUnclamped11\":" << (a.sumChromaUnclamped / den) << ",\"meanChromaClamped11\":" << (a.sumChromaClamped / den) << ",";
        os << "\"magentaProxyUnclampedCount\":" << a.magentaUnclamped << ",\"magentaProxyClampedCount\":" << a.magentaClamped << ",";
        os << "\"magentaProxyUnclampedFraction\":" << (a.magentaUnclamped / den) << ",\"magentaProxyClampedFraction\":" << (a.magentaClamped / den) << ",";
        os << "\"spatial3x3\":{\"pixelCount\":[";
        for (int b = 0; b < 9; ++b) { if (b) os << ","; os << a.spatialCount[b]; }
        os << "],\"boundaryFraction\":[";
        for (int b = 0; b < 9; ++b) { if (b) os << ","; const double bd = a.spatialCount[b] ? static_cast<double>(a.spatialCount[b]) : 1.0; os << (a.spatialBoundary[b] / bd); }
        os << "],\"meanClampHueShiftDeg\":[";
        for (int b = 0; b < 9; ++b) { if (b) os << ","; const double bd = a.spatialCount[b] ? static_cast<double>(a.spatialCount[b]) : 1.0; os << (a.spatialClampHueShift[b] / bd); }
        os << "]}";
        if (fi == 1) {
            os << ",\"topBoundarySamples\":[";
            bool first = true;
            for (const auto& s : sat3Samples) {
                if (s.excursion < 0.0) continue;
                if (!first) os << ",";
                first = false;
                os << "{\"x\":" << s.x << ",\"y\":" << s.y << ",\"branch\":\"" << (s.branchEven ? "M06_even" : "M07_odd") << "\",";
                os << "\"mask\":" << s.mask << ",\"maxExcursion11\":" << s.excursion << ",";
                os << "\"pre14\":[" << s.pre[0] << "," << s.pre[1] << "," << s.pre[2] << "],";
                os << "\"unclamped11\":[" << s.unclamped[0] << "," << s.unclamped[1] << "," << s.unclamped[2] << "],";
                os << "\"clamped11\":[" << s.clamped[0] << "," << s.clamped[1] << "," << s.clamped[2] << "]}";
            }
            os << "]";
        }
        os << "}";
    }
    os << "]}";
    return os.str();
}
'''

c = replace1(c,
'''void throwIllegalArgument(JNIEnv* env, const char* message) {''',
native_helpers + '''
void throwIllegalArgument(JNIEnv* env, const char* message) {''',
'native audit helpers')

jni_func = r'''
extern "C" JNIEXPORT jstring JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_auditSatDomainJsonDirect(
        JNIEnv* env, jclass,
        jlong handle,
        jlong camAddress,
        jint pixelCount,
        jint width,
        jint height,
        jdouble gain) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    const auto* cam = reinterpret_cast<const jshort*>(static_cast<uintptr_t>(camAddress));
    if (!ctx || !cam || pixelCount <= 0 || width <= 0 || height <= 0
            || pixelCount != width * height || !std::isfinite(gain) || gain <= 0.0) {
        throwIllegalArgument(env, "Invalid SATDOMAIN1A audit arguments");
        return nullptr;
    }
    const auto started = std::chrono::steady_clock::now();
    std::string json = auditSatDomainJson(*ctx, cam, pixelCount, width, height, gain);
    const auto ended = std::chrono::steady_clock::now();
    const double elapsedMs = std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count() / 1.0e6;
    if (!json.empty() && json.back() == '}') {
        json.pop_back();
        std::ostringstream t;
        t << std::fixed << std::setprecision(6) << ",\"auditElapsedMs\":" << elapsedMs << "}";
        json += t.str();
    }
    return env->NewStringUTF(json.c_str());
}

'''
c = replace1(c,
'''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_createContext(''',
jni_func + '''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_createContext(''',
'jni audit entry')
cp.write_text(c)

n = np.read_text()
n = replace1(n,
'''    static native void renderStrip(long handle,''',
'''    /** SATDOMAIN1A: read-only exact SAT2/SAT3/SAT4 domain audit on packed CV_16UC3 input. */
    static native String auditSatDomainJsonDirect(long handle,
                                                 long camAddress,
                                                 int pixelCount,
                                                 int width,
                                                 int height,
                                                 double gain);

    static native void renderStrip(long handle,''',
'java native declaration')
np.write_text(n)

r = rp.read_text()
r = replace1(r,
'''            long fullRenderStartedNs = System.nanoTime();''',
'''            // SATDOMAIN1A runs only for the SKYSAT SAT3 control. It reads the same full-resolution
            // demosaiced camera Mat and the exact already-computed TC20 gain, evaluates SAT2/3/4
            // side-by-side, and returns aggregate JSON. It cannot alter cam16, the native context,
            // meter.gain, or any rendered pixel.
            String satDomainTelemetryJson1A = null;
            long satDomainAuditElapsedMs1A = -1L;
            final boolean satDomainAuditInputEligible1A = cam16.isContinuous()
                    && cam16.channels() == 3
                    && cam16.elemSize1() == 2L
                    && cam16.step1() == (long)width * 3L
                    && cam16.dataAddr() != 0L;
            if (skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A) {
                long satDomainStartedNs1A = System.nanoTime();
                satDomainTelemetryJson1A = M9NativeColorCore.auditSatDomainJsonDirect(
                        nativeContextForFrame, cam16.dataAddr(), pixels, width, height, meter.gain);
                satDomainAuditElapsedMs1A = (System.nanoTime() - satDomainStartedNs1A) / 1_000_000L;
            }

            long fullRenderStartedNs = System.nanoTime();''',
'java audit call')

r = replace1(r,
'''            d.put("satBank", SATURATION_BANK);''',
'''            d.put("satBank", SATURATION_BANK);
            d.put("satDomain1A", skySatDiagnosticEncoded1A);
            d.put("satDomainAuditReadOnly", true);
            d.put("satDomainAuditControlOnly", true);
            d.put("satDomainAuditInputEligible", satDomainAuditInputEligible1A);
            d.put("satDomainAuditElapsedMs", satDomainAuditElapsedMs1A);
            d.put("satDomainRenderedPixelsModified", false);
            if (satDomainTelemetryJson1A != null && !satDomainTelemetryJson1A.isEmpty()) {
                d.put("satDomainTelemetry", new JSONObject(satDomainTelemetryJson1A));
            }''',
'java diagnostic json')
r = r.replace('"m9cam.renderer.skysat.v1a"', '"m9cam.renderer.satdomain.v1a"')
rp.write_text(r)

b = bp.read_text()
b = replace1(b,
'-basishsm1p-skysat1a-nativewpclip1a',
'-basishsm1p-satdomain1a-nativewpclip1a',
'version')
bp.write_text(b)

print('M9Cam BASISHSM1P SATDOMAIN1A read-only saturation-domain audit applied')
print(' - rendered SKYSAT pixels unchanged')
print(' - SAT3 control evaluates exact SAT2/SAT3/SAT4 signed matrix outputs side-by-side')
print(' - logs pre-SAT, overflow/underflow, hue/chroma before/after first 0..2047 clamp')
print(' - includes 3x3 spatial aggregates and bounded SAT3 boundary samples')
