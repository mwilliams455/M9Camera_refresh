M9Cam 2.59 PREVIEWSETTLE1A — confirmed lower-target exposure settling

The ordinary Auto exposure descent previously waited for two fresh samples before every quarter-stop reduction toward the same target. This candidate keeps the initial confirmation, then continues at the existing 0.25 EV per fresh sample until that target changes or is reached. Invalid evidence and manual EV clear the transition. Highlight safety remains immediate.

A synthetic 0.75-to-0 EV transition now takes four fresh meter samples instead of six. Candidate host checks pass: 1,472 assertions/checks across inherited exposure policy, highlight protection, subject headroom and new Photo/Motion transition tests. These are host checks, not phone timing measurements.

Only the Auto transition logic and version metadata change. Targets, positive acquisition, frame pairing, probe cadence/freshness, ISO allocation, AE-L, WB, saved JPEG/DNG rendering, native code/assets, Monochrom, queues and crash fixes remain unchanged. A capture during settling can use a different exposure because the shutter continues to follow the displayed plan.

Start here:
- patches/previewsettle1a/README.md — evidence, scope, recovery and phone comparison
- patches/previewsettle1a/HOST_VERIFICATION.json — production Auto/tap class results
- patches/previewsettle1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/previewsettle1a/assemble.py — complete pinned source reconstruction
- patches/previewsettle1a/PACKAGED_VERIFICATION.json — APK integrity checks

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.59_PREVIEWSETTLE1A.apk.
Parent is 2.58 at fc4e53099c939e93be3bbe4fd3686ec9c5698a8e, including PR #76 and its #75/#74 predecessors. Full Android build and packaged APK integrity checks passed. Phone validation is pending. This candidate does not merge main.
