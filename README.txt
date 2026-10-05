M9Cam 2.49 MONOPERF1A — phone comparison build

M9 and Monochrom camera with the 2.48 Monochrom image profiles. This revision removes four unused inherited M9 shading reports from Monochrom rendering. Actual photographic operations and all accepted native libraries/assets remain unchanged.

Start here:
- patches/monoperf1a/README.md — findings, limits, build and phone comparison
- patches/monoperf1a/assemble.py — reconstruct the complete pinned source chain
- patches/monoperf1a/SOURCE_VERIFICATION.json — exact source-change boundary
- patches/monoperf1a/HOST_PARITY_BENCHMARK.json — 265 stage parity checks and host timings
- patches/monoperf1a/TEST_VERIFICATION.json — app regression results
- patches/monoperf1a/PACKAGED_VERIFICATION.json — delivered APK identity and integrity

This is an incremental source assembly/recovery repository, not an already-assembled Android project. Use the latest entry point above. Phone speed and visual confirmation of 2.49 remain pending. Host stage timings are not total phone-render timings.

Comparison baseline: M9Cam_2.48_MONOPROFILES1A.apk
Candidate package: M9Cam_2.49_MONOPERF1A.apk
