M9Cam 2.56 SHADINGPERF1A — lens-shading speed candidate

Both renderers now precompute horizontal lens-shading lookup coordinates once per correction pass instead of recalculating them for every row. Shading strength, interpolation, headroom and rounding are unchanged. Actual before/after helpers matched exactly across 4,600 cases and 203,980,112 RAW samples, with 76 matching invalid-input cases.

The isolated 12 MP host shading pass used about 58% less time on the standard M9 path and 46% less on Monochrom. This is not a claim about total rendering time or phone performance. Only two renderer files and the version change; all subsequent photographic calculations, output, queues and crash fixes remain unchanged. Added coordinate storage is 64 KiB of array payload at width 4096.

Start here:
- patches/shadingperf1a/README.md — scope, results, recovery/build and phone comparison
- patches/shadingperf1a/HOST_PARITY_BENCHMARK.json — exact corrected RAW and host timing evidence
- patches/shadingperf1a/SOURCE_VERIFICATION.json — exact reversible optimisation and source boundaries
- patches/shadingperf1a/TEST_VERIFICATION.json — 44 app regression tests
- patches/shadingperf1a/assemble.py — reconstruct the complete pinned source chain
- patches/shadingperf1a/PACKAGED_VERIFICATION.json — native/assets/signature integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.56_SHADINGPERF1A.apk. Phone confirmation is pending.
Main remains accepted 2.55 at e8b1a4979cc9e20237b1d42a66037a006f127b85, including merged PRs #71–73. Three-shot admission/recovery and the 2.55 crash retest were confirmed on the phone. The accepted APK is M9Cam_2.55_THUMBUI1A.apk.
