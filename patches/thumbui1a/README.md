# M9Cam 2.55 — THUMBUI1A

Gallery-thumbnail UI threading and lifecycle fix, based on 2.54 SWITCHVIEW1A (`f3d6467330d95d7412f0d0216c3dddff28fc41b4`, draft PR #72). Phone validation of this fix is pending. Main remains the accepted 2.52 baseline; the 2.53 JPEG queue and 2.54 redraw fixes remain included.

## Confirmed logcat cause

The supplied logcat's latest M9 Java crash is at **10-05 08:50:20.979**, on **AsyncTask #1**:

```
AndroidRuntimeException: Animators may only be run on Looper threads
ValueAnimator / LayoutTransition / View.setVisibility
LensZoomBarController.animateIn -> setSettingsHidden
CameraFragment$1.onPropertyChanged
CameraFragmentModel.setBitmap
CameraFragmentViewModel$2.onResourceReady
Glide SingleRequest / Engine.load / RequestBuilder.into
CameraFragmentViewModel.updateGalleryThumb
CameraFragment.onResume (line 550) / AsyncTask
```

Earlier M9 crashes in the same log also report CalledFromWrongThreadException through this thumbnail path. The latest stack matches 2.54's onResume line, although the stack itself does not state an APK version. `LOGCAT_EVIDENCE.json` contains the relevant M9 stack only; the complete multi-app logcat is not published.

Glide can deliver a memory-cache hit synchronously inside `into()`. The resume task calls it from AsyncTask, and photo-save notifications can call it from save workers. The thumbnail callback changes an observable model, which broadly notifies the lens controls and starts layout animations on that worker. This is a separate, directly evidenced crash from the historical pre-draw null-binding bug addressed in 2.54.

## Change

- Start Glide thumbnail requests on main, covering synchronous cache hits as well as ordinary asynchronous completion.
- Keep MediaStore history queries off main. Register the request generation immediately, before queuing the query, including on resume/unlock.
- Ignore superseded requests and completions after clear or ViewModel disposal. A lock-screen clear invalidates an in-flight history query while still allowing a subsequent explicit session photo.
- Own and clear the Glide target; remove the displayed bitmap before releasing its resource. A retired target cannot clear a newer thumbnail.
- Notify only the bitmap binding for bitmap changes, avoiding unrelated lens/settings updates.
- Remove the lens model observer when its view is destroyed and ignore an already-copied callback for that retired view.

Production changes are limited to CameraFragment, CameraFragmentModel and CameraFragmentViewModel, plus the version. The 200-pixel gallery thumbnail request size is unchanged. All photographic rendering, preview colour/exposure calculations, JPEG/DNG save queues, RAW profile embedding, native code and assets remain unchanged. No lens-shading optimisation is included.

## Verification

- `PARENT_REPRODUCTION.json`: unchanged 2.54 ViewModel and model reproduce the animator-thread exception with a background request and simulated synchronous Glide cache delivery. This is a controlled regression reproducer, not a physical-device run.
- `TEST_VERIFICATION.json`: **44 tests across nine nonempty suites**, all passing. Seven thumbnail cases cover synchronous cache completion, main-thread publication, overlapping targets, lock clear during queued work and an active history query, ViewModel disposal, safe resource release, and property-specific notifications. Five renderer lifecycle cases include observer retirement, both switching directions and the earlier redraw protections. Camera/GL hardware and Glide delivery are controlled in Robolectric.
- `SOURCE_VERIFICATION.json`: six changed/added scoped files; **1,325 unchanged files**. Photographic/save code and live lens geometry preserved.
- `RECONSTRUCTION_VERIFICATION.json`: **1,331 scoped files** match the built source tree exactly.
- `PACKAGED_VERIFICATION.json`: upgrade identity/signature and 16 KiB alignment verified; **all 27 native libraries and 285 assets** byte-identical to 2.54.

## Recover/build

```bash
python3 M9Camera_refresh/patches/thumbui1a/assemble.py PhotonCamera_255
# Or add --parent /path/to/verified/PhotonCamera_254.
python3 M9Camera_refresh/patches/thumbui1a/verify_source.py PhotonCamera_254 PhotonCamera_255
python3 M9Camera_refresh/patches/thumbui1a/test.py PhotonCamera_255 --sdk /path/to/android-sdk --output build255 --java-agent /path/to/byte-buddy-agent.jar
python3 M9Camera_refresh/patches/thumbui1a/build.py PhotonCamera_255 --sdk /path/to/android-sdk --output build255
python3 M9Camera_refresh/patches/thumbui1a/package.py PhotonCamera_255 build255/app/outputs/apk/debug/M9Cam_2.55_THUMBUI1A-debug.apk /path/to/M9Cam_2.54_SWITCHVIEW1A.apk /path/to/android-sdk/build-tools/35.0.0 deliverables255
```

Use the packaging step to preserve the accepted native libraries; do not distribute the raw Gradle APK. The pinned source chain and toolchain are unchanged apart from this patch.

## Phone retest

Install 2.55 over 2.54. Repeat M9 photo → Monochrom photo → M9 several times. Also leave/reopen the app with an existing thumbnail and return while a photo finishes saving. Check the latest thumbnail, both renderers' saves, and normal controls. The automated reproduction passes after this fix; repeated phone use is still needed to establish that the reported exits are resolved.
