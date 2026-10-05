# M9Cam 2.49 — Monochrom rendering performance

Monochrom inherited four M9 shading analyses whose results were never used or emitted: it returns its photograph before their consumers. Two analyses each cloned the full normalized RAW and repeated lens-shading correction. They ran even with diagnostic files disabled.

MONOPERF1A skips those four reports in the Monochrom branch. The physical shading pass remains unchanged. It also exposes existing normalization, demosaic and native-render timings and measures physical shading for phone diagnosis. The existing whole-render and JPEG timings remain available.

Only the Monochrom renderer and app version change. M9's renderer, all native processing, RAW normalization, actual lens shading, MHC demosaic, noise/detail processing, contrast curves, toning, sharpening, profiles, exposure, capture snapshots, JPEG encoding and linear DNG export retain the 2.48 implementation. Native libraries and assets are copied byte for byte from the signed 2.48 package.

## Evidence and limits

- `SOURCE_VERIFICATION.json` verifies the two-file delta and that reversing the four guards and diagnostic timing additions reproduces the entire previous renderer. It confirms that no removed report is consumed before the Monochrom return.
- `HOST_PARITY_BENCHMARK.json` records 265 passing cases: four Bayer patterns, four origin parities, four rotations, black/clipped/gradient/random RAW data, constant and spatial/channel-varying gain maps, degenerate dimensions, shading off, invalid-map rejection and two full-size frames.
- Actual parent/candidate pre-demosaic Java blocks and unchanged helper methods are compiled by `host_parity.py`. Only read-only Camera2 map/result accessors are adapted. Corrected RAW samples and every shading representation statistic are identical; gain maps are unmodified. This is a stage parity test, not a whole-JPEG test.
- At 4096×3072, skipping the two RAW clones avoids 50,331,648 bytes (48 MiB) of array allocations per frame, plus small report/histogram allocations. This describes allocations avoided, not measured peak memory or RSS.
- Host timing is recorded with three warmups and seven alternating paired runs. It is not an Android/phone benchmark or a claim about total capture time. Phone speed and visual confirmation remain pending.

M9 was inspected too. Its accepted path already contains preparation and phase-noise optimisations. The persistent colour route was previously rolled back after a phone colour regression; this release leaves that route unchanged. Phone timings should identify the next worthwhile M9 stage before further changes.

## Reconstruct, verify, build and package

Parent main: `9e38c4a6e762a76c1c03d23586ffd83c6de03b7f` (2.48, PR #66).

```sh
python3 patches/monoperf1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/verified/PhotonCamera_248
# Omit --parent to reconstruct the full pinned history.
python3 patches/monoperf1a/verify_source.py /absolute/verified/PhotonCamera_248 /absolute/new/PhotonCamera
python3 patches/monoperf1a/host_parity.py /absolute/verified/PhotonCamera_248 /absolute/new/PhotonCamera --json-jar /absolute/json-20250517.jar --output /absolute/host-parity
python3 patches/monoperf1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build
python3 patches/monoperf1a/test.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --java-agent /absolute/byte-buddy-agent.jar
python3 patches/monoperf1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.49_MONOPERF1A-debug.apk /absolute/M9Cam_2.48_MONOPROFILES1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Use JDK 17, SDK 36, build-tools 35.0.0, CMake 3.22.1 and NDK 27.0.12077973. The circularbar library also uses SDK 33. Run build and tests serially. `--offline` requires provisioned dependency/SDK caches. Never distribute the raw Gradle APK: packaging restores and verifies all 27 accepted native libraries and all 285 assets, signs with the existing app certificate and checks 16 KiB alignment. Version code 27249 installs over 2.48.

## Phone comparison

Use the same scene, lens, exposure, profile and output selection on 2.48 and 2.49. Let the phone cool between batches. Take one warmup and at least five shots per version. Compare `renderCoreElapsedMs`, `renderElapsedMs` and `jpegEncodeWriteElapsedMs` from diagnostic files; also assess capture-to-ready time with the same DNG options. Check bright edges, deep shadows, fine detail and toning. Check M9 still renders normally and switch back to Mono. Keep 2.48 as the comparison build until phone results are accepted.
