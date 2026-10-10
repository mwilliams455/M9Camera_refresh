# M9Cam 2.71 TRACEREWIND1A

The user cannot release the camera shutter while the phone's screen recorder is running. Requiring simultaneous screen recording and photo capture therefore cannot collect the requested exposure evidence. The 10 October recording shows a planned ISO change from 282 to 119 at 1/30s around 14–18 seconds. The supplied trace covers a later shutter and stops at `still_result`, sequence 5, 0.546 seconds after the press. Its existing three-second pre-history misses that recording. The controller responsible for the recorded dip is not established.

This diagnostic candidate exports up to 30 seconds before the shutter from the existing metering, metadata and preview-pixel rings. The previous export requested only three seconds. All three collectors use the same camera and time range. The trace records its requested interval, collection time, app version and the fact that actual retained coverage may be shorter. Missing preview pixels are reported explicitly.

The history is included in the first trace snapshot, so analysis of the earlier preview does not depend on the final JPEG or post-capture trace updates arriving. This does not repair or diagnose incomplete exports. There are no additional GL reads, increased sampling rates or enlarged rings. Serialization stays on the existing trace worker. The larger pre-history increases trace size and serialization/export work after a photo. Actual coverage remains limited by existing capacities, camera switches, application lifecycle and time waiting for that worker.

## Capture-gate audit

The reviewed source contains no explicit external screen-recorder or MediaProjection capture veto. The shutter path includes camera/session readiness, render-queue admission, bracketing, autofocus and current displayed-exposure-plan checks. A missing current displayed plan waits and then reports an error after one second. These are possible stopping points, not a diagnosis of this device's blocked shutter. No gate or exposure safety policy is bypassed.

## Scope and checks

Parent: 2.70 MONORAWGAIN1A at `301a80733145f7d88decefdde7fc0388df1210a7`, draft PR #88. All 2.68–2.70 Monochrom changes are retained. Only the shutter trace serializer, a new regression test and app version metadata change. Exposure, rendering, shutter admission, AF/WB, UI, storage exporter and all native libraries/assets are unchanged.

`M9TraceRewindTest` exercises the production pre-history serializer with real metering rings. It verifies that an exposure dip twenty seconds before the photo survives, where the former three-second query contains only recovery. It also checks common metadata/pixel time boundaries, camera filtering, inclusive start/end, future exclusion, short uptime, missing collectors and the unchanged 128-row bound. Hardware-only collectors are substituted in one test. Android compilation and all 34 tests pass (five new and 29 inherited), with no failures, errors or skips. Actions run [38034703706](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38034703706) built source commit `91853e19f7ad0e9230886f431240736345a27d07`. `BUILD_VERIFICATION.json` records the run, artifact and test suites. `PACKAGED_VERIFICATION.json` records the final signed APK checks. All 27 native libraries and 285 assets match 2.70 byte-for-byte; package identity, signature, 16 KiB ZIP alignment and compiled menus pass. Device validation remains required.

## Phone procedure

1. Enable diagnostic saving and keep the camera open.
2. Screen-record a 10–15 second example of the brightness change. No photo is required during recording.
3. Stop screen recording, return to the camera and take one photo within about five seconds, keeping the same lens and scene.
4. Leave the camera open for 15 seconds, then send the recording and that photo's `M9_SHUTTERTRACE_…json`.

The trace requests the preceding 30 seconds; it cannot recover events already evicted from the bounded rings. This build provides a workable way to gather evidence. It does not claim to fix preview pumping or the blocked shutter during screen recording. Keep the PR as a draft; do not merge main before phone acceptance.

## Reproduce

`python3 patches/tracerewind1a/assemble.py /absolute/path/PhotonCamera_271` reconstructs the pinned chain. Optional `--parent` accepts the exact complete 2.70 tree. The dedicated GitHub Actions workflow compiles Android and runs the new test with inherited Monochrom diagnostic/output tests. `package.py` requires the verified 2.70 APK and retains all 27 native libraries and 285 assets byte-for-byte.
