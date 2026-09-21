# M9DETAIL1G — native guard and noise-profile provenance

21 September 2026. **The accepted DETAIL1F guard now has a standalone C++
implementation. All five complete native JPEGs match DETAIL1F byte for byte.**
This preserves the reviewed fringe improvement and modest noise reduction;
it is an implementation step, not a stronger photographic setting. Native
green, fixed ISO160 Sharp, metering and colour processing remain exact.

## Native implementation

`noise2_guard_native.cpp` implements the mode1 target, combined-kernel variance
transport, same-CFA confidence, clipping protection and bounded signed correction.
The kernel has no Python/SciPy or Android dependencies. The host wrapper supplies
normalized RAW variance from the existing `inputs.read(..., with_noise=True)`
path. No application source, JNI entry point, production default or APK changes.

The port preserves signed floor after each smoothing pass, float32 narrowing of
residual variance and confidence, vertical-then-horizontal local means, and
ties-to-even rounding of the correction. It uses wide integer intermediates and
double-precision accumulators. Builds disable fast-math and FMA contraction.
This remains explicit mobile confidence logic around a recovered Leica mode1
target, not complete Leica Noise2 or WB emulation.

The research C ABI accepts separate read-only carrier/variance/censor inputs and
non-overlapping output/diagnostic buffers. It checks shape, CFA, neutral ratios,
variance, strength and carrier range. It reports invalid inputs and allocation
failure. The Python wrapper owns and sizes all buffers. This implementation
retains full-frame diagnostics and intermediate buffers; it is not yet a phone
memory/performance design. No visual quality is traded for performance.

## Native validation

| Check | Result |
| --- | --- |
| 144 cases: four CFAs, odd/even/minimum extents, unequal gains, three variance factors | 798,840 carrier and smoothing samples exact against F; float32 variance exact |
| Unoptimized versus optimized native build | All four output/diagnostic arrays exact in 48 cases |
| Read-only inputs, zero-variance and all-censored bypass | Exact |
| Invalid shapes, CFA, gains, strength, carrier and variance | 11 cases rejected |
| Existing F photographic falsification suite through the native port | All 36 neutral-edge and 24 known-colour results exactly equal F |
| Mixed clipping after final R/B consumer | Protected RGB exact in all four CFAs |
| AddressSanitizer and UndefinedBehaviorSanitizer | 241,800 contract samples; no reported address/undefined-behaviour errors |
| Signed rounding boundaries | 201 exact half ties plus either side of each tie |
| Five complete 4096×3072 RAW replays | 62,914,560 carrier samples exact; all five JPEG SHA256 values equal F |

All 62,914,560 native green samples remain unchanged. The supported interior
also agrees with native fixed ISO160 Sharp for 62,199,760 samples. Every full
render keeps the exact F meter values and untouched ten-pixel output border.
Correction bounds are asserted on every complete frame.

The sanitizer run disabled LeakSanitizer because it fails under this host's
ptrace environment. This is not a leak-check result. Both address and undefined
behaviour instrumentation completed. All execution is x86-64 host execution;
there is no ARM/Android build, device timing or phone parity claim.

## Calibration audit: a concrete channel-order gap

The [Android noise-profile contract](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#SENSOR_NOISE_PROFILE)
defines four coefficient pairs in CFA layout order. The inspected `Parameters`
passes those pairs and `cfaPattern` directly to `NoiseModeler`. Its four-pair
branch ignores the Bayer argument, assigns pair0 to R, averages pairs1/2 as G,
and assigns pair3 to B. `DngCreator` then writes the result as RGB pairs.

That branch assumes RGGB and cannot generally pack other layouts correctly.
The new native research helper `noise2_profile_rgb` handles **fresh four-pair
Camera2 input** explicitly:

| CFA layout | R pair | G pairs averaged | B pair |
| --- | --- | --- | --- |
| RGGB | 0 | 1, 2 | 3 |
| GRBG | 1 | 0, 3 | 2 |
| GBRG | 2 | 0, 3 | 1 |
| BGGR | 3 | 1, 2 | 0 |

Indices are zero-based. Distinct synthetic R/Gr/Gb/B coefficients verify all
four mappings. The helper neither applies the writer's frame-count multiplier
nor infers a profile's provenance. The average green profile preserves the
three-pair DNG representation; it does not establish equality of the two green
channels. It is ready for a future metadata integration, not wired into the app.

The current source is **not proof of the path used for every historical DNG**.
Custom sensor models and three-pair inputs take different paths. The older 17
Ultra ISO50 file has the 15 Ultra ISO50 R/B coefficients reversed, but this does
not independently identify either sensor's physical noise. Existing DNG tags
and all accepted F inputs are preserved. Blindly swapping them or multiplying
them by0.9 would replace one unverified assumption with another.

For the two available BGGR DNGs, a hypothetical R/B pair swap changes predicted
per-channel standard deviation by at most 1.125% (ISO104) or 1.136% (ISO50),
over normalized signal0–1. These are bounds on the stored affine profiles,
not measured changes in sensor noise or final output. They also do not settle
overall scale, sensor correlation, clipping, green split or historical writer
provenance. This pass retains the nominal factor1 unchanged.

## What the available RAWs can establish

`noise2_calibration_audit.py` inventories all20 available DNGs read-only, with
hashes, capture settings, profiles and current writer source hashes. Nineteen
descriptions report FrameCount=1; the remaining DNG lacks that description.
No pair matches model, camera ID, ISO, exposure and focal length within120s
of the filename timestamp. This metadata screen does not establish matched,
stable flat-field captures for noise measurement. A scene's texture variance
cannot be labelled measured noise just because the crop looks quiet.

The next calibration captures should keep one physical lens, ISO, exposure,
focus and illumination fixed within each repeat set. Record the original four
Camera2 pairs, CFA layout, black/white levels, frame count, adaptive multiplier,
custom-model selection and writer version alongside each single RAW. Retain
sensor-plane samples before shading/normalization; use no merged/HDR input.

For each sensor/ISO under evaluation, collect at least eight repeats at four
unclipped flat-field levels spanning shadows to mid/high signal. Pair
differences divided by sqrt(2) can estimate temporal noise while cancelling
static scene/fixed-pattern structure, provided illumination and framing are
stable. Inspect per-CFA means for drift before fitting nonnegative slope/offset;
retain separate green channels for this audit. Measure spatial covariance at
the offsets used by the carrier-residual kernel and compare observed residual
variance after the actual Co/filter chain. Fixed-pattern artifacts require
separate assessment because pair subtraction cancels them.

Use separate repeated colour-edge/texture captures to check detail retention;
do not select the noise strength on the same scenes used to report success.
The prior factor2 failure remains a reason to keep calibration explicit.
High-ISO 17 Ultra and telephoto evidence is still missing.

**Decision:** retain the native factor1 guard as the next research implementation,
with corrected DETAIL1D as fallback. The exact F appearance is preserved in the
reviewed set. Calibrated variance transport and controlled device integration
remain necessary before changing a phone default. Existing limitations on
complete Leica arithmetic, metadata replay and host JPEG encoding remain.

## Reproduce

Use the same frozen GL2G assembly, generated Sharp header and five RAWs as F.
The recorded files are `results/noise2_native_checks.json`,
`noise2_native_quality_checks.json`, `noise2_native_report.json`,
`noise2_native_sanitize.json` and `noise2_calibration_audit.json`.

```bash
python3 research/detail1a/noise2_calibration_audit.py \
  /absolute/path/inputs PhotonCamera /absolute/path/detail1g/calibration_audit.json
python3 research/detail1a/noise2_guard_native_checks.py \
  /absolute/path/detail1g --header /absolute/path/m9_sharp_fulliso_bank.h
g++ -std=c++17 -O1 -g -ffp-contract=off -fno-fast-math \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  research/detail1a/noise2_guard_native_sanitize.cpp -o /absolute/path/detail1g/native_sanitize
ASAN_OPTIONS=detect_leaks=0 /absolute/path/detail1g/native_sanitize
python3 research/detail1a/noise2_guard_native_run.py \
  --assembled PhotonCamera --header /absolute/path/m9_sharp_fulliso_bank.h \
  --reference-report research/detail1a/results/noise2_guard_report.json \
  --out /absolute/path/detail1g/replay \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng /absolute/path/15u-1142.dng
```
