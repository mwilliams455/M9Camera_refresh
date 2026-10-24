# FOCUSSUBJECT1A — first implementation checkpoint

## Scope (24 October 2026)

The shared M9/Monochrom human face/eye autofocus milestone begins on exact, reconstructed **2.95** source; the optional 2.96 phase-noise optimization remains a separate experimental branch.

This branch introduces a camera-neutral `SubjectFocusPolicy` in `src/` and a JDK-only regression test in `host/`. The CI workflow copies the exact same policy into the reconstructed Android application source and compiles the application. It also exposes the relevant focus hooks in the job log to guide the next integration changes.

**What this checkpoint actually does:** selects an observed face, targets a human eye when supplied by the detector, falls back to the face, pins tap-selected subjects, rejects stale/wrong-session results, and prevents accidental switching to another subject while tap-pinned. It does not yet perform computer-vision inference or submit a Camera2 AF request.

**What it does NOT claim:** No working Face/Eye mode appears in the viewfinder; no ML Kit model is attached, no menu was added, the camera's autofocus behaviour and saved photographic processing are unchanged. A compiled APK at this checkpoint is not a functional focus-feature candidate.

## Hard integration requirements

1. Read actual 2.95 `FocusTrackingController`, `TrackingGeometry`, `TouchFocus`, `CaptureController`, `CameraFragment` and preview data source before modifying them.
2. Use a bundled on-device human face/eye model; never require a remote download or send frames off-device.
3. Carry accurate preview rotation, mirror, viewport transform, crop, zoom, active-array and physical sensor identity to AF region calculations. Reject lenses with zero AF regions or fixed focus.
4. Run recognition off the camera/UI thread with a single outstanding frame and a bounded cadence. Reject late/old session results after lens switches, capture, orientation changes, zoom and profile changes.
5. Preserve Continuous Picture AF where supported; change only AF regions and do not modify AE/AWB, exposure, WB, preview or render settings. Do not issue AF_TRIGGER_START on every tracked frame.
6. Maintain manual tap focus and AF-S/MF. Subject detection must be opt-in and off by default until phone evidence verifies lens focus and shutter handover.
7. Gate Android build and subject-policy tests before making an installable phone candidate. Check both M9 and Monochrom, as well as multi-lens and fixed-focus behaviour.

## Verification

Local JDK: `javac` followed by `java -ea` passed the host target-policy test. GitHub CI re-runs it in the reconstructed source and builds the Android app. Physical-device AF accuracy not yet evaluated.

Human eyes are the first target; cat/dog, vehicles and animal-eye localisation require their own models, selection policies and phone validation. No external Hasselblad firmware code or proprietary binaries are imported.