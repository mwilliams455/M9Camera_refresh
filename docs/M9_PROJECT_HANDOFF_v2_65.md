# M9 Project Handoff v2.64 — PERF3G Promoted / PERF3H CVDIRECT1A Next

**Checkpoint date:** 2026-09-02  
**Primary device:** Xiaomi 15 Ultra, rear wide/main camera  
**Current promoted performance branch:** `v0.7ZO / PERF3G ORIENTFUSE8A`  
**Next device-test candidate:** `v0.7ZP / PERF3H CVDIRECT1A`  
**Status:** PERF3G DEVICE-VALIDATED/PROMOTED; PERF3H HOST/STATIC VALIDATED TEST CANDIDATE

---

## 1. Frozen objective and quality gate

Continue reducing M9 primary-render latency while preserving the current photographic result.

Required output remains:

```text
capture
  -> M9 12 MP JPEG
  -> untouched development DNG
```

Quality remains a hard acceptance gate:

- 12 MP JPEG remains frozen;
- `jpegQuality = 95` remains frozen;
- Android `Bitmap.compress` encoder remains frozen;
- 64 KiB JPEG output buffer remains retained;
- no chroma-subsampling/quantization shortcut;
- no exposure changes;
- no H25/HSM/TC20/SAT3/curve02/BT.601/TG1 approximation;
- no `-ffast-math`;
- no NEON/vectorization experiment yet;
- no queue widening merely to hide processing latency.

A faster build that worsens the photographs is not a successful build.

---

## 2. Promoted architecture carried forward

Retain:

```text
COLOR8A
TC20LUMA8A
JPEGBUF64K1A
EXIFASYNC1A
ORIENTFUSE8A
DNGASYNC1A
QUEUE1B
NAME1A
TIMINGFREEZE1A
NORMNATIVE1A
METAFREEZE1A
COLORNATIVE2A-FIX1
```

Photographic renderer remains:

```text
R3.8 H25/TG1
Cobalt Xiaomi main calibration
M9 bridge
TC20
SAT3 M06/M07
curve02
exact firmware-style BT.601 horizontal 4:2:2
```

Renderer schema remains deliberately unchanged because photographic math remains unchanged:

```text
m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1
```

Timing schema remains:

```text
m9cam.primarytiming.v6.exifasync1a.dngasync1a
```

---

## 3. PERF3G ORIENTFUSE8A device validation

Test set:

```text
standalone:
IMG_20260902_074512_1788331512058_00_M9_PRIMARY.json

rapid completed frames:
IMG_20260902_074612_1788331572050_00_M9_PRIMARY.json
IMG_20260902_074612_1788331572574_00_M9_PRIMARY.json
IMG_20260902_074613_1788331573011_00_M9_PRIMARY.json
IMG_20260902_074613_1788331573428_00_M9_PRIMARY.json
IMG_20260902_074614_1788331574150_00_M9_PRIMARY.json
```

All six frames passed correctness:

```text
nativeColorOrientationMode = orientfuse8a_worker_subranges_exact
nativeColorSerialOrientationPass = false
jpegQuality = 95
jpegExifAsyncAccepted = true
jpegExifSyncFallback = false
jpegExifFinalizeSuccess = true
jpegPublicationAfterExif = true
jpegSaved = true
dngSaved = true
rawFrameCloseOwner = M9PrimaryDngIO
```

No EXIF or DNG preservation fallback occurred.

### Standalone PERF3G

```text
queue wait                       0 ms
worker                         862 ms
render core                    600 ms
full color                     300 ms
native color worker wall       233.45 ms
TC20                           149 ms
native TC20                    109 ms
JPEG payload                   207 ms
JPEG encoder CPU               177.97 ms
EXIF finalization off worker    35.30 ms
DNG save                       550 ms
```

### Rapid PERF3G five-frame medians

```text
queue wait                     693 ms
worker                         858 ms
render core                    644 ms
full color                     406 ms
native color worker wall       343.16 ms
worker-local orientation sum    26.18 ms
JNI output copy                  5.90 ms
Bitmap.setPixels commit         27 ms
OpenCV->Java color transfer     13.15 ms
JNI color input copy             5.11 ms
TC20                           177 ms
native TC20                    116 ms
meter transfer                  10 ms
TC20 native input copy           0.81 ms
JPEG payload                   171 ms
JPEG encoder CPU               150.34 ms
EXIF finalization off worker    36.59 ms
DNG save                       691 ms
```

Rapid queue waits:

```text
0, 296, 693, 1285, 1557 ms
```

The five uploaded frames all completed, but `admissionRejectCountSnapshot` progressed:

```text
0 -> 2 -> 4 -> 6 -> 8
```

This indicates additional shutter attempts were rejected by QUEUE1B while the bounded render allowance was full. This is expected preservation behavior; do not widen the queue simply to make all presses appear accepted.

---

## 4. PERF3G comparison with PERF3F

PERF3F rapid medians:

```text
worker                         1072 ms
render core                     761 ms
full color                      452 ms
native color worker wall        353.79 ms
queue wait                     1367 ms
```

PERF3G rapid medians:

```text
worker                          858 ms
render core                     644 ms
full color                      406 ms
native color worker wall        343.16 ms
queue wait                      693 ms
```

Do not credit all of the large whole-frame improvement to ORIENTFUSE8A. The PERF3G scene/device run also had much lower JPEG encoder, EXIF and DNG times.

The cleaner ORIENTFUSE signal is:

```text
native color worker wall 353.79 -> 343.16 ms  (~-10.6 ms)
```

while:

```text
nativeColorSerialOrientationPass = false
```

and the exact same orientation memory movement is now worker-local rather than a serial post-worker pass.

Decision:

```text
ORIENTFUSE8A = RETAIN / PROMOTE
```

---

## 5. Why the next target is input-side copying

PERF3G still pays pure transport costs before the frozen scalar math:

```text
full-color Mat.get(short[])                 ~13.15 ms median
full-color JNI GetShortArrayRegion           ~5.11 ms median
TC20 meter Mat.get(short[])                  ~10.00 ms median
TC20 native input copy                        ~0.81 ms median
```

Approximate duplicate-input transport budget:

```text
~29 ms/frame in this burst
```

This is preferable to direct Android Bitmap writes as the next experiment because it avoids pixel-format/Bitmap-memory semantics entirely.

The current output side remains untouched:

```text
native orientedScratch
-> JNI SetIntArrayRegion
-> Java int[]
-> Bitmap.setPixels
-> quality-95 Bitmap.compress
```

---

## 6. PERF3H CVDIRECT1A candidate

Package:

```text
M9Cam_v0_7ZP_PRIMARY2_5_PERF3H_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A_DirectFrom07ZO.zip
```

SHA-256:

```text
b6376b0bb2052ba360dc39f0da80cc18317e3b4fc23a181abfe9ed321f985b86
```

Build identity:

```text
1.31-m9modern7r38luma24fb1primary25perf3hcvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a
```

Performance marker:

```text
PERF3H_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A
```

### Execution change

PERF3H uses OpenCV `Mat.dataAddr()` only after explicitly validating the normal demosaic/meter Mat layout:

```text
isContinuous = true
channels = 3
elemSize1 = 2 bytes
step1 = width * 3 scalar elements
dataAddr != 0
```

The meter applies the corresponding `meterW * 3` check.

When valid:

```text
packed OpenCV CV_16U x3 storage
-> direct synchronous JNI read
-> exact same frozen scalar routine
```

If any layout property is unexpected:

```text
fallback to promoted PERF3G short[] copied-input path
```

No guessed stride or type is permitted.

The Mat remains alive until JNI returns, and all native child threads join before JNI returns.

---

## 7. PERF3H host/static validation

Frozen photographic function hashes remain unchanged:

```text
applyHsm
7f4e1e8224d976b65be68ae21fe5fcd3d5ef43d461507ea33f87c2007fffbe5a

cameraToSrgbLuma
d2247d137a35f6ef0729df2977c494f30d54da438ed0b98197a529bdb7bbe382

cameraToM9
a3d216769a59128825c44b5b69f7f9d9219dddb76c43e00bb462293afedf2bc9

m9CurvePixel
0c88877b5d50cf409bae84fe95e6e172184f2e7f0c39352b763fd5dafa7a9d5f

renderStripScalar
c157a252e4d29657ff000f3241c21a3c9cb89dfa57769b0579e6f22ac928faa0

orientCompletedStrip
534221e756b6d5af9e54312dfad441e25120d2941e288473d7b5aeda28faa51d
```

### Actual scalar COLOR parity

The actual frozen `renderStripScalar()` was tested with:

1. historical copied `jshort` input;
2. direct packed unsigned-16 storage viewed through the JNI sample representation.

Production-style `-O3 -ffp-contract=off -fno-fast-math` passed:

```text
PERF3H CVDIRECT1A actual scalar-kernel input parity PASS 15316 block cases
```

Includes explicit unsigned boundary values through `65535`.

### TC20 parity

The actual frozen `meterTc20WeightedSelectScalar()` passed copied-vs-direct input equality:

```text
PERF3H CVDIRECT1A TC20 direct-input parity PASS 12 cases
```

### Other validation

```text
PERF3H CVDIRECT1A source guard PASS
m9color_jni.cpp production-flag host syntax PASS
M9NativeColorCore javac PASS
patch/verifier py_compile PASS
```

The complete `m9color_jni.cpp` SHA changes because PERF3H adds new JNI wrappers, but the six quality-critical function hashes above remain frozen.

Complete PERF3H `m9color_jni.cpp` SHA-256:

```text
1b7999b7eb887bd9bf1e008fce3d129c6fd9c9ace04c5c5001a2b058a037dbe5
```

A complete Android Gradle/APK build cannot be performed from the overlay alone.

---

## 8. PERF3H expected PRIMARY diagnostics

On the expected direct path:

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

Retained correctness signals:

```text
nativeColorOrientationMode = orientfuse8a_worker_subranges_exact
nativeColorSerialOrientationPass = false
jpegQuality = 95
jpegExifAsyncAccepted = true
jpegExifSyncFallback = false
jpegExifFinalizeSuccess = true
jpegPublicationAfterExif = true
jpegSaved = true
dngSaved = true
rawFrameCloseOwner = M9PrimaryDngIO
```

Expected transport changes:

```text
meterTransferElapsedMs                 -> near zero
nativeColorOpenCvTransferElapsedMsSum  -> near zero
nativeColorInputCopyElapsedMsSum        -> near zero
```

`tc20NativeInputCopyElapsedMs` may remain slightly above zero because row/column weight arrays are still copied; the large meter camera array is no longer copied on the direct path.

---

## 9. PERF3H device test

Test:

1. one settled standalone frame after cooling;
2. 4-5 rapid frames.

Compare primarily:

```text
meterTransferElapsedMs
tc20NativeInputCopyElapsedMs
nativeColorOpenCvTransferElapsedMsSum
nativeColorInputCopyElapsedMsSum
nativeColorWorkerWallElapsedMsSum
fullColorRenderElapsedMs
renderCoreElapsedMs
workerElapsedMs
queueWaitElapsedMs
admissionRejectCountSnapshot
```

A useful end-to-end win is approximately 15-30 ms with no correctness/quality regression.

If direct eligibility is unexpectedly false, do not remove the fallback. Inspect the reported Mat step/type/layout first.

---

## 10. What NOT to do next

Do not yet:

- lower JPEG quality;
- change JPEG encoder;
- change JPEG chroma behavior;
- change photographic math;
- alter exposure;
- enable fast-math;
- vectorize the branchy double-heavy HSM kernel;
- increase COLOR workers beyond 8;
- widen QUEUE1B;
- remove CVDIRECT1A fallback;
- write Android Bitmap pixels directly without a dedicated pixel-layout/parity gate.

---

## 11. After PERF3H

If CVDIRECT1A passes and produces the expected transport collapse, retain/promote it.

The remaining low-risk output boundary will still be approximately:

```text
JNI output copy                 ~5-8 ms
Bitmap.setPixels commit        ~21-29 ms
```

Only then investigate a direct Bitmap/native destination or another exact output-buffer architecture, with explicit RGBA/ARGB memory-layout validation and pixel parity before device promotion.

The scalar full-color compute remains the largest long-term block, but it should remain frozen until architectural/copy gains are exhausted.

---

## 12. Executive state

PERF3G is promoted. Its exact ORIENT1A copy is now distributed into the existing COLOR8A workers, removes the serial orientation pass, passes device correctness, and shows a plausible ~10.6 ms native-color critical-wall improvement versus the prior PERF3F burst despite substantial whole-frame run variability.

PERF3H is the next quality-safe candidate. It does **not** touch output pixels, Android Bitmap memory, JPEG quality, exposure, or photographic math. It removes redundant OpenCV->Java->native camera-input copies only when the Mat layout is explicitly verified, and otherwise preserves the exact promoted fallback.

**Current promoted build:** `v0.7ZO / PERF3G ORIENTFUSE8A`  
**Next test:** `v0.7ZP / PERF3H CVDIRECT1A`

---

# v2.65 addendum — PERF3H FIX1 verifier correction

**Checkpoint date:** 2026-09-02

The first `v0.7ZP / PERF3H CVDIRECT1A` GitHub build stopped in `verify-m9cam-v0.7-r35.py` with exactly one failure:

```text
FAIL COLORNATIVE2A serializes OpenCV extraction before JNI
```

All PERF3H-specific checks passed, including:

```text
PERF3H direct OpenCV JNI seams
PERF3H renderer validates Mat layout and has fallback
PERF3H color direct blocks diagnosed
PERF3H meter direct input diagnosed
PERF3H CVDIRECT1A renderer marker
```

## Root cause

This was a stale inherited verifier assumption, not an implementation failure.

Pre-PERF3H COLORNATIVE2A intentionally executes:

```text
cam16.get(...) -> Java short[] -> renderBlockParallel(...)
```

and the verifier therefore required the first `cam16.get(...)` to occur before the first native color call.

PERF3H intentionally changes the healthy path to:

```text
validated OpenCV Mat.dataAddr()
-> renderBlockParallelDirect(...)
```

while retaining:

```text
cam16.get(...) -> renderBlockParallel(...)
```

only as the exact preservation fallback. The historical ordering test therefore became logically incompatible with the new branch.

## FIX1

`v0.7ZP-FIX1` changes only:

```text
patches/verify-m9cam-v0.7-r35.py
```

The verifier now behaves conditionally:

- pre-PERF3H builds retain the historical extraction-before-JNI requirement;
- PERF3H requires both the guarded direct CVDIRECT1A seam and the original copied-input fallback seam, plus its direct/fallback telemetry markers.

No application/native payload changed.

The apply script hash is unchanged from the original PERF3H package:

```text
apply-m9cam-v0.7-r35-parity.py
SHA256 a4627a96f139896287836a606c690966442818ceab9882a09b697ec5fc19aed6
```

Corrected verifier:

```text
verify-m9cam-v0.7-r35.py
SHA256 e4fcbde2893e720ed7bf367c9b4a295beb866bcd0cd45414505e1e637f6bee0a
```

Corrected package:

```text
M9Cam_v0_7ZP_FIX1_PRIMARY2_5_PERF3H_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A_DirectFrom07ZO.zip
SHA256 d7b57aaa41287f3122fd39697be0382222167daa1968b5a75c7322e304b209d6
```

## Next action

Re-run the GitHub build with `v0.7ZP-FIX1`. No new device-test protocol is required merely because of FIX1; after the APK builds, continue the original PERF3H device test: one cooled standalone frame followed by 4–5 rapid frames, then inspect the new CVDIRECT1A telemetry and timing.
