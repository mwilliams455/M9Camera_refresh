# UISETTINGS1A — M9Cam 2.77

Malcolm confirmed 2.76 MONOPLANWAIT1A works, then reported an M9-named queue message after three photographs and flashing legacy settings. Recording 52551.mp4 (23.10 seconds) shows the old Flash / Countdown Timer / RAW / Image Stabilization panel at the start, around the renderer switch at 13 seconds, and after a downward gesture near 20.5 seconds. The queue warning is reported by the user; the recording does not establish its timing or how long saving took.

## Correction

- Replace the hard-coded M9 queue warning with the shared resource “Photos are still processing. Please wait.” The existing M9/Monochrom admission routing and bounded capacity remain unchanged (one running plus two queued jobs).
- The legacy panel had no initial visibility in XML, and binding posted an animated hide. It could therefore draw before it was hidden. Start it GONE and hide synchronously, cancelling earlier animation work.
- Swipe-down and the old arrow could still request this panel. Retire that model control before the first binding of each camera view, keeping visibility false so legacy requests cannot hide the new header/lens controls or reopen the panel. Retain underlying controls and preferences; the current settings screen and shooting-controls panel remain available.

Eight scoped files change, including the version and two regression cases added to the existing layout suite. Native/rendering assets, queues, exposure planners and capture/focus controller are byte-unchanged. Source verification checks exact scope, reverse restoration, XML default visibility and retirement before binding. The UI tests cover immediate hiding, cancellation of pending animation, and legacy requests following orientation changes, plus existing overlay/shooting-controls tests.

Android and signed-installer verification pending. Device validation of this UI correction remains pending. The successful 2.76 readiness check is recorded separately from this new issue. Draft only; no merge authorized.
