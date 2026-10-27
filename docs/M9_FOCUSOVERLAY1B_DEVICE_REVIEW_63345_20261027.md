# M9Cam 3.12 FOCUSOVERLAY1B — device video review

**Date:** 27 October 2026. **Video:** user-supplied `63345.mp4`, 32.95 s, portrait 1440×3200, approximately 59.25 fps. **Camera:** M9 profile, Motion mode, 1× preview, Continuous Picture AF and Wide area visible in HUD.

## Result

**Visual size regression from 3.11: FIXED in the recorded Eye AF portion.**
The white 4-corner Balanced Extended marker is compact and appears centred on a detected eye while the face moves, without the black Eye AF text plaque. At ~4.2 s and ~7.6 s the overlay is eye-local. This is a positive visual review, **not yet explicit approval to merge or proof of optical saved-image sharpness**.

The earlier 3.11 video `63341.mp4` at ~6.2 s showed an eye marker extending above the eyebrow and below the eye onto the cheek. In 3.12 the smaller white corners lie around the eye and no longer resemble the full AF metering-region footprint.

## Time-coded observations

| Time | On-screen evidence | Interpretation |
| --- | --- | --- |
| 0–2.5 s | Start/camera-preview state; no stable face tracking; horizontal magenta/yellow lines remain even during black preview | Level/guide-like overlay is independent of white eye ticks; exact owner unproven |
| ~3–9.5 s | One child visible, active white four-corner bracket centred on an eye while head angle/position changes; `Eye AF` / AF scanning and reported-focused HUD | New display extent works; AF status cannot certify optical sharpness |
| ~10–14.5 s | Child travels towards/partly outside left side; `Eye AF` sometimes idle/scanning; intermittent marker at edge, then no sustained eye display | Face loss/partial occlusion can explain status variation; no definitive 3.12 AF regression |
| ~15–18.5 s | HUD explicitly changes to `Tracking person`; larger square-ish 4-corner marker follows seated adult | This is arbitrary/semantic **person tracking**, not the compact automatic Eye AF marker; target-sized box intentional |
| ~18.75–21 s | Person-tracking region changes from seated adult to child; brief amber `Tracking obscured - AF area held`, then white around child | **User confirmed deliberate taps** between the people; the subject handover is expected and not evidence of identity theft |
| ~22–25.5 s | Tracking person indicator returns to adult | **User confirmed intentional tapping**; expected manual subject switch |
| ~26–32.9 s | Person tracker alternates towards child and amber hold appears; final large rectangle-like corner configuration is person tracking | **User confirmed deliberate subject selection changes**; this is person tracking rather than a recurrence of the large Eye AF bracket |

## Outstanding investigation gates

1. **RESOLVED — user confirmed intentional taps:** adult/child switches around 19, 22 and 26 s were deliberate manual selections. No subject-identity fault established; no identity algorithm change warranted from this clip.
2. **Not a 3.12 patch:** centre horizontal magenta/yellow lines cross whichever face happens to be in the middle of preview; they also exist on black preview without an eye. Red clipping warnings and viewfinder grid are separately drawn. Treat these as independent UI overlay settings/diagnostics, not a rendering or eye-AF issue. Identify owner before disabling or changing them.
3. **Optical AF gate pending:** capture actual JPEG/DNG with focus on eye in motion; HAL `AF reported focused` does not establish optical accuracy or compare with 3.10.
4. **Visual approval pending:** the design is locked; do not merge into main without explicit phone approval for 3.12. Keep signed 3.11 and 3.10 as rollback.

## User follow-up — subject handover verified

After this review, the user explicitly confirmed, **“I intentionally tapped.”** This resolves the uncertainty regarding person-to-person switching during the second half of `63345.mp4`. Treat these as deliberate focus-target changes, not automated tracker identity switches. No tracking code change or new capture solely for identity diagnosis is needed.

## Source boundary

3.12 caps only `HumanSubjectFocusController` display half-extents at 17×13 dp before forwarding to `TrackingFocusView.show`. Original `focus.update(...)` Camera2 region, target centres, detectors, face gates, track identity/predictor, photo rendering, the pet marker and the manual/area focus marker remain unchanged. CI 3.12: https://github.com/mwilliams455/M9Camera_refresh/actions/runs/40468484229 ; signed APK SHA-256 `434fb4a6de2e87aa883fe841db1d8abed5c38785e574a756020d8b6aa818a4ee`.

**Decision after user clarification:** no 3.13 tracking/identity patch warranted. Eye AF bracket's visual-size regression is resolved, and manual retargeting behaves as intended in the recording. The separate optical sharpness test, guide-overlay ownership investigation, and explicit merge approval remain pending.
