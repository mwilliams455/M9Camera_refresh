# UISETTINGS1A — M9Cam 2.77

Malcolm confirmed 2.76 MONOPLANWAIT1A works, then reported an M9-named queue message after three photographs and flashing legacy settings. Recording 52551.mp4 (23.10 seconds) shows the old Flash / Countdown Timer / RAW / Image Stabilization panel at the start, around the renderer switch at 13 seconds, and later near 20.5 seconds. The queue warning is reported by the user; the recording does not establish its timing or how long saving took.

## Correction

- Replace the hard-coded M9 queue warning with the shared resource “Photos are still processing. Please wait.” The existing M9/Monochrom admission routing and bounded capacity remain unchanged (one running plus two queued jobs).
- The legacy panel had no initial visibility in XML, and binding posted an animated hide. It could therefore draw before it was hidden. Start it GONE and hide synchronously, cancelling earlier animation work.
- Swipe-down and the old arrow could still request this panel. Retire that model control before the first binding of each camera view, keeping visibility false so legacy requests cannot hide the new header/lens controls or reopen the panel. Retain underlying controls and preferences; the current settings screen and shooting-controls panel remain available.

Eight scoped files change, including the version and two regression cases added to the existing layout suite. Native/rendering assets, queues, exposure planners and capture/focus controller are byte-unchanged. Source verification checks exact scope, reverse restoration, XML default visibility and retirement before binding. The UI tests cover immediate hiding, cancellation of pending animation, and legacy requests following orientation changes, plus existing overlay/shooting-controls tests.

Android CI [38137876959](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38137876959) passed **20 tests**, with zero failures/errors/skips: overlay layout (3), overlay policy (7), shooting controls (7) and tracking lifecycle (3). The XML report also contains an empty AF-continuity discovery suite; no AF-continuity cases are counted in this UI run. The inherited 2.76 capture/focus implementation is byte-unchanged.

The signed installer passed version/certificate, 16 KiB alignment, both compiled settings menus, compiled legacy-panel GONE visibility, neutral message/old-message absence, and preservation of all 27 native libraries and 285 assets. APK SHA-256: `856cccd23d8c5020d2ecd730ae559c6a4d9a0351689cabf3ef3cd2144cf4409d`. Evidence: [source](SOURCE_VERIFICATION.json), [build](BUILD_VERIFICATION.json), [package](PACKAGED_VERIFICATION.json).

Device validation remains pending: open/close Settings, switch between M9 and Monochrom, and swipe down; the old panel should stay hidden. Verify the neutral wording when processing capacity is reached. The successful 2.76 readiness check is recorded separately. [PR #95](https://github.com/mwilliams455/M9Camera_refresh/pull/95) remains a draft; no merge authorized.
