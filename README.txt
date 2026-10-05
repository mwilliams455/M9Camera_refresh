M9Cam 2.51 M9PERF1B — phone comparison build

M9 and Monochrom camera with independent profiles. This revision skips three setup report builders when diagnostic files are disabled, and allocates the M9 ARGB fallback buffer only when needed. An ordinary direct-rendered frame at RAW width 4096 avoids 6 MiB of Java array payload allocation. Photographic calculations and all accepted native libraries/assets are preserved. Monochrom's confirmed 2.49 speed improvement and M9's 2.50 optional image reports are retained.

Start here:
- patches/m9perf1b/README.md — changes, verification limits, build and phone comparison
- patches/m9perf1b/assemble.py — reconstruct the complete pinned source chain
- patches/m9perf1b/SOURCE_VERIFICATION.json — exact source-change boundary
- patches/m9perf1b/FALLBACK_VERIFICATION.json — 244 actual-source routing/allocation cases with deterministic adapters
- patches/m9perf1b/TEST_VERIFICATION.json — 34 app tests across eight suites
- patches/m9perf1b/PACKAGED_VERIFICATION.json — signed APK identity and integrity

This is an incremental source assembly/recovery repository, not an already-assembled Android project. Use the latest entry point above. Host routing checks do not establish a phone speedup. M9 2.51 performance and visual acceptance are pending. Malcolm reported a modest improvement with all diagnostics disabled in 2.50; no isolated version-to-version phone timing is claimed.

Parent source: 2.50, dad20828a772254b60ceb2e0b3145e5b07d0816d (draft PR #68, stacked on #67).
Comparison baseline: M9Cam_2.50_M9PERF1A.apk
Candidate package: M9Cam_2.51_M9PERF1B.apk
