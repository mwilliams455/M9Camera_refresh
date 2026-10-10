# M9Cam 2.56 — SHADINGPERF1A

Test candidate based on the accepted **2.55 THUMBUI1A** main commit `e8b1a4979cc9e20237b1d42a66037a006f127b85`. Main remains 2.55 until phone validation and merge. The 2.53 save queue, 2.54 redraw protection and 2.55 thumbnail-thread fix remain unchanged.

## Change

Both renderers calculated each horizontal lens-shading map coordinate, neighbouring cell and interpolation fraction again for every image row. The horizontal geometry is constant within a correction pass.

All four correction helpers in each renderer now precompute the two horizontal cell indices and the double-precision fraction once per pass, then reuse them across rows. The original multiplication, floor, clamp and subtraction are preserved exactly. Coordinates are local to the invocation; each pass still copies and uses its own live Camera2 map. There is no persistent map cache or lens-specific assumption.

For a width of 4096 this adds **65,536 bytes (64 KiB)** of coordinate-array payload, plus small object headers. It avoids repeating 4096 horizontal coordinate calculations on each of 3072 rows. Only the two renderer files and app version metadata change.

The following remain unchanged: shading strengths and alpha selection, gain decomposition, Bayer/crop mapping, interpolation arithmetic and operation order, highlight headroom, quantisation, demosaic, colour, tone, exposure, noise reduction, sharpening, JPEG/DNG output, queue limits, diagnostics policy and all recent crash fixes.

## Exactness and performance

`HOST_PARITY_BENCHMARK.json` records **4,600 exact parity cases**, comparing **203,980,112 corrected RAW samples** and every returned shading statistic. Another **76 rejection cases** preserve the exception class/message and output-buffer state. Coverage includes:

- Both renderers and all four correction helpers.
- All Bayer layouts and origin parities, including nonzero/negative offsets.
- Single-pixel/thin/odd dimensions, varied map shapes, uniform/chromatic/random/stepped gains and multiple alpha values.
- Every uint16 input code, plus 4096×3072 and 4000×3000 frames.
- Source maps unchanged and the same number of map copies.

The harness compiles the actual before/after Java helpers and each renderer's unchanged CFA resolver. Only class names and Camera2's read-only map accessors are adapted for the host. This is exact **shading-stage** parity, not a whole-JPEG comparison or a phone benchmark.

Host measurements at 4096×3072, five warmups and nine alternating paired rounds, including the new coordinate allocation:

| Path | 2.55 median | 2.56 median | Stage time reduction |
| --- | ---: | ---: | ---: |
| M9, RGGB decomposed shading | 305.90 ms | 128.65 ms | 57.9% |
| Monochrom, RGGB physical shading | 359.89 ms | 195.42 ms | 45.7% |
| M9, general Bayer decomposed shading | 343.85 ms | 156.01 ms | 54.6% |
| Monochrom, general Bayer physical shading | 352.55 ms | 153.59 ms | 56.4% |

Absolute times varied on the shared host; every measured candidate pair was faster. These percentages describe the isolated correction pass, **not total rendering or save time**. Android ART/device speed must be measured on the phone. The benchmark ran before the Android test/build workload.

## Other verification

- `SOURCE_VERIFICATION.json`: reversing only coordinate reuse restores both parent renderers exactly. **1,328 other scoped files** are byte-identical to 2.55.
- `RECONSTRUCTION_VERIFICATION.json`: all **1,331 scoped reconstructed files** match the source tree used for the build.
- `TEST_VERIFICATION.json`: **44 app tests across nine nonempty suites** pass, including thumbnail thread/lifecycle and renderer-switch regressions. Hardware and Glide delivery are controlled in Robolectric.
- `PACKAGED_VERIFICATION.json`: all **27 native libraries and 285 assets** preserved byte for byte; accepted upgrade signature, app ID and 16 KiB alignment verified.

## Recover/build

```bash
python3 M9Camera_refresh/patches/shadingperf1a/assemble.py PhotonCamera_256
# Or add --parent /path/to/verified/PhotonCamera_255.
python3 -B M9Camera_refresh/patches/shadingperf1a/verify_source.py PhotonCamera_255 PhotonCamera_256
python3 M9Camera_refresh/patches/shadingperf1a/host_parity.py PhotonCamera_255 PhotonCamera_256 --json-jar /path/to/json-20250517.jar --output shading256_host
python3 M9Camera_refresh/patches/shadingperf1a/test.py PhotonCamera_256 --sdk /path/to/android-sdk --output build256 --java-agent /path/to/byte-buddy-agent.jar
python3 M9Camera_refresh/patches/shadingperf1a/build.py PhotonCamera_256 --sdk /path/to/android-sdk --output build256
python3 M9Camera_refresh/patches/shadingperf1a/package.py PhotonCamera_256 build256/app/outputs/apk/debug/M9Cam_2.56_SHADINGPERF1A-debug.apk /path/to/M9Cam_2.55_THUMBUI1A.apk /path/to/android-sdk/build-tools/35.0.0 deliverables256
```

Use the packaging step; a fresh Gradle APK lacks the two accepted sharpness library copies. Toolchain and signing are unchanged from 2.55. Run the host benchmark without a concurrent Android build.

## Phone comparison

Install 2.56 over 2.55. Keep lens, scene, exposure, output mode, profile and diagnostics settings the same. Compare one warmup followed by several shots in M9 and Monochrom, ideally with a cool phone. Check total time until photos finish saving, colour/tone, corners and fine detail; repeat the M9 → Monochrom → M9 sequence to check the retained crash fixes. Phone speed and visual confirmation remain pending.
