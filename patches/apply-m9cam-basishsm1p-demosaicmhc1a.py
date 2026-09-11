#!/usr/bin/env python3
from pathlib import Path
import re, sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
RENDERER = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
CORE = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
GRADLE = ROOT / 'app/build.gradle'

for p in (RENDERER, CORE, CPP, GRADLE):
    if not p.exists():
        raise SystemExit(f'DEMOSAICMHC1A missing required file: {p}')

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'DEMOSAICMHC1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)

# Java JNI bridge.
t = CORE.read_text()
method = '''
    /**
     * DEMOSAICMHC1A: native Malvar-He-Cutler 5x5 RGGB demosaic.
     * Input is the existing normalized Bayer plane; output is packed CV_16UC3
     * in the same R,G,B memory order produced by OpenCV COLOR_BayerRG2BGR_EA
     * and consumed by the frozen M9 colour path. Output storage is caller-owned
     * direct memory so OpenCV can wrap it without another full-frame copy.
     */
    static native long demosaicMhcRggb(short[] raw,
                                       int width,
                                       int height,
                                       java.nio.ByteBuffer outRgb16,
                                       int workers,
                                       long[] stats);

'''
anchor = '    /** Native TC20NATIVE1B-ORIENT1A: frozen scalar H25/HSM+luma, weighted-selection median and P98. */\n'
if 'demosaicMhcRggb(' not in t:
    t = replace_once(t, anchor, method + anchor, 'M9NativeColorCore insertion')
CORE.write_text(t)

# Native MHC implementation. Integer forms are algebraically identical to the
# canonical 5x5 Malvar kernels; final values are rounded to nearest and saturated
# to unsigned 16-bit, matching the downstream CV_16UC3 domain.
t = CPP.read_text()
helper_anchor = '''inline uint16_t u16(jshort v) {\n    return static_cast<uint16_t>(v);\n}\n'''
helpers = r'''

// DEMOSAICMHC1A: Malvar-He-Cutler 5x5 demosaic for an RGGB Bayer lattice.
// The normalized Bayer input and packed RGB16 output are both unsigned 16-bit.
inline int mhcClampCoord(int v, int hi) {
    return v < 0 ? 0 : (v >= hi ? hi - 1 : v);
}

inline int64_t mhcAt(const jshort* raw, int width, int height, int y, int x) {
    y = mhcClampCoord(y, height);
    x = mhcClampCoord(x, width);
    return static_cast<int64_t>(u16(raw[y * width + x]));
}

inline uint16_t mhcSat16From16ths(int64_t numerator16) {
    // Symmetric round-to-nearest before divide-by-16, then unsigned saturation.
    const int64_t q = numerator16 >= 0 ? (numerator16 + 8) / 16 : -((-numerator16 + 8) / 16);
    return static_cast<uint16_t>(clipl(q, 0, 65535));
}

inline uint16_t mhcSat16From8ths(int64_t numerator8) {
    const int64_t q = numerator8 >= 0 ? (numerator8 + 4) / 8 : -((-numerator8 + 4) / 8);
    return static_cast<uint16_t>(clipl(q, 0, 65535));
}

inline void mhcPixelRggb(const jshort* raw, int width, int height,
                         int y, int x, uint16_t* rgb) {
    const int64_t C  = mhcAt(raw, width, height, y, x);
    const int64_t N  = mhcAt(raw, width, height, y - 1, x);
    const int64_t S  = mhcAt(raw, width, height, y + 1, x);
    const int64_t W  = mhcAt(raw, width, height, y, x - 1);
    const int64_t E  = mhcAt(raw, width, height, y, x + 1);
    const int64_t NN = mhcAt(raw, width, height, y - 2, x);
    const int64_t SS = mhcAt(raw, width, height, y + 2, x);
    const int64_t WW = mhcAt(raw, width, height, y, x - 2);
    const int64_t EE = mhcAt(raw, width, height, y, x + 2);
    const int64_t NW = mhcAt(raw, width, height, y - 1, x - 1);
    const int64_t NE = mhcAt(raw, width, height, y - 1, x + 1);
    const int64_t SW = mhcAt(raw, width, height, y + 1, x - 1);
    const int64_t SE = mhcAt(raw, width, height, y + 1, x + 1);

    const bool evenY = (y & 1) == 0;
    const bool evenX = (x & 1) == 0;

    // Kernel for G at an R/B site, canonical /8 form.
    const int64_t greenAtRb8 = 4 * C + 2 * (N + S + W + E) - (NN + SS + WW + EE);
    // Kernel for the opposite colour at an R/B site, expressed in sixteenths
    // to represent the +/-1.5 coefficients exactly.
    const int64_t oppositeAtRb16 = 12 * C + 4 * (NW + NE + SW + SE)
                                 - 3 * (NN + SS + WW + EE);
    // Missing colour at a green site. h16 uses horizontal same-colour neighbours;
    // v16 is its transpose for vertical same-colour neighbours.
    const int64_t h16 = 10 * C + 8 * (W + E) + (NN + SS)
                      - 2 * (NW + NE + SW + SE) - 2 * (WW + EE);
    const int64_t v16 = 10 * C + 8 * (N + S) + (WW + EE)
                      - 2 * (NW + NE + SW + SE) - 2 * (NN + SS);

    if (evenY && evenX) {          // R site
        rgb[0] = static_cast<uint16_t>(C);
        rgb[1] = mhcSat16From8ths(greenAtRb8);
        rgb[2] = mhcSat16From16ths(oppositeAtRb16);
    } else if (!evenY && !evenX) { // B site
        rgb[0] = mhcSat16From16ths(oppositeAtRb16);
        rgb[1] = mhcSat16From8ths(greenAtRb8);
        rgb[2] = static_cast<uint16_t>(C);
    } else if (evenY) {            // G on R row: R horizontal, B vertical
        rgb[0] = mhcSat16From16ths(h16);
        rgb[1] = static_cast<uint16_t>(C);
        rgb[2] = mhcSat16From16ths(v16);
    } else {                       // G on B row: R vertical, B horizontal
        rgb[0] = mhcSat16From16ths(v16);
        rgb[1] = static_cast<uint16_t>(C);
        rgb[2] = mhcSat16From16ths(h16);
    }
}

'''
if 'mhcPixelRggb(' not in t:
    t = replace_once(t, helper_anchor, helper_anchor + helpers, 'native helper insertion')

jni_anchor = '''extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect(\n'''
jni = r'''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(
        JNIEnv* env, jclass,
        jshortArray rawArray,
        jint width,
        jint height,
        jobject outBuffer,
        jint workers,
        jlongArray statsArray) {
    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;
    const int64_t pixels64 = static_cast<int64_t>(width) * static_cast<int64_t>(height);
    if (pixels64 <= 0 || pixels64 > 0x7fffffffLL) return -2;
    const jsize pixels = static_cast<jsize>(pixels64);
    if (env->GetArrayLength(rawArray) < pixels) return -3;
    void* outRaw = env->GetDirectBufferAddress(outBuffer);
    const jlong outCapacity = env->GetDirectBufferCapacity(outBuffer);
    const int64_t requiredBytes = pixels64 * 3LL * static_cast<int64_t>(sizeof(uint16_t));
    if (!outRaw || outCapacity < requiredBytes) return -4;

    jboolean isCopy = JNI_FALSE;
    jshort* raw = static_cast<jshort*>(env->GetPrimitiveArrayCritical(rawArray, &isCopy));
    if (!raw) return -5;
    auto* out = static_cast<uint16_t*>(outRaw);
    const auto started = std::chrono::steady_clock::now();
    const int workerCount = std::max(1, std::min(static_cast<int>(workers), static_cast<int>(height)));
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (height * worker) / workerCount;
        const int y1 = (height * (worker + 1)) / workerCount;
        threads.emplace_back([=]() {
            for (int y = y0; y < y1; ++y) {
                for (int x = 0; x < width; ++x) {
                    mhcPixelRggb(raw, width, height, y, x,
                                 out + (static_cast<size_t>(y) * static_cast<size_t>(width)
                                        + static_cast<size_t>(x)) * 3u);
                }
            }
        });
    }
    for (auto& thread : threads) thread.join();
    const auto ended = std::chrono::steady_clock::now();
    env->ReleasePrimitiveArrayCritical(rawArray, raw, JNI_ABORT);
    const jlong elapsedNs = static_cast<jlong>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count());
    if (statsArray && env->GetArrayLength(statsArray) >= 2) {
        const jlong stats[2] = {elapsedNs, static_cast<jlong>(workerCount)};
        env->SetLongArrayRegion(statsArray, 0, 2, stats);
    }
    return elapsedNs;
}

'''
if 'M9NativeColorCore_demosaicMhcRggb' not in t:
    t = replace_once(t, jni_anchor, jni + jni_anchor, 'native JNI insertion')
CPP.write_text(t)

# Replace only the demosaic transport. Everything upstream of norm16 and everything
# downstream of cam16 is left byte-for-byte assembled by the existing branch.
t = RENDERER.read_text()
old_decl = '''        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);\n        Mat cam16 = new Mat();\n        Mat meterCam16 = new Mat();\n'''
new_decl = '''        // DEMOSAICMHC1A owns one direct RGB16 frame. The backing ByteBuffer must\n        // stay strongly reachable until cam16.release() because OpenCV wraps, not copies, it.\n        final int mhcBytes = Math.multiplyExact(Math.multiplyExact(width, height), 6);\n        ByteBuffer mhcRgbBuffer = ByteBuffer.allocateDirect(mhcBytes).order(ByteOrder.nativeOrder());\n        Mat rawMat = new Mat(); // retained only for frozen finally-block compatibility; no RAW copy required.\n        Mat cam16 = new Mat(height, width, CvType.CV_16UC3, mhcRgbBuffer);\n        Mat meterCam16 = new Mat();\n'''
if 'DEMOSAICMHC1A owns one direct RGB16 frame' not in t:
    t = replace_once(t, old_decl, new_decl, 'renderer Mat declaration')
old_demo = '''            long demosaicStartedNs = System.nanoTime();\n            rawMat.put(0, 0, norm16);\n            norm16 = null;\n            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);\n            rawMat.release();\n            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;\n'''
new_demo = '''            long demosaicStartedNs = System.nanoTime();\n            long[] mhcStats = new long[2];\n            long mhcNativeNs = M9NativeColorCore.demosaicMhcRggb(\n                    norm16, width, height, mhcRgbBuffer, NATIVE_COLOR_WORKERS, mhcStats);\n            if (mhcNativeNs < 0) {\n                throw new IllegalStateException("DEMOSAICMHC1A native failure: " + mhcNativeNs);\n            }\n            norm16 = null;\n            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;\n'''
if 'DEMOSAICMHC1A native failure' not in t:
    t = replace_once(t, old_demo, new_demo, 'renderer demosaic replacement')
# Audit fields immediately after existing demosaic timing. This does not affect pixels.
audit_anchor = '            d.put("demosaicElapsedMs", demosaicElapsedMs);\n'
audit_add = '''            d.put("demosaicMode", "DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct");\n            d.put("demosaicControl", "OpenCV_COLOR_BayerRG2BGR_EA_not_rendered");\n            d.put("demosaicInputDomain", "existing_NORM030_normalized_linear_Bayer");\n            d.put("demosaicOutputDomain", "CV_16UC3_RGB_memory_order_frozen_downstream");\n            d.put("demosaicPhotographicChangeScope", "demosaic_only_WB_shading_SOURCECAL_HSM_TC20_SAT3_curve02_BT601_TG1_frozen");\n'''
if 'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct' not in t:
    t = replace_once(t, audit_anchor, audit_anchor + audit_add, 'renderer diagnostics')
RENDERER.write_text(t)

# Make the APK self-identifying while retaining all prior production naming.
g = GRADLE.read_text()
if 'demosaicmhc1a' not in g.lower():
    m = re.search(r'(?m)^(\s*versionName\s+[\'\"])([^\'\"]+)([\'\"]\s*)$', g)
    if not m:
        raise SystemExit('DEMOSAICMHC1A versionName anchor missing')
    version = m.group(2)
    g = g[:m.start()] + m.group(1) + version + '-demosaicmhc1a' + m.group(3) + g[m.end():]
GRADLE.write_text(g)

print('DEMOSAICMHC1A applied')
