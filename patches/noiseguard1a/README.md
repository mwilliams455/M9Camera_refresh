# M9Cam 2.91 NOISEGUARD1A

Parent: verified 2.90 CCTGUARD1A. Malcolm reported on 2026-10-16 that it looks the same in his photos so far. This is a provisional visual pass for those photos, not all-lens/mode acceptance.

The inherited noise-strength setting is a string parsed as float, with an existing UI range of -6..+4 and default 0.0. SettingsManager now validates only that key at the read boundary. Missing, malformed, non-finite, out-of-range or wrongly typed stored values resolve to the established default (or a valid explicit caller default). Valid fractional values and signed zero keep their exact float representation. Reads do not rewrite preferences and unrelated float settings keep their existing behavior.

PostPipeline validates its three-channel model and both final noise coefficients before publishing either. It rejects missing data, non-finite doubles, overflow when converting to float, float-sum overflow, invalid multipliers and final float overflow. Invalid models take the existing processing-error path before OpenGL setup; no substitute noise model or huge clamped coefficient is invented. Both regular legacy rendering and its optional gain-map route call this guarded method. This change does not enable HDR.

Valid calculations retain the original per-channel float conversion, addition order, division by 3.f, double Math.pow multiplier and final float narrowing. The existing Float.MIN_NORMAL floor is preserved, including for finite negative/zero and subnormal model values. The primary M9/Monochrom renderer, capture, exposure, native and asset sources are unchanged.

Verification:
- 22 guard tests and nine boundary tests cover saved settings and actual PostPipeline publication. Android CI runs these using Robolectric; this does not replace phone testing.
- The JDK host probe runs 31 checks with explicit stubs, then compares 100,000 noise-model results with the verbatim v2.90 computeNoise method by exact float bits. It also checks 100,000 valid stored-strength strings for parity.
- Full reconstruction, scoped fingerprints and exact reverse-patch restoration pass. Seven scoped files change (two existing production files, two new helpers, two new test classes, version metadata); 1,370 remain unchanged.
- Android installer gate selects 266 tests; broader regression/CodeQL gate selects 269. Remote results are recorded separately after completion.
- Packaging requires all 27 native libraries and 285 assets to match the signed v2.90 APK byte for byte, the accepted signing certificate, compiled menus/resources and 16 KiB ZIP alignment.

Reconstruct: `python3 patches/noiseguard1a/assemble.py DEST --parent VERIFIED_290` (omit parent to reconstruct the pinned chain). Verify: `verify_source.py VERIFIED_290 DEST`. Host probe: `host_probe.py DEST VERIFIED_290`.

This candidate is stacked on the v2.90 draft; main remains v2.88. The unused SmartNR node and debug-overlay text warning are outside this change.
