#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
j=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()
c=(root/'payload/app/src/main/cpp/m9color_jni.cpp').read_text()
p=(root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
assert 'm9cam.renderer.r38.h25tg1.full12.android.v17.primary2p4tc20native1borient1anormnative1a' in r
assert 'M9-PRIMARY2.4-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A' in r
assert 'PARALLEL_RENDER_WORKERS = Math.max(2, Math.min(4' in r
assert 'RENDER_STRIP_ROWS = 24' in r
assert 'cam16.get(y0, 0, worker.camStrip)' in r
assert 'oriented.setPixels(strip.argb' in r and 'native_strip_destination_layout_orient1a' in r
assert 'M9NativeColorCore.createContext' in r and 'M9NativeColorCore.renderStrip' in r and 'M9NativeColorCore.destroyContext' in r and 'M9NativeColorCore.normalizeRawDirect' in r
assert 'tc20MeterNative' in r and 'M9NativeColorCore.meterTc20WeightedSelect' in r
assert 'native_scalar_weightedselect_parity1b' in r and 'weighted_selection_partition_p98_select' in r
assert 'meterResizeElapsedMs' in r and 'meterTransferElapsedMs' in r and 'meterWeightElapsedMs' in r and 'nativeTc20ElapsedMs' in r
assert 'meterTc20WeightedSelect' in j and 'normalizeRawDirect' in j
assert 'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelect' in c and 'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect' in c
assert 'meterTc20WeightedSelectScalar' in c and 'partitionIndicesByValue' in c and 'std::sort(order.begin(), order.end()' not in c
assert 'nativeColorMode", "scalar_cpp_jni_parity1' in r
assert 'ensureLoaded' in j and 'System.loadLibrary("m9color")' in j and 'static {' not in j
assert 'renderStripScalar(' in c
assert 'GetPrimitiveArrayCritical' not in c and 'ReleasePrimitiveArrayCritical' not in c
assert 'thread_local std::vector<jshort> camScratch' in c and 'thread_local std::vector<jint> argbScratch' in c
assert 'GetShortArrayRegion' in c and 'SetIntArrayRegion' in c
assert 'first native strip begin' in r and 'first native strip complete' in r
assert '/ 65535.0' in c
assert 'h * (static_cast<double>(hd) / 6.0)' in c
assert 's * static_cast<double>(sd - 1)' in c
assert 'constexpr double HSM_H = 0.25' in c and 'constexpr double HSM_S = 0.85' in c and 'constexpr double HSM_V = 1.00' in c
assert '16754, -7632, -922' in c and '18160, -9034, -922' in c
assert 'std::rint(m9[0] * gain * RAW_MAX)' in c
assert 'for (int x = 0; x < w2; x += 2)' in c
assert '(-2765 * rs + 1) >> 1' in c and '(4899 * r0 + 9617 * g0 + 1868 * b0) >> 14' in c
assert 'cb < 0 ? cb * tgCbGain' in c and 'cr < 0 ? cr * tgCrGain' in c
assert '1.402 * crModern' in c and '.344136 * cbModern' in c and '.714136 * crModern' in c and '1.772 * cbModern' in c
assert '_cmake_is_photon_baseline' in p and '_git_good_cmake_candidate' in p and '_download_upstream_photon_cmake' in p
assert all(k in p for k in ['dngCreator.cpp','allocator.cpp','flacRecorder.cpp','native-engine.cpp'])
assert '-ffp-contract=off' in p and '-fno-fast-math' in p and 'max-page-size=16384' in p
assert 'add_library(m9color SHARED' in p and 'target_sources(ncnnMl' not in p
assert "1.14-m9modern7r38luma24fb1primary24tc20native1b" in p and "1.16-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1a" in p
print('NORMNATIVE1A inherited TC20NATIVE1B/ORIENT1A/FIX7 source guard PASS')
