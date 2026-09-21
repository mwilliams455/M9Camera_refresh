# M9DETAIL1H — controlled phone integration

The accepted corrected R/B reconstruction and bounded mode1 noise guard are now
integrated after the existing native demosaic and before representation-scale
restoration, metering and colour. This candidate builds on exact GL2G INSTALLFIX1.
Green and fixed ISO160 Sharp remain the native baseline. Preview, exposure,
focus, source colour, SAT2, curve02 and JPEG encoding are unchanged.

The new stage uses 256-pixel tiles with a 12-pixel halo. The added buffer budget
is 8,565,760 bytes for a 4096×3072 frame, excluding existing renderer storage and
allocator overhead. It reads normalized RAW in full-width bands through JNI,
without holding a critical Java array across filtering. Buffers are released
on return; the existing single-worker render queue and RAW ownership remain.
The host stage takes about 1.8–2.0 seconds in the five replays; this is not a
phone timing measurement. Image quality is not reduced for speed.

## Validation completed before Android build

- All five full JPEGs match the accepted DETAIL1F files byte for byte with the
  same DNG profile authority. Meter values and 62,914,560 green samples are exact.
- 96 tiled tests cover all CFAs, odd/minimum dimensions, three tile sizes,
  clipping and green preservation: 6,328,872 RGB samples match full-frame G and D.
- Injected guard failure after earlier tiles have changed the frame recomputes
  the entire corrected-D fallback exactly in all four CFAs. No mixed result is
  accepted. Fault injection is compiled only in the host test target.
- The actual Java helper executes through JVM JNI into the C++ entry point:
  16 CFA/origin cases, 3,195,024 RGB samples exact, including missing-profile D
  fallback. Four-channel packing, scale rejection and non-finite profiles are tested.
- Address/undefined-behaviour sanitizers pass 1,457,352 RGB samples. Leak checking
  is disabled only for the local ptrace environment; CI enables it.

## Noise-profile authority on the phone

The candidate uses fresh `CaptureResult.SENSOR_NOISE_PROFILE` pairs in physical
CFA order, explicitly maps them to RGB, and averages the two green profiles.
It does not apply Photon writer/custom-model/stacking multipliers. That live
estimate can differ from historical DNG tags used in the equivalence replay;
byte parity of the host JPEGs is conditional on the same input profile. This is
not a claim of historical writer correction or measured sensor calibration.

The existing physical LensShadingMap is decomposed with the same NORM030 alpha
and representation scale. A mismatch disables the guard. The variance kernel
reads original black/white-normalized RAW signal, carries variance through that
gain and into green-normalized R/B differences, and protects censored samples.
No noise strength is chosen by device name or a guessed ISO multiplier.

Missing or invalid four-pair profiles retain corrected DETAIL1D R/B with the
guard off. A guard failure recomputes D across the full frame. A failure to
complete even that correction fails the render rather than exposing partial
tiles. Existing forensic demosaic/colour modes do not enter the new stage.

`renderer.detail1H` in PRIMARY/burst diagnostics records the original four
Camera2 pairs, mapped RGB profile, CFA/origin, ISO/exposure/timestamp, black/white
levels, neutral, NORM030 alpha and scale, guard reason, changed carrier count,
maximum correction, mean confidence/variance, tile count, budget and timing.
The estimate is explicitly labelled uncalibrated. DNG pixels and existing DNG
NoiseProfile tags are not rewritten by this integration.

## Build and phone check

The dedicated workflow is `.github/workflows/build-m9cam-m9detail1h.yml`. It
reconstructs and verifies GL2G, applies three changed files and four additions,
checks 30 frozen authorities, runs tile/JNI and inherited host/GPU tests, builds
Android, and checks packaged JNI/diagnostic markers, signature, alignment and
the short version name `1.61-m9detail1h-nativeguard`.

Android build and phone validation are pending at this source checkpoint.
Do not infer installability or device quality from host parity alone.

For the first phone check, compare foliage/high-contrast edges and skin/hair,
including a dim scene and two successive captures. Send the matching JPEG,
DNG and burst/PRIMARY diagnostics. Check for green/magenta edges, colour-detail
loss, seams and capture failures. Inspect `detail1H.guardApplied` and its reason
before attributing an image to guarded noise processing. Repeat flat-field
captures described in DETAIL1G remain necessary for empirical noise calibration.
No default-setting promotion or complete Leica/Android parity is claimed.

Reproduction:

```bash
python3 patches/tests/m9detail1h/native.py /absolute/path/detail1h
python3 patches/tests/m9detail1h/jni.py /absolute/path/detail1h/jni
python3 research/detail1a/detail1h_run.py \
  --header /absolute/path/m9_sharp_fulliso_bank.h --out /absolute/path/detail1h/replay \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng /absolute/path/15u-1142.dng
```

The overlay manifest pins the exact G guard and D carrier source files copied
into the Android target. `results/detail1h_*` retains local verification evidence.
