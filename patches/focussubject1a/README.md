# FOCUSSUBJECT1B — false-positive human-eye AF correction (24 October 2026)

## Real phone evidence

In user-supplied screen recording `61791.mp4` (24.8 s, 1440 × 3200),
M9 mode / Motion / 24 mm shows the white `Tracking` box placed on
countertop clutter and other household objects in a scene without a
visible person. This is a **FAIL** for Human Face/Eye AF. The box was
generic for both the 2.72 patch tracker and 2.97 Eye AF, so the video
cannot by itself prove which controller owned each rectangle. The
2.97 source nevertheless has a concrete unsafe acquisition path:
`SubjectFocusPolicy.update(...HUMAN_EYE)` accepts a single face-box
result and aims at the *face centre* with zero eye landmarks.

## 2.98 correction

- Keep Eye AF off by default and prevent simultaneous legacy patch-tracker
  ownership whenever the Eye AF preference is enabled.
- Do not allow unverified face rectangles into Camera2 autofocus updates.
- Require **both human-eye landmarks, nose base and mouth bottom** in a
  plausible facial arrangement, as well as a non-null ML Kit tracking ID.
- Require three consecutive, separate, recent observations of the same ID
  within a bounded movement/gap window before automatic acquisition.
- Reject repeated callbacks for the same frame, stale frames, old sessions,
  tiny detected patches, extreme landmark geometry, missing eyes and
  tracking-ID changes.
- When no eye is admitted, do **not** issue tracking AF-region updates,
  trigger AF scans, alter exposure or white balance, or show a newly
  acquired focus box. Ordinary continuous-picture AF continues.
- Preserve the existing 2.95 M9/Monochrom photographic pipeline, all 27
  native libraries and 285 inherited assets. Use the bundled on-device
  ML Kit model, no remote inference.

This deliberately sacrifices immediate acquisition and unsupported
strongly-profile/partly-occluded faces. Three detections at a 200 ms
inference opportunity cadence can cost at least around 400 ms before
first eye lock. Camera HAL focus accuracy remains a separate phone gate.

## Validation

The host `HumanEyeAdmissionGateHostTest` explicitly feeds repeated
fake face boxes, two eye-like points without nose/mouth, missing eyes,
bad landmark geometry, small patches, duplicate frames, wrong
camera epochs, stale results, discontinuous motion and real-looking
face landmarks. Fake eyes must **never** be admitted even after twelve
frames; a coherent full face requires three hits.

The original `SubjectFocusPolicyHostTest` and
`FocusAreaPolicyHostTest`, the Android focus/tracking regressions,
signed APK identity and 16 KiB arm64 alignment all remain required.
Tests and Android compilation do not constitute a real-device sharpness
or AF-C stability claim.

## Follow-up phone gate

Install the signed `M9Cam_2.98_FOCUSSUBJECT1B.apk` over 2.97, enable
Human Face/Eye AF and use AF-C. Repeat the *same* empty-room pan as the
video, including Motion: the Eye AF box should never acquire objects.
Then introduce a clearly visible person's face and confirm the eye
box begins only after stable recognition, moves with the eye, and
produces a sharp saved photograph. Repeat on M9 and Monochrome;
test ordinary tap-focus, pause/resume, and lens switches.

--- 

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