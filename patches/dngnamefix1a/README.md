# M9Cam 2.52 — repair embedded DNG profile names

Malcolm reported the M9 save warning: RAW saved, but its Leica look could not be embedded. He had not installed 2.51.

The exporter constructs a name containing ` C:` plus the contrast label. The writer permits only ASCII letters, digits, spaces, underscores, periods and hyphens. The colon causes `IOException: Invalid profile name` before any storage access. This mismatch entered with the 2.27 contrast-menu patch and affects all 25 saturation/contrast combinations. It reproduces a failure producing the reported warning; the screenshot did not include the phone exception log.

The fix changes ` C:` to ` C-`. The writer validation remains intact. Apart from the version, this is the only source change from 2.51. Profile generation, colour/tone tables, physical RAW metadata, atomic replacement, JPEG rendering, exposure, Monochrom and save-status logic are unchanged. The two 2.51 performance improvements are included.

## Regression coverage

The older contrast export test substituted a writer without name validation. It verified profile generation but missed this integration failure. The new test always uses the real writer.

`verify_export.py` compiles the actual exporter, profile generator, TIFF writer, firmware-asset loader, save selection and save-status classes. Only Android logging and asset access use host adapters. Small synthetic RAW16 Bayer DNGs contain physical calibration tags; the test performs real profile generation, staging, verification and atomic replacement.

- Parent export reproduces `Invalid profile name`, preserves the original DNG byte for byte and raises the profile-warning bit.
- All 25 saturation/contrast combinations embed successfully in both RAW-only and RAW+JPEG selections: 50 successful exports.
- The test inspects the root IFD, profile name, look/tone dimensions, XMP name/digest and neutral editor settings. Original RAW and physical-tag bytes remain exact, except for the intended root pointer and DNG version update. Successful exports clear the profile warning in the real save-status class.
- Invalid contrast, missing target data and a failed renderer retain original RAW and report the profile warning. No staging files remain.
- 34 Android app tests in eight suites pass, including 2.51 diagnostic gates and existing profile/output-setting regressions.
- Exact source reversal proves only the name delimiter and version changed. The other 1,328 scoped files match 2.51.
- Clean reconstruction and signed packaging pass. All 27 native libraries and 285 image assets are retained byte for byte.

These are host integration tests of actual Java export code, not Android storage or Lightroom tests. RAW-only and RAW+JPEG cases exercise profile export and save status with synthetic capture metadata; they do not execute the Android camera or JPEG encoder. Phone confirmation remains pending.

## Recovery and build

Parent: `b8a21870f5ff6457b3cf9a347afff14da908cd48`, branch `codex/m9perf1b-v2.51`, draft PR #69, stacked on #68 and #67. These changes are not merged into main.

```sh
python3 patches/dngnamefix1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/verified/PhotonCamera_251
# Omit --parent to reconstruct the complete pinned chain.
python3 patches/dngnamefix1a/verify_source.py /absolute/verified/PhotonCamera_251 /absolute/new/PhotonCamera
python3 patches/dngnamefix1a/verify_export.py /absolute/verified/PhotonCamera_251 /absolute/new/PhotonCamera --json-jar /absolute/json-20250517.jar --output /absolute/export-check
python3 patches/dngnamefix1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build
python3 patches/dngnamefix1a/test.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --java-agent /absolute/byte-buddy-agent.jar
python3 patches/dngnamefix1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.52_DNGNAMEFIX1A-debug.apk /absolute/M9Cam_2.51_M9PERF1B.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Use JDK 17, SDK 36 plus SDK 33 for circularbar, build-tools 35.0.0, CMake 3.22.1 and NDK 27.0.12077973. Run Gradle build and tests serially. Packaging retains both libm9sharpness copies absent from a fresh Gradle output. Distribute the packaged APK.

## Phone confirmation

Install 2.52 directly over the currently installed build; 2.51 need not be installed first. In M9 mode, capture one RAW-only and one RAW+JPEG photo. Confirm save completes without the profile warning, then open the new DNG in the usual editor and check its embedded Leica look. Diagnostics may remain off. If a warning remains, the useful next evidence is `dngProfile1A.reason` from PRIMARY diagnostics: other storage/metadata failures still safely retain RAW.

This fix applies to new captures. Previously saved RAWs remain available but are not automatically rewritten.
