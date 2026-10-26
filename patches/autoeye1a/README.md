# M9Cam 3.10 AUTOEYE1A — automatic human-eye detection in normal AF-C

**Parent:** user phone-accepted signed M9Cam 3.09 (`codex/m9-aftracking5a-v3.09`).
**Branch:** `codex/m9-autoeye1a-v3.10`; experimental, do not merge into main until phone validation.

## Behaviour

- New **Automatic human Eye AF** control defaults **ON**, including on upgrades where the old *Human Face/Eye AF* switch was OFF. No explicit opt-in, tap, or manually selected subject is required. Turning the new switch OFF returns to ordinary AF-C. The old switch is replaced in the M9/Monochrome Capture menus; historical old-key state is not authoritative.
- Only runs during Photo, Night, Motion with Camera2 Continuous Picture AF and **Wide** focus area. A user-selected non-Wide Spot/Custom area, AF-S/manual focus or opt-in Cat/Dog AF outranks it.
- Existing ML Kit human-eye detector remains on device, one reduced viewfinder frame at a time; no network or face pixels persisted.
- Existing **2.98 strict frontal gate** (two real eye landmarks, nose, mouth, stable ML Kit face ID for three fresh frames) remains untouched. A separate **3.10 profile gate** allows precisely one real eye with coherent nose/mouth geometry only after four fresh consistent frames of the same ID. A face-sized bounding box cannot move focus without landmarks.
- Existing Camera2 AF-region code, target geometry, shutter/tap lifecycle, accepted 3.08 prediction and 3.09 identity modes are unchanged. Eye AF uses their existing mutually exclusive focus handle. If user deliberately taps an arbitrary object, the automatic eye controller stands down. Tapping a visible face selects that eye and cancels any prior arbitrary selection.
- No exposure, WB, tone, JPEG/DNG/RAW, demosaic, Monochrome processing, native libraries or existing model assets changed.

## Verification

- `AutoEyeFocusPolicyHostTest`: 40 mode/priority cases (AF-C, Wide, Photo, opt-out, pet, deliberate tap).
- `ProfileEyeAdmissionGateHostTest`: 93 temporal/geometry/age/epoch/false-positive checks, profile eye acquisition and explicit optical target coordinates.
- Preserve inherited original `HumanEyeAdmissionGateHostTest`, `SubjectFocusPolicyHostTest`, all parent AF/face/pet/track, shutter/handover and capture regressions. Build and package with accepted 3.09 APK; 37 native libraries/301 assets must be byte-for-byte identical; signed app certificate must match.

## Phone test

1. Install over 3.09 **without clearing data**; put AF mode in **Continuous Picture** and focus area in **Wide**. Leave Automatic human Eye AF ON (its default). You should not need to enable generic Focus tracking or the legacy Human Eye mode. Open M9 Photo, introduce a face and let the app recognise an eye automatically.
2. Use a child at profile like video `62876.mp4`. Confirm that the marker follows the **actual visible eye**, not generic body/furniture. Turn their head away, show a face again, and verify reacquisition. Confirm saved stills focus on the eye; a box or HAL state alone is not proof of optical sharpness.
3. Test an empty room with toys: **no eye marker**. Move two people across the viewfinder; tap one to keep selection; tap a toy to override automatic eye focus. After the manual object track is retired, automatic eye acquisition can resume.
4. Disable Automatic human Eye AF; ordinary Camera2 AF-C and explicit 3.09 arbitrary tracking should continue. Switch to Spot, AF-S/manual, unsupported/fixed-focus, Cat/Dog and Monochrome; no automatic human-eye AF should claim ownership in those modes.
5. Test after shutter, app pause/resume, zoom/lens switches and rotation. Check no exposure pumping, preview flicker or capture regression, and assess the preview CPU cost.

**Limits:** This implements a stock-like automatic eye-detection *behaviour*, not vendor-equivalent Xiaomi or Hasselblad recognition. Profile recognition still depends on ML Kit providing an eye, nose, mouth and stable tracking ID. It does not guarantee eye sharpness or real-time 60 Hz tracking until tested on device.
