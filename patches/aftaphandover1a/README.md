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

## Verification

Android build and all **181 tests** passed (36 handover cases and 145 inherited cases; zero failures/errors/skips), workflow [38121755874](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38121755874), source commit `541a93e28514c024ae5aa3f0b38a1015fc005eeb`.

The initial test fixture omitted the Monochrom camera-characteristics map that a real controller initializes. Correcting the fixture preserved the request assertion; the complete suite then passed. Background-thread tap exceptions also propagate to the test runner.

The signed installer passed version/certificate, 16 KiB ZIP and Monochrom ELF alignment, compiled-menu and exact native/assets preservation checks. All 27 native libraries and 285 assets match 2.74. SHA-256: `94de57daefb1dddb43297d5c3b8220c233ec76579c39696faa07f6b0c5ca7963`.

Evidence: [source](SOURCE_VERIFICATION.json), [build](BUILD_VERIFICATION.json), [package](PACKAGED_VERIFICATION.json). This new build still needs physical-device evidence; the successful 2.74 phone feedback above remains recorded.
