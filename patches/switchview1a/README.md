# M9Cam 2.54 — SWITCHVIEW1A

Camera-view callback lifetime fix, based on 2.53 JPEGQUEUE1A (`2d153d946e05c0fb93807d4cdd9669f2752bb590`, draft PR #71). Main remains the accepted 2.52 baseline. The user confirmed 2.53 admits three consecutive captures and resumes capture after a brief pause, then reported frequent app exits while switching rendering modes. Phone confirmation of this fix is pending.

## Evidence and cause

The supplied video shows an M9 photo saved, a switch to Monochrom, a Monochrom photo saved, and an app exit shortly after switching back to M9. It does not expose the exception.

The supplied exit report was exported by **2.50 at 06:50 UK time on 5 October 2026**. It includes an older **2.48 Java crash at 20:31:52 UK time on 4 October**:

```
NullPointerException: cameraFragmentBinding is null
CameraFragment.syncLensClusterOffset(CameraFragment.java:734)
CameraFragment$2.onPreDraw(CameraFragment.java:636)
```

This is historical evidence, not a report of the new video. Its latest exit-history records describe package updates and task removal, rather than identifying the latest crash. However, the same unguarded code remained in 2.53. The added test reproduces the exact exception against unchanged 2.53 production code by invoking a retained pre-draw listener after Activity recreation while a retired manual panel changes geometry. `PARENT_REPRODUCTION.json` records that expected failure. This establishes a live code bug; it does not prove every reported phone exit has that cause.

The old cleanup looked up the root's observer during destruction. A detached view can return a different observer from the attached window. Also, a dispatch can already have snapshotted the listener before removal. Its callback could then dereference a binding that onDestroy had cleared.

## Change

- Register lens pre-draw callbacks when the root attaches; retain the attached observer and remove from that exact observer on detach/destruction.
- Invalidate panel callbacks at the start of onDestroyView, before binding/controller teardown.
- Ignore late lens-offset, panel-blur and manual-dome updates for a retired view, including callbacks already copied into a dispatch.
- Keep the live control geometry calculations unchanged.

Only CameraFragment production code, the lifecycle tests and the app version change. All photographic processing, preview colour/exposure calculations, JPEG/DNG saving, 2.53 queue improvements and the 2.52 RAW profile fix remain unchanged. No lens-shading optimisation is included.

## Verification

- Parent reproducer: exact null-binding crash in syncLensClusterOffset with 2.53 production code.
- `TEST_VERIFICATION.json`: 36 tests across eight suites. Four lifecycle tests cover recreation in both directions, stale preview updates, stale lens/panel callbacks, attached observer cleanup and live lens controls still moving normally. Android/Robolectric tests mock GPU/camera hardware; phone retest remains required.
- `SOURCE_VERIFICATION.json`: only three scoped files changed; 1,327 other source/resource files unchanged. Lens geometry math, preview/capture callbacks and save queues preserved.
- `RECONSTRUCTION_VERIFICATION.json`: all 1,330 scoped reconstructed files match the built tree.
- `PACKAGED_VERIFICATION.json`: upgrade signature, identity, 16 KiB alignment; all 27 native libraries and 285 assets byte-identical to 2.53.

## Recover/build

```bash
python3 M9Camera_refresh/patches/switchview1a/assemble.py PhotonCamera_254
# Or add --parent /path/to/verified/PhotonCamera_253.
python3 M9Camera_refresh/patches/switchview1a/verify_source.py PhotonCamera_253 PhotonCamera_254
python3 M9Camera_refresh/patches/switchview1a/test.py PhotonCamera_254 --sdk /path/to/android-sdk --output build254 --java-agent /path/to/byte-buddy-agent.jar
python3 M9Camera_refresh/patches/switchview1a/build.py PhotonCamera_254 --sdk /path/to/android-sdk --output build254
python3 M9Camera_refresh/patches/switchview1a/package.py PhotonCamera_254 build254/app/outputs/apk/debug/M9Cam_2.54_SWITCHVIEW1A-debug.apk /path/to/M9Cam_2.53_JPEGQUEUE1A.apk /path/to/android-sdk/build-tools/35.0.0 deliverables254
```

Use the packaging step to preserve accepted native libraries; do not distribute the raw Gradle APK. Toolchain is unchanged from 2.53. Source manifests pin the parent and patch hashes.

## Phone retest

Install 2.54 over 2.53. Repeat the recorded M9 photo → Monochrom photo → M9 sequence several times, and open/close an exposure control while switching. Check that controls still move normally and photos save. If an exit remains, obtain a fresh crash report or logcat tied to 2.54 and the reproduction time; the historical report cannot establish another cause.
