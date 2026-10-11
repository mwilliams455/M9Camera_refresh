# M9Cam 2.85 UPSTREAMUI1A

This candidate integrates selected October 6 PhotonCamera gallery, preview and build
updates on top of 2.84. The EXIF panel reuses the gallery preview bitmap for GPU blur
with clamped edges and pan/zoom tracking. Histogram requests reject superseded decodes,
clear failures and reuse one compute helper. MainRenderer caches shader uniform
locations. circularbarlib now compiles against SDK 36 with its own saturation icon.

UPSTREAM_SELECTION.json records the exact commits and deferred work. This is a
selective integration, not a claim that all changes through PhotonCamera dev HEAD
are merged. The original upstream pin remains accurate for the underlying pipeline.
Java 17 and Actions v4 are already present in our build workflow. The library release
resource verification task remains enabled and is a required build check.

Twelve scoped files change, including version metadata and six gallery regression
tests; 1,355 remain byte-identical. Source verification also checks exact reverse
restoration of 2.84. Capture, exposure (including MONOAEREF1B), custom M9/Monochrom
menus, processing assets and native sources remain unchanged. No HDR/stacking,
vendor RAW-size change, native alignment update or settings reorganization is added.
The fingerprint scope now includes circularbarlib/build.gradle explicitly.

CI requires the 128 existing exposure/capture/profile tests, seven gallery thumbnail
tests, five renderer lifecycle tests and six histogram request regressions (146 total),
plus standalone library release resource verification. The final installer preserves
all 27 native libraries and 285 assets from the verified 2.84 APK. Packaging validates
menus, APK identity, v2 signature, CRCs, SHA-256 and 16 KiB alignment.

Device validation remains pending. Install over 2.84, retry Monochrom MOTION on the
affected lens, then open the EXIF panel and swipe/zoom between photos. Check histogram
updates and that the panel background follows the displayed photo.

## Verified installer

CI passed all 146 focused tests with zero failures, errors or skips. Standalone
`circularbarlib:verifyReleaseResources` also passed.

[Download M9Cam-2.85-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38163122084/artifacts/11711241377).
Extract the ZIP and install `M9Cam_2.85_UPSTREAMUI1A.apk` over 2.84.

Built commit: `b7f8bbf229e897d070f7f1229a504b17ede1f63c`; run `38163122084`.
The downloaded archive passed its GitHub digest, CRC, identity, v2 signature,
alignment and byte-for-byte native-library/asset checks. See CI_VERIFICATION.json,
PACKAGED_VERIFICATION.json and GITHUB_DELIVERY_VERIFICATION.json.

APK SHA-256: `ea53e03cb320d9555837e031a2ea9ff4412cbf247731cf850ce738a27768d52b`.

PR #103 remains a device-validation candidate. This integrates the selected upstream
files on the current candidate branch; it does not finalize the earlier draft chain
into main.
