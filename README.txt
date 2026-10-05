M9Cam 2.50 M9PERF1A — phone comparison build

M9 and Monochrom camera with independent profiles. Monochrom's 2.49 speed improvement is retained; Malcolm confirmed it is faster on his phone. This revision makes three M9 report-only image analyses optional under the existing Extended M9 colour diagnostics switch. Photographic calculations and all accepted native libraries/assets are preserved.

Start here:
- patches/m9perf1a/README.md — findings, timing limits, build and phone comparison
- patches/m9perf1a/assemble.py — reconstruct the complete pinned source chain
- patches/m9perf1a/SOURCE_VERIFICATION.json — exact source-change boundary
- patches/m9perf1a/HOST_PARITY_BENCHMARK.json — 523 stage/report parity cases and isolated host timings
- patches/m9perf1a/INITIAL_TWO_CLASS_TIMING.json — retained contradictory initial timing; not a speedup claim
- patches/m9perf1a/TEST_VERIFICATION.json — app regression results
- patches/m9perf1a/PACKAGED_VERIFICATION.json — signed APK identity and integrity

This is an incremental source assembly/recovery repository, not an already-assembled Android project. Use the latest entry point above. Host diagnostic-work savings do not establish total phone speed. M9 2.50 performance and visual acceptance remain pending.

Parent source: 2.49, 45a88fdc28ced19419b7bc0cb4cf9a388bb91e3f (PR #67, not merged).
Comparison baseline: M9Cam_2.49_MONOPERF1A.apk
Candidate package: M9Cam_2.50_M9PERF1A.apk
