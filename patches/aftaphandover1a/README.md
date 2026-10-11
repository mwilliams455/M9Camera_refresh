# AFTAPHANDOVER1A — M9Cam 2.75

Continuation of 2.74, addressing AF-05 tap/shutter handover and disposal plus AF-06 stale passive-settle results.

Tap request mutations now run on the camera handler with the captured preview builder, session, device, open/session generation and focus-command generation. Shutter acceptance retires tap continuations before AF preparation while keeping the selected AF region and mode. New taps are refused while capture owns focus. A queued pre-shutter tap cannot return after that capture finishes. Session/manual replacement and view teardown retire callbacks; timeout removal uses the handler that scheduled it. Manual focus changes share the camera handler and preserve zero-diopter infinity. A stale settled result cannot finish the current passive scan; absolute expiry retires the tap without interpreting expiry as a focus acknowledgment.

The photographic renderer, native libraries, assets, exposure/WB policy and parked/default-off tracking algorithm are unchanged. Tests exercise the real TouchFocus state machine and controller request/admission methods with mocked Camera2 sessions and a Robolectric clock. They do not measure lens accuracy or simulate a complete HAL.

## Reproduce

```sh
python3 patches/aftaphandover1a/assemble.py /absolute/new/PhotonCamera_275
python3 patches/aftaphandover1a/verify_source.py /absolute/PhotonCamera_274 /absolute/PhotonCamera_275
```

Exact reconstruction, scoped change verification and reverse restoration are required. Android CI adds 36 parameterized handover cases to the 145 inherited cases. Package the CI APK with `package.py SOURCE BUILT_APK VERIFIED_274_APK BUILD_TOOLS OUTPUT_DIR`. Preserve all 27 native libraries and 285 assets from 2.74.

## Phone evidence already supplied

On 11 October Malcolm reported 2.74 felt quick enough after tap-to-focus then capture in M9 and Monochrom (52317/52318). He additionally supplied three captures taken while focus was still settling (52339/52338/52336). These are successful phone checks of those attempts, not pending requests to repeat them. They do not reproduce stale asynchronous callback ordering. This 2.75 candidate adds code-level protection for that remaining gap; its device behaviour has not yet been tested.

Android and installer verification pending.
