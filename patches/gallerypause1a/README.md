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
