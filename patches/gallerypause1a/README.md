# M9Cam 2.88 GALLERYPAUSE1A

Four phone reports from 2.87 show CameraActivity pause failing on the main thread:
CameraFragment.onPause -> Swipe.SwipeDown -> null TouchFocus.resetFocusCircle.
The pause method already disposed the touch focus owner before calling the live
swipe gesture. It crashed only when the manual panel was open. Three reports have
render_complete checkpoints in the same process; the fourth has no current render.
An older stored checkpoint must not be attributed to that fourth process.

The camera pause now calls a dedicated UI-only cleanup method. It cancels the
arrow animation, closes the manual panel and retracts its knobs, without invoking
touch focus or explicitly resetting camera 3A. Normal live swipe behaviour is
unchanged. No exception swallowing or capture/render/save/RAW-size changes.

Five Robolectric regressions execute real fragment pause with open/closed manual
controls, manual ISO, repeated pause/resume, and activity recreation; the fifth
checks the live swipe still resets focus and 3A. These run with the previous 175
focused tests. Source verification allows only Swipe, one CameraFragment call,
the regression class and version metadata. Packaging retains the 27 native
libraries and 285 assets from the verified 2.87 installer.

Phone test: install over 2.87; open manual controls, take a photo, open gallery,
return to camera and repeat. Also leave the app and return with the panel open,
and confirm tap focus and ordinary manual controls still work. Phone validation
is pending; unrelated crashes are not claimed fixed.

## Verified installer

All 180 focused tests passed (five new gallery-pause regressions, 175 existing),
with zero failures/errors/skips. Library release resources and signed APK checks
passed. The independently downloaded APK has the accepted signing certificate,
correct package/version, intact archive and 16 KiB alignment. Its 27 native
libraries and 285 assets match v2.87 byte-for-byte.

[Download M9Cam-2.88-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38206819903/artifacts/11727343613).
Extract the ZIP and install `M9Cam_2.88_GALLERYPAUSE1A.apk` over 2.87.

Built commit: `c2a9b959d509ad822e113ec90f6a70ce888734d6`; run `38206819903`.
APK SHA-256: `06a95902b293c9b236ddc471c33bf8465cdcaf8011d04aaf9cb8b40148c7ae26`.
See CI_VERIFICATION.json, PACKAGED_VERIFICATION.json and
GITHUB_DELIVERY_VERIFICATION.json. Draft PR #106 awaits phone confirmation;
no claim of additional vendor RAW-size hardware support is added.
