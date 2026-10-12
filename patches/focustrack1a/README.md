# 2.72 FOCUSTRACK1A — experimental tap-to-track autofocus

Adds an optional **Settings → Capture → Focus tracking** switch to both M9 and
Monochrom, off by default. With Continuous Picture AF selected, tap a textured
subject in Photo, Night or Motion. A white tracking box follows the selected
patch. Tap the box to cancel, or tap elsewhere to select another target. An amber
“Tracking lost — tap again” box means the match was rejected. Tracking confidence
does not claim that the lens is focused.

This is a local visual-patch tracker, not semantic person, face or eye detection.
It follows translation within a bounded search window. Occlusion, repeated
patterns, low texture, rapid movement, substantial scale/shape change and stale
frames stop tracking; it does not silently reacquire a different target.

The sharp preview supplies its actual rotation, mirror, viewport and texture
timestamp. PixelCopy reads at most one reduced frame (long edge 256 pixels) at a
time, on a 100 ms opportunity interval. Fixed-template normalized correlation
runs on one worker, not the UI or camera thread. Late results are rejected after
retaps, pause, view destruction, geometry/lens/zoom/profile/mode changes, capture,
or loss. The bitmap is not recycled while PixelCopy or analysis owns it.

Camera requests run on the camera handler. The initial selection releases a
previous tap AF lock with one CANCEL, returned immediately to IDLE. Movement
changes only AF regions, with a small deadband, and retains Continuous Picture
AF. It does not issue START, change to Video AF, move AE/AWB regions, or change
exposure/white-balance/tone controls. Cancellation restores the earlier AF region
only while this tracker still owns that region, and waits for preview before
submitting after a capture. Unsupported/fixed-focus lenses and other AF modes
are rejected. Pinch zoom retires a target; retap after zooming.

The source patch is based on exact merged 2.71. Native libraries, assets, colour
and Monochrom rendering, exposure plans and shutter diagnostics are unchanged.
The final installer reuses all 27 native libraries from the verified 2.71 APK.

## Validation

`assemble.py` verifies complete scoped parent and candidate fingerprints;
`verify_source.py` checks the exact changed scope and reverses the patch back to
the parent. Android CI builds the app and runs tracker movement/brightness,
ambiguity/loss, display geometry, AF request ownership, lifecycle, existing tap
focus and inherited capture/diagnostics tests. Packaged verification records the
APK hash, signature, menus and native/asset preservation.

Phone validation is still required. Try a textured subject against a distinct
background, move the phone gently, then move the subject nearer/farther. Check
that the box follows, the lens refocuses, and saved stills are sharp. Repeat in
both profiles, portrait/landscape, front/back where AF is supported, and after
zooming or switching lenses. Cover the subject to verify loss, retap to recover,
and check that taking a photo/backgrounding clears the target safely. Fast
motion or a large change in subject size may intentionally require another tap.

This feature does not resolve the separately reported exposure pumping or the
screen-recorder/shutter limitation.

## Verified delivery

Android [run 38080675440](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38080675440)
on source commit `83a421a4b47533135628b8d69c9f92338dea2ac6` passed the build and
all **71 tests** (zero failures, errors or skips). See `BUILD_VERIFICATION.json`.
The AF tests observe builder state at session submission because Robolectric's
request-builder shadow does not populate the native metadata of built requests.
Actual HAL response, focus accuracy and phone performance remain device checks.

The signed `M9Cam_2.72_FOCUSTRACK1A.apk` is 119,618,357 bytes, version code 27272.
It preserves all 27 native libraries and all 285 assets from 2.71, matches the
accepted certificate, and passes 16 KiB ZIP alignment. Both compiled Capture
menus contain the new setting. See `PACKAGED_VERIFICATION.json`.

SHA-256: `3018e5eac4869ba2c1a3470f12a830ccdcff3aa29fd2f055472fcc0f43f2bdfb`.
