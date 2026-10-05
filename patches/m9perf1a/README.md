# M9Cam 2.50 — optional M9 image reports

M9 performed three read-only research analyses for every ordinary photograph: a RAW flat-field residual report, a second shading-decomposition report and a full-resolution finished-bitmap clipping scan. None of these report results selects exposure or contributes pixels to the photograph.

M9PERF1A puts those reports behind the existing Settings > Advanced > Extended M9 colour diagnostics switch, which defaults off. Explicit nonzero bridge/probe modes and skin-luma probes retain the reports. Normal diagnostic files still contain timing, exposure, RAW-tail, shading-normalization and existing renderer statistics. Skipped reports identify themselves as unmeasured; they do not invent zero measurements. The three new elapsed-time fields show their cost when enabled.

The separate alpha-zero shading-normalization probe remains unconditional because it feeds the real shading strength. Physical lens shading, exposure/TC20, AMaZE, colour, tone, noise, sharpening, JPEG encoding, DNG output and capture/profile snapshots are unchanged. All native libraries and image assets are retained byte for byte. Monochrom's 2.49 optimisation is retained unchanged; Malcolm confirmed on 5 October that Monochrom is definitely faster.

## Evidence and timing limits

`SOURCE_VERIFICATION.json` proves that reversing only the allowlisted diagnostic gates, skipped-report helper and diagnostic timings reproduces the entire 2.49 M9 renderer. Only that file, the app version and the diagnostic-setting summary change. The other 1,326 scoped source/asset files are identical, including all Monochrom processing and exposure controllers.

`host_parity.py` compiles actual parent/candidate RAW shading orchestration and finished-bitmap report code with read-only Camera2 and Bitmap adapters. All 523 cases pass: four Bayer patterns, four origin parities, four rotations, dark/clipped/gradient/random input, unity and spatial/channel-varying gain maps, diagnostics on/off, explicit probes, small/degenerate geometry and two full-size frames. Corrected RAW, shading normalization strength, representation statistics and finished ARGB contents are exact. The original reports are also exact when opted in. This does not execute Android JNI or JPEG encoding.

Timing requires care. An initial comparison of separately compiled parent/candidate classes was contradictory: 231.69 ms versus 309.76 ms. Those raw results are retained in `INITIAL_TWO_CLASS_TIMING.json`; they do not establish an optimisation speedup. Independent JVM optimisation of duplicate kernels is a possible confounder.

The subsequent isolation uses the SAME candidate class and photographic helper methods, toggling only these three reports. The audit-on report results are already verified equal to the parent. At 4096×3072, with three warmups and nine alternating paired runs, median timed work was 462.57 ms with reports and 334.00 ms without: 128.57 ms of avoidable host work. This excludes saturation audit, native colour and JPEG encoding and is not a version-to-version total render benchmark or a phone speed prediction. Enabling the actual extended-diagnostics switch also enables the existing saturation audit, outside this timing scope.

Normal shooting avoids one full-bitmap scan and 50,331,648 bytes (48 MiB) of bitmap readback at 12.6 MP. This is avoided copy traffic, not a 48 MiB allocation or peak-memory claim. There is no claimed phone speedup until the comparison build is tested.

## Recovery, build and package

Parent: 2.49 source commit `45a88fdc28ced19419b7bc0cb4cf9a388bb91e3f`, PR #67. It is not yet merged into main.

```sh
python3 patches/m9perf1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/verified/PhotonCamera_249
# Omit --parent to reconstruct the complete pinned chain.
python3 patches/m9perf1a/verify_source.py /absolute/verified/PhotonCamera_249 /absolute/new/PhotonCamera
python3 patches/m9perf1a/host_parity.py /absolute/verified/PhotonCamera_249 /absolute/new/PhotonCamera --json-jar /absolute/json-20250517.jar --output /absolute/host-parity
python3 patches/m9perf1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build
python3 patches/m9perf1a/test.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --java-agent /absolute/byte-buddy-agent.jar
python3 patches/m9perf1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.50_M9PERF1A-debug.apk /absolute/M9Cam_2.49_MONOPERF1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Use JDK 17, SDK 36 plus SDK 33 for circularbar, build-tools 35.0.0, CMake 3.22.1 and NDK 27.0.12077973. Builds/tests must run serially. Offline operation requires provisioned dependency caches. Packaging restores all 27 accepted native libraries, including both libm9sharpness copies absent from a clean Gradle build, and checks all 285 assets, signing, version identity and 16 KiB alignment. Do not distribute the raw Gradle APK.

## Phone comparison

Install 2.50 over 2.49. Keep Extended M9 colour diagnostics off for normal shooting. Use the same scene, lens, exposure, image profile and JPEG/DNG selections for comparison; use a warmup then at least five shots per build and let the phone cool. Save diagnostic files can stay on to collect `renderCoreElapsedMs`, `renderElapsedMs` and `jpegEncodeWriteElapsedMs`; it does not enable the extended reports. `imageReportPerformanceRevision=M9PERF1A` and `readOnlyImageAuditsExecuted=false` identify the new path. Compare colour, tone, fine detail and capture-to-ready time. M9 phone performance and appearance confirmation are pending. Monochrom should retain its already-confirmed speed improvement.
