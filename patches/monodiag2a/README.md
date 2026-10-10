# M9Cam 2.69 MONODIAG2A candidate

Parent: 2.68 MONODIAG1A, commit `096723ea62eb77ca09087ff31efa18f54c8d9d1e`.

The 11:19:27 phone capture produced its priority Mono primary report but its
preview/capture pair remained unavailable. The supplied burst manifest records
an 87,615-byte `mono_live_pair` payload and 1,673 pending individual exports;
1,670 entries had been recovered from earlier sessions. A manifest proves private
staging, not public delivery. The parent gave `monochrom_primary` priority while
leaving `mono_live_pair` on the ordinary historical-export worker.

This candidate gives the pair the same fresh priority route and orders recovered
priority reports newest first. Existing queued files remain preserved. It also
copies the exact camera-ID/sensor-timestamp-associated pair into `_MONO_PRIMARY.json`
at the existing metadata persistence boundary. The primary's `monoLivePair` survives
rejection of its separate sidecar. Missing capture metadata or an unmatched callback
is reported explicitly instead of substituting current preview state.

Three production Java files, version metadata, and one new regression test differ.
All 1,335 other scoped files, including photographic rendering, exposure, AF/WB,
shaders, native code, and assets, are unchanged. This is a diagnostic-delivery repair;
it does not claim to resolve the Mono Motion brightness mismatch.

## Verification

Source reconstruction/fingerprints and exact reverse patch pass. The transport
harness uses the actual shared spool, filesystem and executors, seeds 1,673 ordinary
reports, verifies newest recovered Mono evidence and blocks the ordinary worker
while checking fresh primary and live-pair delivery. It also retains the existing
preference-off/background/resume preservation checks. Android tests verify exact
capture association, separate-sidecar rejection, camera mismatch, missing metadata,
and compatibility for existing metadata callers. All 19 Android/Robolectric tests
pass, including the five new association/embedding tests; the Android build passes.
The 19 Mono transport assertions and 225 inherited spool assertions pass, and CI
also passes the 69 inherited preference assertions. The signed package passes its
certificate, version, compiled-menu, and 16 KiB alignment checks. All 27 native
libraries and 285 assets match the 2.68 APK byte for byte. See the accompanying
verification JSON files. Phone acceptance remains pending.

## Reproduce

```sh
python3 patches/monodiag2a/assemble.py /absolute/PhotonCamera_269 --parent /absolute/PhotonCamera_268
python3 patches/monodiag2a/verify_source.py /absolute/PhotonCamera_268 /absolute/PhotonCamera_269
python3 patches/monodiag2a/transport_test.py /absolute/PhotonCamera_269 --output /absolute/mono269-host
python3 patches/monodiag2a/build.py /absolute/PhotonCamera_269 --sdk /absolute/android-sdk --output /absolute/build269
python3 patches/monodiag2a/package.py /absolute/PhotonCamera_269 /absolute/build269/app/outputs/apk/debug/M9Cam_2.69_MONODIAG2A-debug.apk /absolute/M9Cam_2.68_MONODIAG1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables269
```

Omit `--parent` to reconstruct the full pinned chain. Retain JDK 17 / SDK 36 /
build-tools 35.0.0 / NDK 27.0.12077973 / CMake 3.22.1. Only distribute the final
packaged APK, which preserves all 27 parent native libraries and 285 assets.

## Phone check

Install the update, keep Save diagnostic files enabled, and take one Mono Motion
3x photo. Remain in the app briefly. Send the new `_MONO_PRIMARY.json` with its
JPEG and preview screenshot. The primary now contains `monoLivePair`; finding a
separate live-pair file is unnecessary. The requested destination is
`DCIM/PhotonCamera/Raw`. Old queued reports are preserved and newest priority
reports are considered first on resume/restart.
