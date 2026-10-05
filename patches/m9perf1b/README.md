# M9Cam 2.51 — diagnostic early exits and lazy fallback storage

The M9 diagnostics-off path still computed device, RAW shading metadata and historical source-calibration reports, then serialized them before the output writer discarded them. The ordinary direct-Bitmap colour path also allocated a Java ARGB fallback array that it did not use.

M9PERF1B addresses only those two opportunities:

- `M9DevicePortAudit1A`, `M9RawShadingAudit1A` and `M9SourceCalibrationAudit1A` return before inspecting metadata or loading historical calibration when Save diagnostic files is disabled. They return explicit unmeasured markers (`executed=false`, `valid=false`, `reason=diagnostic_files_disabled`). Their enabled report bodies are unchanged. This is not a claim that all renderer telemetry is eliminated: exposure decisions, DNG profile data, crash reporting and the existing extended-diagnostics policy remain intact.
- The production M9 block loop allocates the ARGB buffer only if the direct Bitmap path is unavailable or rejected. A late rejection retains completed direct blocks and uses one reusable buffer for subsequent fallback blocks. At RAW width 4096 and block height 384, an ordinary all-direct frame avoids 6,291,456 bytes (6 MiB) of Java array payload allocation. Other widths scale accordingly. `nativeColorArgbFallbackAllocatedBytes` records zero or the allocation size in the existing diagnostic result.

No exposure, lens shading, demosaic, colour, tone, noise, sharpening, JPEG, DNG, save queue, settings UI or Monochrom processing changes. The accepted Monochrom 2.49 improvement and M9 2.50 report gates remain in place. The previously rolled-back persistent colour scheduler stays disabled.

## Verification and limits

- Source verification reverses only the explicit early gates, lazy allocations, allocation statistic and version strings, then compares all affected production files with 2.50. The enabled report bodies and all photographic operations match exactly; 1,324 other scoped files are unchanged.
- 34 Android app tests in eight suites pass. New tests prove disabled audits do not reach their metadata/calibration dependencies or logging, and re-enabling diagnostics restores report execution.
- `host_fallback.py` compiles the actual parent/candidate block orchestration. All 244 routing cases pass, including rejection on the first, middle and last block, copied-input fallback, all four orientations, odd dimensions and partial blocks. The normal 4096×3072 case allocates 6 MiB before and zero after. Deterministic native and Bitmap adapters test routing and allocation; this is not a photographic JNI parity test or a phone performance benchmark.
- Clean patch reconstruction matches all 1,330 scoped files in the built source.
- Android build and signed packaging pass. All 27 accepted native libraries and 285 image assets are byte-identical to 2.50; application ID, signing certificate and 16 KiB alignment are preserved.

There is no claimed time saving until phone testing. Malcolm reported a modest improvement with all diagnostics disabled in 2.50; that observation does not isolate the 2.50 change from report-writing overhead.

## Recovery and build

Parent: `dad20828a772254b60ceb2e0b3145e5b07d0816d`, branch `codex/m9perf1a-v2.50`, draft PR #68. Parent is stacked on 2.49 draft PR #67. These changes are not merged into main.

```sh
python3 patches/m9perf1b/assemble.py /absolute/new/PhotonCamera --parent /absolute/verified/PhotonCamera_250
# Omit --parent to reconstruct the complete pinned chain.
python3 patches/m9perf1b/verify_source.py /absolute/verified/PhotonCamera_250 /absolute/new/PhotonCamera
python3 patches/m9perf1b/host_fallback.py /absolute/verified/PhotonCamera_250 /absolute/new/PhotonCamera --output /absolute/fallback-check
python3 patches/m9perf1b/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build
python3 patches/m9perf1b/test.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --java-agent /absolute/byte-buddy-agent.jar
python3 patches/m9perf1b/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.51_M9PERF1B-debug.apk /absolute/M9Cam_2.50_M9PERF1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Use JDK 17, SDK 36 plus SDK 33 for circularbar, build-tools 35.0.0, CMake 3.22.1 and NDK 27.0.12077973. Run Gradle build and tests serially. Packaging retains all 27 baseline libraries, including the two libm9sharpness copies absent from a fresh Gradle output. Distribute the packaged APK, not the raw Gradle APK.

## Phone check

Install 2.51 over 2.50. Keep Save diagnostic files and Extended M9 colour diagnostics off for the speed comparison, and use the same lens, exposure, profile and JPEG/DNG output selection. Compare a warmup followed by several shots of the same scene, with a cool phone. Check colour, tone and detail as well as time until ready. Re-enable Save diagnostic files briefly when report inspection is needed; the three setup reports must appear again. There is no new menu option.

Follow-on opportunities identified but not implemented: exact coordinate precomputation in lens shading, JPEG-only completion overlap, and prompt Monochrom DNG publication. The first is pixel-sensitive and requires stage parity; the latter two concern save completion and durability.
