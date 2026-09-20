# M9LIVEGL2B — focus continuity after capture

Candidate based on GL2A commit 87f0b766df071b649f1dc205ac6ab22fc11eb7a2. The user reports improved main-camera preview on Xiaomi 17 Ultra, but a grey/white haze on telephoto and loss of focus after a shot; the latter is not observed on their 15 Ultra.

## Evidence

The 24.94 s recording `1126.mp4` shows a sustained telephoto preview black floor around RGB 74–75 in a dark lower-preview region, deep blacks in the displayed still, and a blurred live preview later. This establishes visible preview disagreement, not the exact shader/HAL cause. A clean lens is reported by the user.

The supplied `IMG_20260920_171122_1789920682052_00` sidecars identify direct camera 4, 18.7 mm f/2.28, ISO 42, 18,396,226 ns, RAW 4080×3072. Still AF state is INACTIVE (0); recorded lens distance is 0.5703125 diopters. A single still result does not show the post-capture lens trajectory or prove a successful focus lock. The uploaded JPEG is visibly sharp at the window/toys and does not have the preview's grey floor.

The new upload contains M9, SOURCECAL, RAWSHADING, DEVICEPORT and TTL JSON, but no matching PRIMARY or diagnostic burst. `_M9.json` has legacy descriptive build/render strings; these must not be used to infer that this running candidate uses SAT3. Actual GL2A preview readiness/fallback, matrices and exposure scale reside in PRIMARY's `shutterPreview1W.source2A`. Haze remains unresolved without that evidence, and possibly a direct OES input probe if returned metadata does not explain the pixels.

## Confirmed source defects and change

The parent shutter lock submitted START as a repeating request. Its still builder then changed AF to AUTO and submitted CANCEL, discarding the very AF state established for the shot. A further preview callback submitted START on every completed frame when the preference was AUTO. Post-capture release unconditionally cancelled, including trigger-driven AUTO.

Android documents START/CANCEL as single-request events; repeating START restarts autofocus. Mode changes reset the AF algorithm. See [CaptureRequest.CONTROL_AF_TRIGGER](https://developer.android.com/reference/android/hardware/camera2/CaptureRequest#CONTROL_AF_TRIGGER) and [CaptureResult.CONTROL_AF_STATE](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AF_STATE).

GL2B scopes its correction to ordinary M9 photo capture:

- Shutter sends one START; repeating requests retain IDLE. Submission failure also clears the trigger.
- The still retains the preview AF mode and regions, with IDLE. Manual focus including zero-diopter infinity is carried through explicitly. Automatic focus is not replaced by a guessed manual distance.
- Post-capture continuous AF receives one CANCEL to resume passive focusing. AUTO/MACRO retain their established focus; manual/OFF and EDOF are not triggered.
- AUTO preview is primed at most once on entering the session/mode; additional starts come from deliberate shutter/tap actions. Stale INACTIVE results cannot create a trigger loop. The existing tap-to-focus sequence remains its own trigger owner.
- Fixed/manual focus bypasses a lock wait that cannot produce an AF lock acknowledgment.
- LIVEPAIR records the preview AF mode, trigger, distance/state and timestamp, plus still request/result AF and distance fields. The resume log identifies mode/cancel/distance. This is not a post-capture focus trace or optical sharpness measurement.

No Xiaomi model or lens ID is hardcoded. The correction follows AF mode semantics. Continuous AF can still refocus when a scene changes; phone validation is required to assess the reported focus jump.

## Frozen boundaries and validation

GL2A shader, OES inversion/context, matrices, WB behaviour, preview exposure, native RAW renderer, SAT2/curve02 assets, demosaic/sharpness and exposure allocation are byte-identical. The capture's focus commands change; the photographic processing does not. This is not a haze or yellow-WB correction.

Host tests compile the actual helper and actual controller lock/resume/prime method bodies against a recording Camera2 stub: 83 assertions across continuous, AUTO, macro, manual, EDOF/fixed focus, repeated callbacks, tap ownership and submission failure. The manifest verifies changed files and all GL2A frozen boundaries. These are request-sequence checks, not hardware focus evidence.

Device check: use telephoto, tap the toys, take a shot, observe return to live preview and take a second shot without retapping. Compare automatic continuous AF, tap focus and manual focus, then check the main lens and 15 Ultra for regressions. Upload the matching PRIMARY and diagnostic burst as well as JPEG/recording. Do not merge until device evidence supports the focus behaviour and the outstanding preview haze is separately understood.
