#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "LEICARB1A_EAGREEN_RGGB"

JAVA_BRIDGE = r'''package com.particlesdevs.photoncamera.m9.render;

/**
 * LEICARB1A_EAGREEN_RGGB research-only bridge.
 *
 * This is deliberately not advertised as the complete Leica M9 demosaic. It preserves
 * OpenCV EA green and the EA border, while applying Leica-derived signed R/B difference
 * averaging to the normalized RGGB interior. The native library is already loaded by
 * M9NativeColorCore before this method is reached.
 */
final class M9LeicaRbExperiment {
    private M9LeicaRbExperiment() {}

    static native boolean applyDirect(long normalizedRaw16Address,
                                      long bgr16Address,
                                      int width,
                                      int height);
}
'''

CPP_APPEND = r'''

// LEICARB1A_EAGREEN_RGGB_BEGIN
// Research-only Android A/B experiment.
//
// IMPORTANT: this is not claimed to reproduce the complete M9 pre-Green RAW-plane
// preparation. OpenCV EA supplies green and safe borders. The normalized RGGB interior
// uses the signed-16 averaging semantics closed against ASMRedBlueInterpolation1.
namespace {
static inline int16_t m9_leicarb_avg2_bits(int16_t a, int16_t b) {
    const uint16_t ua = static_cast<uint16_t>(a);
    const uint16_t ub = static_cast<uint16_t>(b);
    const uint32_t low = static_cast<uint32_t>(ua & 1u) + static_cast<uint32_t>(ub & 1u);
    const uint16_t out = static_cast<uint16_t>(
            static_cast<uint32_t>(ua >> 1) + static_cast<uint32_t>(ub >> 1) + (low >> 1));
    return static_cast<int16_t>(out);
}

static inline int16_t m9_leicarb_avg4_bits(int16_t a, int16_t b, int16_t c, int16_t d) {
    return m9_leicarb_avg2_bits(m9_leicarb_avg2_bits(a, b), m9_leicarb_avg2_bits(c, d));
}

static inline uint16_t m9_leicarb_clip14(int32_t v) {
    if (v < 0) return 0;
    if (v > 0x3fff) return 0x3fff;
    return static_cast<uint16_t>(v);
}
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9LeicaRbExperiment_applyDirect(
        JNIEnv*, jclass, jlong normalizedRaw16Address, jlong bgr16Address,
        jint width, jint height) {
    if (normalizedRaw16Address == 0 || bgr16Address == 0 || width < 4 || height < 4) {
        return JNI_FALSE;
    }

    const int w = static_cast<int>(width);
    const int h = static_cast<int>(height);
    const auto* raw = reinterpret_cast<const uint16_t*>(static_cast<uintptr_t>(normalizedRaw16Address));
    auto* bgr = reinterpret_cast<uint16_t*>(static_cast<uintptr_t>(bgr16Address));

    auto raw14 = [&](int y, int x) -> uint16_t {
        return static_cast<uint16_t>(raw[static_cast<size_t>(y) * w + x] >> 2);
    };
    auto green14 = [&](int y, int x) -> uint16_t {
        const size_t p = (static_cast<size_t>(y) * w + x) * 3u;
        return static_cast<uint16_t>(bgr[p + 1u] >> 2);
    };
    auto siteDiff = [&](int y, int x) -> int16_t {
        const uint16_t d = static_cast<uint16_t>(raw14(y, x) - green14(y, x));
        return static_cast<int16_t>(d);
    };
    auto addDiff = [&](int y, int x, int16_t d) -> uint16_t {
        return m9_leicarb_clip14(static_cast<int32_t>(green14(y, x)) + static_cast<int32_t>(d));
    };

    // Existing renderer assumption: COLOR_BayerRG2BGR_EA on RGGB, R at (even,even),
    // B at (odd,odd). Leave a one-pixel EA border untouched for a safe A/B experiment.
    for (int y = 1; y < h - 1; ++y) {
        const bool yOdd = (y & 1) != 0;
        for (int x = 1; x < w - 1; ++x) {
            const bool xOdd = (x & 1) != 0;
            uint16_t r14;
            uint16_t b14;

            if (!yOdd && !xOdd) {
                // Native R site; estimate B-G from four diagonal native B sites.
                r14 = raw14(y, x);
                b14 = addDiff(y, x, m9_leicarb_avg4_bits(
                        siteDiff(y - 1, x - 1), siteDiff(y - 1, x + 1),
                        siteDiff(y + 1, x - 1), siteDiff(y + 1, x + 1)));
            } else if (yOdd && xOdd) {
                // Native B site; estimate R-G from four diagonal native R sites.
                b14 = raw14(y, x);
                r14 = addDiff(y, x, m9_leicarb_avg4_bits(
                        siteDiff(y - 1, x - 1), siteDiff(y - 1, x + 1),
                        siteDiff(y + 1, x - 1), siteDiff(y + 1, x + 1)));
            } else if (!yOdd) {
                // Green on an R row: horizontal R-G, vertical B-G.
                r14 = addDiff(y, x, m9_leicarb_avg2_bits(
                        siteDiff(y, x - 1), siteDiff(y, x + 1)));
                b14 = addDiff(y, x, m9_leicarb_avg2_bits(
                        siteDiff(y - 1, x), siteDiff(y + 1, x)));
            } else {
                // Green on a B row: vertical R-G, horizontal B-G.
                r14 = addDiff(y, x, m9_leicarb_avg2_bits(
                        siteDiff(y - 1, x), siteDiff(y + 1, x)));
                b14 = addDiff(y, x, m9_leicarb_avg2_bits(
                        siteDiff(y, x - 1), siteDiff(y, x + 1)));
            }

            const size_t p = (static_cast<size_t>(y) * w + x) * 3u;
            bgr[p] = static_cast<uint16_t>(b14 << 2);
            // bgr[p + 1] remains the exact OpenCV EA green estimate.
            bgr[p + 2u] = static_cast<uint16_t>(r14 << 2);
        }
    }
    return JNI_TRUE;
}
// LEICARB1A_EAGREEN_RGGB_END
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <PhotonCamera root>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    java_dir = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render"
    renderer = java_dir / "M9R35Renderer.java"
    native = root / "app/src/main/cpp/m9color_jni.cpp"
    bridge = java_dir / "M9LeicaRbExperiment.java"

    if not renderer.is_file() or not native.is_file():
        raise RuntimeError("assembled baseline renderer/native source missing")

    renderer_text = renderer.read_text()
    native_text = native.read_text()
    if MARKER in renderer_text or MARKER in native_text or bridge.exists():
        raise RuntimeError("LEICARB1A experiment already present")

    bridge.write_text(JAVA_BRIDGE)
    native.write_text(native_text + CPP_APPEND)

    renderer_text = replace_once(
        renderer_text,
        "        long demosaicElapsedMs = -1L;\n",
        "        long demosaicElapsedMs = -1L;\n"
        "        long leicaRbExperimentElapsedMs = -1L;\n"
        "        boolean leicaRbExperimentApplied = false;\n",
        "demosaic timing declaration",
    )

    old_seam = '''            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
            rawMat.release();
            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;
'''
    new_seam = '''            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
            final boolean leicaRbDirectEligible = rawMat.isContinuous()
                    && rawMat.channels() == 1
                    && rawMat.elemSize1() == 2L
                    && rawMat.step1() == (long)width
                    && rawMat.dataAddr() != 0L
                    && cam16.isContinuous()
                    && cam16.channels() == 3
                    && cam16.elemSize1() == 2L
                    && cam16.step1() == (long)width * 3L
                    && cam16.dataAddr() != 0L;
            long leicaRbStartedNs = System.nanoTime();
            if (leicaRbDirectEligible) {
                leicaRbExperimentApplied = M9LeicaRbExperiment.applyDirect(
                        rawMat.dataAddr(), cam16.dataAddr(), width, height);
            }
            leicaRbExperimentElapsedMs = (System.nanoTime() - leicaRbStartedNs) / 1_000_000L;
            Log.d(TAG, "LEICARB1A_EAGREEN_RGGB applied=" + leicaRbExperimentApplied
                    + " eligible=" + leicaRbDirectEligible
                    + " elapsedMs=" + leicaRbExperimentElapsedMs);
            rawMat.release();
            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;
'''
    renderer_text = replace_once(renderer_text, old_seam, new_seam, "OpenCV EA seam")

    diag_anchor = '            d.put("demosaicElapsedMs", demosaicElapsedMs);\n'
    diag_extra = (
        diag_anchor
        + '            d.put("demosaicMode", leicaRbExperimentApplied ? "EA_GREEN_LEICARB1A_RGGB_INTERIOR" : "OPENCV_EA_FALLBACK");\n'
        + '            d.put("leicaRbExperiment", "LEICARB1A_EAGREEN_RGGB");\n'
        + '            d.put("leicaRbExperimentApplied", leicaRbExperimentApplied);\n'
        + '            d.put("leicaRbExperimentElapsedMs", leicaRbExperimentElapsedMs);\n'
        + '            d.put("leicaRbAdapter", "normalized16_to_14_shift2_rggb_rawgrid_ea_green_ea_border1");\n'
        + '            d.put("leicaRbClaim", "experimental_rawgrid_adapter_not_full_m9_pre_green_pipeline");\n'
    )
    renderer_text = replace_once(renderer_text, diag_anchor, diag_extra, "diagnostic anchor")
    renderer.write_text(renderer_text)

    print(f"LEICARB1A applied to {root}")
    print(f"renderer={renderer}")
    print(f"native={native}")
    print(f"bridge={bridge}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
