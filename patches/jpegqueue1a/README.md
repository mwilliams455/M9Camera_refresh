# M9Cam 2.53 — JPEGQUEUE1A

Test candidate based on main `5d8994f0266557747d1120764a88edd2f88d3ca4` (2.52). Malcolm confirmed the 2.52 RAW profile-name fix and faster rendering before that version was merged. Phone validation of 2.53 is pending.

## Behaviour

M9 JPEG-only captures no longer wait for EXIF/publication on the render worker. Before handing off, the worker snapshots all frame-dependent diagnostics into text. A static lightweight completion object carries only paths, save status, strings, timing values and queue telemetry. The render worker closes its RAW frame and releases capture capacity while EXIF finishes.

Completion runs on the existing EXIF executor: one active save, two waiting. Saturation still finalizes synchronously on the caller to preserve outputs and bound memory. Save status and bracketing completion occur after the EXIF/publication attempt, not at render completion. Failures retain the existing JPEG/processing issue reporting. No extra executor, larger capture queue or retained image buffer was introduced.

RAW-only and RAW+JPEG keep the existing DNG worker and JPEG-before-DNG publication order. Monochrom uses the unchanged three-argument finalizer submission API. The shared finalizer gained an optional completion callback; EXIF content, JPEG encoding, colour, exposure, contrast, saturation, sharpness, noise reduction and native photographic code are unchanged. All 2.52 performance changes and its RAW fix remain included.

Expected benefit: better repeated JPEG capture throughput, dependent on how long EXIF/publication takes on the phone. No phone speed measurement is claimed. This does not reduce rendering computation or add a durable restart-recoverable save queue.

## Verification

- `SOURCE_VERIFICATION.json`: only app version and the two queue classes changed; 1,327 other scoped files unchanged. DNG worker executable body and EXIF write/publication body preserved.
- `QUEUE_VERIFICATION.json`: 13 real-queue host scenarios using deterministic Android/renderer/storage adapters: delayed EXIF, delayed publication, full queues and renderer rejection, RAW-only, RAW+JPEG, bracketing, 250 rapid completion callbacks, throwing callback recovery, EXIF/publication/render failures, missing EXIF. Checks exact frame close ownership, no early success, per-capture diagnostics, bounded fallback and settings frozen at enqueue. These are concurrency/ownership tests, not photographic output tests.
- `TEST_VERIFICATION.json`: 34 Android app regression tests in eight suites passed.
- `RECONSTRUCTION_VERIFICATION.json`: 1,330 reconstructed source/resource files match the built tree exactly.
- `PACKAGED_VERIFICATION.json`: signed upgrade APK, all 27 native libraries and 285 assets byte-identical to accepted 2.52, matching certificate and 16 KiB alignment.

## Recover and build

This is an incremental recovery repository; use its pinned assembly chain. From a workspace containing this repository and the required Android toolchain:

```bash
python3 M9Camera_refresh/patches/jpegqueue1a/assemble.py PhotonCamera_253
# Or add --parent /path/to/verified/PhotonCamera_252.
python3 M9Camera_refresh/patches/jpegqueue1a/verify_source.py PhotonCamera_252 PhotonCamera_253
python3 M9Camera_refresh/patches/jpegqueue1a/verify_queue.py PhotonCamera_253 --json-jar /path/to/json-20250517.jar --output host-jpegqueue1a
python3 M9Camera_refresh/patches/jpegqueue1a/build.py PhotonCamera_253 --sdk /path/to/android-sdk --output build253
python3 M9Camera_refresh/patches/jpegqueue1a/test.py PhotonCamera_253 --sdk /path/to/android-sdk --output build253 --java-agent /path/to/byte-buddy-agent.jar
python3 M9Camera_refresh/patches/jpegqueue1a/package.py PhotonCamera_253 build253/app/outputs/apk/debug/M9Cam_2.53_JPEGQUEUE1A-debug.apk /path/to/M9Cam_2.52_DNGNAMEFIX1A.apk /path/to/android-sdk/build-tools/35.0.0 deliverables253
```

Use the packaging step, not the raw Gradle APK: it preserves the accepted native library set. `manifest.json` pins source and patch hashes. The build needs JDK 17, SDK 36/33, build-tools 35, NDK 27.0.12077973 and CMake 3.22.1, as in 2.52.

## Phone check

Install `M9Cam_2.53_JPEGQUEUE1A.apk` over 2.52. In M9 JPEG-only mode take 5–6 consecutive photos as the shutter permits. Check responsiveness, final photo count, orientation and normal gallery/save-indicator behaviour. Try exposure bracketing once and a RAW+JPEG shot to check the retained RAW profile fix. Compare with 2.52 using the same diagnostics settings. No lens-shading optimisation is included.

New optional diagnostic fields identify `JPEGQUEUE1A`, the completion thread and whether actual renderer release was observed. If EXIF finishes before release is recorded, timing explicitly reports the handoff boundary rather than pretending it measured exact release time.
