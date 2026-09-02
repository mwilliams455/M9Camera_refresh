# M9 Project Handoff v2.66 — PERF3H CVDIRECT1A Promoted / PERF3I BITMAPDIRECT1A Next

**Checkpoint date:** 2026-09-02  
**Device:** Xiaomi 15 Ultra rear wide/main  
**Promoted performance branch:** `v0.7ZP-FIX1 / PERF3H CVDIRECT1A + ORIENTFUSE8A + EXIFASYNC1A + JPEGBUF64K1A + TC20LUMA8A + COLOR8A`  
**Next test candidate:** `v0.7ZQ / PERF3I BITMAPDIRECT1A`

## 1. Quality gate remains frozen

Do not change:

- 12 MP JPEG output;
- `jpegQuality = 95`;
- Android `Bitmap.compress` encoder;
- R3.8 H25/TG1 photographic math;
- Cobalt main calibration;
- M9 bridge;
- TC20 algorithm/gain policy;
- SAT3 M06/M07;
- curve02;
- exact BT.601 horizontal 4:2:2;
- exposure;
- DNGASYNC/QUEUE1B ownership architecture.

Architectural speedups are accepted only when visible photographic quality is preserved.

## 2. PERF3H device validation — PROMOTE

Six PRIMARY JSONs were tested: one standalone plus a five-frame rapid burst.

Every frame used the intended direct OpenCV path:

```text
meterInputMode = opencv_mat_dataaddr_direct1a
meterCvDirectEligible = true
meterCvDirectFallback = false
nativeColorInputMode = opencv_mat_dataaddr_direct1a
nativeColorCvDirectEligible = true
nativeColorCvDirectBlocks = 8
nativeColorCvFallbackBlocks = 0
nativeColorCvStepShorts = 12288
```

Every frame also retained:

```text
jpegQuality = 95
jpegExifAsyncAccepted = true
jpegExifSyncFallback = false
jpegExifFinalizeSuccess = true
jpegPublicationAfterExif = true
jpegSaved = true
dngSaved = true
rawFrameCloseOwner = M9PrimaryDngIO
dngAsyncFallbackSync = false
```

Five-frame burst medians:

```text
queue wait                         1056 ms
worker                              700 ms
render core                         492 ms
full color                          302 ms
native color wall                 261.45 ms
TC20                                111 ms
native TC20                          82 ms
JPEG payload                        167 ms
JPEG CPU                          147.26 ms
DNG                                 445 ms
```

The directly attributable CVDIRECT1A gain versus PERF3G is roughly 29 ms/frame:

```text
color OpenCV extraction        13.15 -> 0.002 ms
color JNI input copy            5.11 -> 0.000 ms
meter transfer                 10.00 -> 0.000 ms
TC20 camera input copy          0.81 -> 0.004 ms
```

Do not attribute the full 858 -> 700 ms worker improvement to CVDIRECT1A; the scene/device/storage workload differed. The transport fields themselves prove the architectural win.

QUEUE1B remains correct. Queue-wait median was higher than PERF3G because shutter cadence was more aggressive; do not widen the queue to hide backlog.

## 3. PERF3I target — output boundary

PERF3H still spends approximately:

```text
Bitmap.setPixels commit                 ~23 ms median
native jint[] output copy               ~5.6 ms median
```

PERF3I targets only those post-photographic costs.

Normal path:

```text
CVDIRECT1A input
 -> frozen renderStripScalar
 -> exact ORIENTFUSE8A coordinate mapping
 -> direct mutable ARGB_8888 Bitmap pixels through AndroidBitmap
 -> same quality-95 Bitmap.compress
```

The scalar photographic result remains Java-style `0xAARRGGBB`. Native output explicitly writes R,G,B,A components to `ANDROID_BITMAP_FORMAT_RGBA_8888` storage.

## 4. PERF3I safety model

Direct Bitmap output is enabled only when Java validates:

- `oriented.isMutable()`;
- `Bitmap.Config.ARGB_8888`;
- expected width/height;
- row bytes >= width * 4;
- PERF3H CVDIRECT input eligibility.

Native then independently validates:

- `AndroidBitmap_getInfo` success;
- RGBA_8888 format;
- exact output dimensions;
- valid stride;
- successful pixel lock.

If native eligibility/lock fails, it returns before writing and Java permanently uses the exact promoted PERF3H `int[] -> Bitmap.setPixels` fallback for that frame.

No full-frame intermediate `int[]` is added.

## 5. PERF3I host validation

Frozen photographic hashes remain unchanged.

Parity completed:

```text
Python orientation composition        7,140 cases PASS
RGBA pack/decode                    100,000 values PASS
compiled C++ mapping/packing         11,628 cases PASS
m9color C++17 syntax                       PASS
M9NativeColorCore javac                    PASS
PERF3I source guard                        PASS
patch/verifier py_compile                  PASS
```

The C++ parity test includes padded destination strides and all 0/90/180/270 mappings.

`m9color` links `jnigraphics`; compile flags remain exact scalar:

```text
-O3 -ffp-contract=off -fno-fast-math
```

## 6. PERF3I expected device signal

```text
nativeColorBitmapOutputMode = androidbitmap_rgba8888_direct1a
nativeColorBitmapDirectEligible = true
nativeColorBitmapDirectBlocks = 8
nativeColorBitmapFallbackBlocks = 0
nativeColorOutputCopyElapsedMsSum ~= 0
directOrientedCommitElapsedMs ~= 0
```

CVDIRECT1A must remain direct/no-fallback.

Expected quality-safe wall improvement is roughly 20-30 ms/frame if Bitmap lock/write scheduling behaves well on device.

## 7. Critical acceptance test

First take one cooled standalone photo and **visually inspect the JPEG** before doing the burst. Specifically verify:

- normal red/blue channel orientation (no R/B swap);
- correct 90-degree camera orientation;
- no strip seams, block displacement, mirroring or corruption;
- same photographic appearance as PERF3H.

Then take 4-5 rapid frames and upload PRIMARY JSONs.

If direct Bitmap output is not clean, revert immediately to promoted PERF3H. Do not attempt to tune around visual corruption.

## 8. Next after PERF3I

If PERF3I succeeds, the major exact architectural seams will largely be exhausted. Remaining broad costs will be:

- native scalar color compute (~220-300+ ms depending scene/load);
- TC20 selection/luma (~75-110+ ms currently);
- JPEG encoder CPU (~130-170+ ms currently).

Under the quality-first rule, do not jump automatically to fast-math, lower JPEG quality or approximate color math. Re-profile after PERF3I before choosing a higher-risk target.
