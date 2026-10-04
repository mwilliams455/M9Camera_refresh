# M9Cam 2.28 SHARPNESSMENU1A

Parent: c0caaffe4e623a90731c411f0b1fedfadfbb03af (2.27), accepted by Malcolm on 4 October 2026: “Already verified it does work”.

## Baseline correction and explicit choice

The earlier handoff incorrectly described production sharpening as fixed Standard. Normal production uses `M9ColourTrial1C.apply` plus `M9NoiseCancel1B`, and explicitly bypasses the old SHARPSOURCE/RBANCHOR stage. The PRIMARY sidecar still hard-coded that obsolete identity. This candidate derives the summary from the actual renderer instead.

After this was explained, Malcolm selected **Leica Standard** as the default, in preference to keeping the old unsharpened look as default. Therefore Standard in 2.28 intentionally changes spatial detail. **Off** bypasses the added stage and retains 2.27's photographic calculations. Contrast and saturation preferences are independent and are not migrated or overwritten.

## Firmware evidence and adaptation boundary

Canonical M9 1.216 firmware SHA-256: `4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20`.

The recovered Sharpening property 0x1005 points to the five-state table at 0xe5e10: Off, Low, Standard, Medium high, High. PROCESS/LUTS contains 13 rows of 2,050 signed coefficients at 0xacf8 and the 5 x 13 selector/ISO mode table at 0x5f8. The bank digest is pinned in tests. Modes use signed shifts, bounded integer multipliers and [-2048,2048] clamping; the kernel uses the recovered 3x3 [1,2,1] Gaussian, residual [-1024,1024], and 14-bit bounds.

The original camera's entire reconstruction is **not** reinstated. The kernel consumes the accepted AMaZE green plane, quantized to 14 bits after shading-domain restoration. Its correction is transported as a common RGB ratio, with a joint headroom cap and half-up 16-bit rounding. This is an explicit app adaptation to preserve camera RGB ratios, not Leica's original R/B reconstruction. The original 16-pixel reconstruction boundary plus two-pixel Sharp support remains untouched. The implementation uses only three green rows of scratch storage.

Actual captured Camera2 sensitivity selects the nearest Leica ISO in logarithmic space, clamped to 160–2500. Missing sensitivity uses 160 and is reported. There is no Xiaomi multiplier or per-lens tuning; equal reported ISO across different sensors is not a claim of calibrated noise equivalence. Off is an explicit app bypass; LUT row 0 alone does not establish the original firmware's Off dispatch mask.

## Integration

The global preference is frozen at RAW enqueue with contrast/saturation. Sharpening runs after the final meter/gain decision and before target colour preparation. Existing exposure decisions, colour reconstruction, target transforms, saturation, contrast and TG1 are retained. All 23 accepted native libraries are copied byte-for-byte from 2.27 during packaging; a separate `libm9sharpness.so` is added for arm64 and armv7.

The menu accurately states that the setting applies to saved JPEGs. The ISP preview is not a spatial-sharpness simulation. Editable DNG sensor samples and colour/tone profiles do not contain the JPEG spatial kernel; the reader controls detail. Capture diagnostics record the selected JPEG kernel, ISO, mode, actual changed pixels and these boundaries.

## Verification and build

`verify_native.py` compares all 65 level/ISO combinations against an independent array oracle, full signed coefficient ranges, 14-bit kernels and 585 RGB fixture cases. It checks Off/flat-field preservation, neutral RGB equality, ratio-rounding bounds, small frames, invalid selectors and unchanged borders. The production queue harness covers changing sharpness across waiting jobs, mixed output modes, DNG fallback and failures. Android unit tests cover settings, ISO mapping and truthful diagnostics.

These are host/build checks, not photographic or phone acceptance. Check actual skin, fine branches, noise and halos on the phone; do not claim magenta fringing is resolved.

1. Assemble into a fresh directory with `assemble.py`.
2. Run `build_native.py <tree> <NDK 27.0.12077973>`.
3. Build the Android debug APK and affected Android tests.
4. Run `package.py <tree> <built-apk> <accepted-2.27-apk> <build-tools-35.0.0> <delivery>`.

Source is committed locally and retained in the recovery archive. No public push was attempted: earlier automatic approval review blocked publication of the new firmware-derived bank; this task does not assume that publication was subsequently approved.
