# M9Cam 3.13 TRACKINGDEFAULT1A — tap-to-track defaults (candidate)

**Parent:** M9Cam 3.12 FOCUSOVERLAY1B merged to main in PR #123, specifically the phone-reviewed, signed APK with SHA-256 \`434fb4a6de2e87aa883fe841db1d8abed5c38785e574a756020d8b6aa818a4ee\`. 3.12 visuals remain locked.

## New candidate behaviour

- In **M9 and Monochrome**, PHOTO / NIGHT / MOTION, **Wide** and **Continuous Picture AF**, an otherwise untouched install offers **Focus tracking** and **Subject-aware tracking** ON by default. **Automatic human Eye AF** stays independently ON by default.
- No automatic arbitrary-object tracker is started by object recognition. The user taps a person, pet or textured object to start a tracking target. Tap the current bracket to cancel or tap elsewhere to switch target. A deliberate human-eye tap wins over arbitrary tracking.
- **AF-S, manual AF, Spot, Expand Spot, Custom, dedicated pet AF**, unsupported lenses and unready preview retain the inherited nontracking tap route. Valid tracking handles are still checked by Camera2; capability cannot be inferred from a marker.
- Saved global OFF for \`pref_focus_tracking\` continues to mean OFF. Advanced-switch inflation no longer enables parent tracking implicitly. Runtime reconciliation never changes an explicit OFF to ON, even with stale child state.
- \`pref_focus_tracking_predictive\` and \`pref_focus_tracking_identity\` remain individually OFF by default. Genuine user interactions with dependent switches still apply the original toggle dependencies.
- Subject recognition is *lazy*: the existing offline model is initialized only after a deliberate selection, rather than at preview start or at every idle tick. The existing automatic Eye AF worker is unaffected.

**Non-goals:** No detector-model changes, automatic recognition of every object, AF-trigger rewriting, exposure, sharpness, denoise, demosaic, LUT/RAW/DNG/JPEG changes, focus marker redesign, or new HDR pipeline.

## Verification and delivery

The new pure-Java \`TrackingDefaultPolicy\` and JDK host test check seven AF admission combinations and model warm-up. Static staged-source checks validate both profile menus, explicit OFF preservation, AF-C/Wide routing, predictive/identity opt-in, one-and-only-one semantic initialization site, and the retained compact eye marker. Inherited AF, human/pet, tracking, layout and shutter regression tests remain mandatory in Android CI.

The exact merged 3.12 workflow reconstructs the Android app, stages \`apply.py\`, runs the new and inherited gates, and packages the debug build with the **original signing key and exact 3.12 signed parent APK**. The signing wrapper requires the precise 3.12 checksum, the original certificate, 16 KiB ZIP alignment and unchanged 37 native libraries / 301 assets. A successful build produces \`M9Cam_3.13_TRACKINGDEFAULT1A.apk\` as an Actions artifact. **Do not merge pending on-phone testing.**

Phone checks: new install default behaviour; upgrade from saved tracking OFF and ON; same checks on M9/Mono; AF-S/manual; Spot/Expand/Custom; supported vs fixed-focus lens; moving child/pet; face-to-toy handoff; deliberate retap cancellation; idle stutter/thermals; suspend/resume, shutter, zoom and orientation; **sharpness of saved JPEG/DNG**, not just overlay colour or HAL focus feedback.
