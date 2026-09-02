# PERF3I BITMAPDIRECT1A Validation Summary

## Base / promotion state

- Promoted base entering this branch: **v0.7ZP-FIX1 / PERF3H CVDIRECT1A**.
- PERF3H device validation on 2026-09-02: PROMOTE.
- PERF3I is a **test candidate only** until device output/channel/orientation correctness is visually confirmed.

## PERF3H device result that motivates PERF3I

Five-frame rapid burst medians:

```text
queue wait                         1056 ms
render worker                       700 ms
render core                         492 ms
full color                          302 ms
native color worker wall          261.45 ms
TC20 total                          111 ms
native TC20                          82 ms
JPEG payload                        167 ms
JPEG encoder CPU                  147.26 ms
EXIF finalization (off worker)     44.47 ms
DNG save                            445 ms
```

Direct-input mechanism proof versus PERF3G burst median:

```text
nativeColorOpenCvTransfer       13.15 -> 0.002 ms
nativeColorInputCopy             5.11 -> 0.000 ms
meterTransfer                   10.00 -> 0.000 ms
tc20NativeInputCopy              0.81 -> 0.004 ms
```

This is approximately **29 ms/frame of directly measured duplicate input transport removed**. Overall worker/core improvements were larger, but those are not attributed entirely to CVDIRECT1A because scene/device/storage load differed.

All six uploaded PERF3H frames reported healthy JPEG/DNG/EXIF ownership and no CVDIRECT fallback.

## PERF3I target

PERF3H still leaves approximately:

```text
directOrientedCommitElapsedMs        ~23 ms median
nativeColorOutputCopyElapsedMsSum   ~5.6 ms median
```

PERF3I removes that output boundary on the eligible path by writing completed oriented pixels directly into the existing mutable ARGB_8888 Bitmap.

Architecture:

```text
OpenCV packed CV_16UC3
  -> PERF3H CVDIRECT1A scalar kernel
  -> existing Java-style 0xAARRGGBB completed pixels
  -> exact ORIENTFUSE8A mapping
  -> AndroidBitmap RGBA_8888 destination bytes
  -> same Bitmap.compress JPEG quality 95
```

No full-frame intermediate output buffer is added.

## Safety / fallback rules

Java requires:

- CVDIRECT1A input eligibility;
- mutable Bitmap;
- `Bitmap.Config.ARGB_8888`;
- exact oriented width/height;
- row bytes >= width * 4.

Native requires before writing:

- `AndroidBitmap_getInfo()` succeeds;
- `ANDROID_BITMAP_FORMAT_RGBA_8888`;
- exact destination dimensions;
- stride >= destination width * 4;
- `AndroidBitmap_lockPixels()` succeeds.

If those native checks fail, the function returns before modifying pixels and the frame uses the complete promoted PERF3H `int[] -> Bitmap.setPixels()` path. The fallback remains present in source.

## Parity validation

Frozen native photographic function hashes remain unchanged:

```text
applyHsm              7f4e1e8224d976b65be68ae21fe5fcd3d5ef43d461507ea33f87c2007fffbe5a
cameraToSrgbLuma      d2247d137a35f6ef0729df2977c494f30d54da438ed0b98197a529bdb7bbe382
cameraToM9            a3d216769a59128825c44b5b69f7f9d9219dddb76c43e00bb462293afedf2bc9
m9CurvePixel          0c88877b5d50cf409bae84fe95e6e172184f2e7f0c39352b763fd5dafa7a9d5f
renderStripScalar     c157a252e4d29657ff000f3241c21a3c9cb89dfa57769b0579e6f22ac928faa0
orientCompletedStrip  534221e756b6d5af9e54312dfad441e25120d2941e288473d7b5aeda28faa51d
```

Host validation:

- Python old block-orientation composition vs direct global mapping: **7,140 cases PASS**.
- RGBA component pack/decode: **100,000 values PASS**.
- Compiled C++ old composition vs direct RGBA mapping/packing, including padded row strides: **11,628 cases PASS**.
- `m9color_jni.cpp` C++17 host syntax check with AndroidBitmap API stub: PASS.
- `M9NativeColorCore.java` javac with minimal Bitmap stub: PASS.
- PERF3I source guard: PASS.
- apply/verifier Python bytecode compilation: PASS.

## Build wiring

`m9color` now links `jnigraphics` for `AndroidBitmap_getInfo/lockPixels/unlockPixels` while keeping:

```text
-O3
-ffp-contract=off
-fno-fast-math
```

No NEON or fast-math is enabled.

## Expected device diagnostics

Normal direct output:

```text
nativeColorBitmapOutputMode = androidbitmap_rgba8888_direct1a
nativeColorBitmapDirectEligible = true
nativeColorBitmapDirectBlocks = 8
nativeColorBitmapFallbackBlocks = 0
nativeColorOutputCopyElapsedMsSum ~= 0
directOrientedCommitElapsedMs ~= 0
```

CVDIRECT1A should remain:

```text
nativeColorInputMode = opencv_mat_dataaddr_direct1a
nativeColorCvDirectBlocks = 8
nativeColorCvFallbackBlocks = 0
meterInputMode = opencv_mat_dataaddr_direct1a
meterCvDirectFallback = false
```

## Device acceptance gate

Test one settled standalone frame, inspect the JPEG visually for orientation and R/G/B channel correctness, then take 4-5 rapid frames.

Do not promote if any of these occur:

- red/blue channel swap or other color corruption;
- orientation/mirroring/strip placement error;
- native Bitmap direct fallback on the normal Xiaomi main-camera path;
- JPEG/EXIF/DNG failure;
- queue/RAW ownership regression;
- any visible photographic-quality change.
