# M9Cam 2.58 PREVIEWPAIR1A

Candidate for the remaining M9 viewfinder brightness jumps in backlit scenes. Parent is 2.57 PREVIEWPROBE1A at `5807641762f5023a64ef7b846670b0b5b0a777a6` (draft PR #75), including the 2.56 rendering improvement in PR #74.

The user reported an improved viewfinder with 2.57, followed by repeated abrupt darkening in a backlit Motion preview. Limiting Auto ISO to 1200 and enabling AE-L together helped, but this does not isolate the cause. Normal Auto should not require those workarounds to remain stable.

## Fault and change

The renderer previously applied the newest immutable exposure state to the texture returned by `SurfaceTexture.updateTexImage()`. Those can belong to different camera frames. During ISO/shutter changes, the newer frame's intended/observed exposure ratio can therefore brighten or darken older pixels incorrectly. It can also invalidate the neutral-reference meter sample.

`M9PreviewFrameHistory1A` retains up to 16 immutable metadata states and selects an exact texture-timestamp match when available. A historical match must be no older than 150 ms since publication and no more than 150 ms behind the latest camera timestamp. Camera, mode, EV, manual exposure controls, Auto ISO control identity, AE-L generation, and source readiness/continuity must agree. Control changes and surface recreation discard history.

One selected state is shared by rendering, both preview probes, Draw diagnostics and the existing shutter authority. Selection adds no waiting, frame buffering, nearest-frame guess or per-draw allocation. Missing, expired, unsupported or foreign matches retain the parent's latest-state fallback. Existing Draw diagnostics retain the texture/result timestamp match and delta.

Only MainRenderer, the new history class and app version metadata change. Auto exposure targets, ISO/shutter allocation, highlight safety, AE-L logic, probe scheduling and evidence freshness rules are unchanged. Saved JPEG/DNG renderers, shaders, native code, assets, Monochrom, save queues and recent crash fixes are unchanged.

This fixes a reproducible pairing error; it does not establish that the error is the sole cause of the phone symptom. Existing stale-meter and TC20 reset paths remain. Aligning the plan with the displayed frame can also align the existing shutter authority with that earlier plan within the bounded window; unchanged saved rendering code does not imply identical capture exposure in every timing scenario.

## Verification

- Host regression: 272 assertions passed, compiling the production history, frame state, exposure plan and TC20 math. Tests cover exact matches, fallback, expiry boundaries, control/owner transitions, duplicate timestamps, capacity eviction, surface reset, Photo/Motion and concurrent publication/selection. Only unrelated GPU source metadata, JSON and bracket containers are stubbed.
- 112 synthetic linear exposure cases: worst mismatch was 2.0 EV with parent-style metadata selection and 0.0 EV with matching metadata. These are isolated exposure-multiplication tests, not measurements from the phone or full colour/JPEG simulations.
- Source verification: 1,329 other scoped files unchanged; reversing the integration exactly restores the parent. A fresh reconstruction matches all 1,332 scoped build-source files.
- Full Android debug build passed: Gradle 8.11.1, JDK 17.0.20.1+1, SDK 36, build tools 35.0.0, NDK 27.0.12077973. No Android instrumentation or phone tests were run.
- Packaged APK: all 27 native libraries and all 285 assets byte-identical to 2.57; accepted signing certificate, version 27258, compiled menus and 16 KiB alignment verified.

Reports: `HOST_VERIFICATION.json`, `SOURCE_VERIFICATION.json`, `RECONSTRUCTION_VERIFICATION.json`, `BUILD_VERIFICATION.json`, `PACKAGED_VERIFICATION.json`.

APK: `M9Cam_2.58_PREVIEWPAIR1A.apk`, 119,585,589 bytes. SHA-256:

```text
5bfb698902fae69e8c986d7bbca3f98ab042eea1d95b52ea52c06e7156c32275
```

## Recovery and build

Run from this repository root:

```bash
python3 patches/previewpair1a/assemble.py /absolute/path/PhotonCamera_258
python3 patches/previewpair1a/host_test.py /absolute/path/PhotonCamera_258 --output /absolute/path/host258
python3 patches/previewpair1a/build.py /absolute/path/PhotonCamera_258 --sdk /absolute/path/android-sdk --output /absolute/path/build258 --offline
python3 patches/previewpair1a/package.py /absolute/path/PhotonCamera_258 /absolute/path/build258/app/outputs/apk/debug/M9Cam_2.58_PREVIEWPAIR1A-debug.apk /absolute/path/M9Cam_2.57_PREVIEWPROBE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables258
```

The assembler can optionally use `--parent /absolute/path/verified_PhotonCamera_257`. Otherwise it reconstructs the pinned parent through the existing recovery chain. Build dependencies must already be provisioned for `--offline`; `JAVA_HOME` can select JDK 17. Package against the accepted 2.57 APK whose SHA-256 is `83f204978d14f05b6f8e0c1132bf5ec074816ef008d9c787fe613e43d8763a23`. Distribute the packaged output; the raw Gradle APK does not retain the accepted native-library baseline.

## Phone comparison

Start with M9, Motion mode, 1x, Auto ISO/shutter, EV 0, AE-L off and the usual Auto ISO ceiling restored. Hold the same backlit composition for at least 15 seconds and check for abrupt darkening or repeated pulsing. Repeat in Photo mode, then move from bright to dark and hold still to check settling. Compare a saved capture with the settled preview and check lens/EV/AE-L changes do not leave an old preview state behind.

If the symptom remains, record a short clip and export existing M9 diagnostics from the same run so texture/result pairing and stale-evidence resets can be distinguished. ISO 1200 and AE-L remain optional photographic controls, not required settings for this test.

Phone validation is pending. This candidate is stacked on 2.57; main is not merged by this change.
