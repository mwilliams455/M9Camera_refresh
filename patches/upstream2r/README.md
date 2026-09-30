# M9Cam 2.09 UPSTREAM2R

This comparison build merges PhotonCamera `dev` at
`4ee108e169496f429c0afa0cc33e57bb6b2ec724` into the delivered M9 2.08
PHOTONBOUNDARY2Q source. The previous Photon base was
`f0e6425d2509fb8ab834d5d3af593183038b778c`.

The purpose is to test whether the upstream capture, allocation, metadata and
DNG changes alter the reported magenta fringing. This is not a demonstrated
fringing fix. The earlier RAW boundary captures matched the saved DNG pixels;
that finding did not clear every part of Photon or the camera pipeline.

## Merge and comparison scope

- Imports upstream capture/AF, native allocation, DNG lifetime/stream handling,
  preview and gallery work. Eighteen overlapping files were resolved against
  the M9 route and the new upstream interfaces.
- Retains the M9 capture/exposure intent, physical-result/CFA selection,
  tap metering, preview colour transform and RAW boundary diagnostics.
- Keeps 111 M9 source/asset files identical to 2.08, including the native AMaZE
  renderer, noise processing, colour transforms and tone data. The render queue
  adds only an upstream-build identity record to its existing diagnostic JSON.
- Uses the newly built Photon native libraries, but reuses the exact two
  `libm9color.so` binaries from the delivered control APK. The package script
  verifies every M9 asset and every other payload entry after signing.
- Disables digital RAW/preview crop on the M9 capture route. Upstream's new
  cropped RAW layout has not been adapted to the M9 full-sensor shading
  contract. Physical lens switching remains available at native field of view.
- Retains the bounded M9 journal implementation. Pins the four native build
  headers that upstream otherwise downloads at configure time, with SHA-256
  checks. Rounded preview corners are disabled during offscreen M9 metering
  and evidence passes so they cannot mask probe pixels.

The upstream GPU AMaZE change does not replace M9's separate native AMaZE
implementation. The latter is intentionally unchanged for this comparison.

## Reproduce

Use JDK 17 and an Android SDK with platform 36, build tools 35.0.0,
NDK 27.0.12077973 and CMake 3.22.1. From the wrapper repository root:

```sh
python3 patches/upstream2r/assemble.py PhotonCamera
cd PhotonCamera
chmod +x gradlew
./gradlew :app:assembleDebug :app:testDebugUnitTest --tests '*ZoomControllerTest' --tests '*M9Upstream2RZoomTest'
cd ..
python3 patches/upstream2r/package.py PhotonCamera CONTROL.apk "$ANDROID_HOME/build-tools/35.0.0" M9_UPSTREAM2R_DELIVERY
```

`CONTROL.apk` must be the delivered 2.08 APK or the 2.07 CAPTURECOLOR1A APK;
their M9 colour libraries and M9 assets are identical. Accepted full APK hashes
are enforced in `package.py`. The GitHub workflow obtains 2.07 from its existing
build artifact. Keep that control artifact available for future packaging.

`assemble.py` applies the complete binary overlay to the pinned upstream
commit and checks all 1,183 tracked source-file hashes. The manifest also
records the local source merge commit and both parents. It is a source
reconstruction guarantee, not a promise of byte-identical Gradle APK output.

## Local validation on 2026-09-30

- Java and native compilation and APK assembly passed.
- 40 upstream zoom tests and 3 M9 crop/lens compatibility tests passed.
- The unchanged boundary helper passed 22 host checks, including a 12 MP RAW
  buffer, single-bit mutation, nanosecond timestamp mismatch and cursor safety.
- A clean pinned upstream worktree plus the overlay matched all 1,183 files.
- Packaging checks the update identity, existing signing certificate, 16 KB
  ZIP alignment, frozen M9 source/assets/native libraries, diagnostic markers
  and preservation of the remaining newly built payload.

Host tests do not exercise the phone camera, GL driver, AF or hardware lens
switching. Device capture and fringing comparison remain pending.

## First device test

Install `M9Cam_2.09_UPSTREAM2R.apk` as an update to M9Cam. It uses the existing
package `com.m9project.m9cam.photon`, signing certificate and a higher version
code (27209); displayed version is `2.09-m9upstream2r-photon4ee108e`.

Start with the physical main camera at 1x, Auto WB and 4:3. Repeat a scene with
the same visible fringe, keeping the existing M9 rendering settings. Confirm
preview, tap focus/metering and saving work. Preserve the original full-size
JPEG, DNG and matching PRIMARY JSON together in a ZIP for comparison.
`renderer.photonUpstream2R` identifies this build, and
`renderer.photonBoundary2Q` retains the RAW handoff evidence.

Keep 2.08 and its capture files as the control. Android may reject a lower
version-code APK as a normal update; no downgrade behavior has been tested.
