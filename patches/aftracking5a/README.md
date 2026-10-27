# M9Cam 3.09 AFTRACKING5A — persistent subject identity (opt-in)

**Parent:** signed and phone-positive M9Cam 3.08 `codex/m9-aftracking4a-v3.08`. Development branch: `codex/m9-aftracking5a-v3.09`. Do not merge into `main` without phone validation.

## Purpose and limitations

User accepted 3.08's predictive AF-C behaviour. This update does **not** modify its AF-region prediction, Camera2 request cadence, shutter capture, exposure, WB, colour, demosaic, Monochrome, RAW/DNG/JPEG, native processing, or existing eye/pet focus modes.

3.07's tapped person/cat/dog anchor matches labels and boxes by spatial overlap; two people crossing can exchange positions, and the tracker can then follow the wrong person. 3.09 introduces an optional **Persistent subject identity (experimental)** switch, **off by default**, which automatically enables Subject-aware tracking and Focus tracking. Switching either parent off retires the dependent identity switch. When identity OFF, the existing 3.08 path and legacy SubjectAnchorPolicy decisions remain unchanged.

## Implementation

- Reuse existing pinned on-device EfficientDet detector. No model download at runtime; no additional .so or assets. `TrackingSemanticDetector` adds a lightweight 12-bin colour/neutral histogram computed from central, bounded **preview** pixels inside recognized person/cat/dog boxes. It never reads saved photographs, DNGs, or any user biometric identification; descriptor lives only in memory during a tap-selected track and is wiped on tap/camera-session retirement.
- First tap still must overlap a recognized candidate and pass two distinct detector frames before semantic acquisition. A strong appearance reference can reject an otherwise spatially plausible stranger with a different shirt/fur. If multiple candidates remain similarly plausible, the app enters HOLD; it never silently selects a winner.
- After any missing/ambiguous detector observation, require **two consecutive, current, spatially coherent observations** of the selected subject before moving Camera2 AF regions. While pending, the prior AF region is retained; no repeated trigger or AE/AWB region update is sent. Existing 1.15 s bounded semantic hold and permanent retirement remain unchanged.
- Absence of informative colour (grey/black/uniform neutral surfaces), matching outfits, significant illumination change, or extended occlusion **cannot** establish reliable identity. Camera falls back to a conservative spatial match or HOLD, and ultimately requests a retap. This is **not** a persistent biometric person ID or Hasselblad firmware equivalence.
- The model still runs on the existing single worker with one in-flight PixelCopy, 448-pixel detector preview and 256-pixel patch fallback. No extra preview readback is scheduled. All epoch, zoom, lens, profile, orientation, stale-result and pause/capture checks remain.

## Local tests

- `SubjectAppearanceDescriptorTest`: histogram, illumination shift, different colour rejection, neutral safety, invalid/short frames, bounded blend, background isolation.
- `SubjectIdentityPolicyTest`: selected-versus-crossing-person, different-shirt rejection, ambiguity HOLD, two-frame recovery, old-session/stale/duplicate protection, retirement and disabled-mode parity.
- Inherited `SubjectAnchorPolicyTest`, `TrackingTogglePolicyTest` + 3.09 dependency checks, 3.08 motion predictor, 3.06 multi-scale patch tracker, inherited autofocus handover and capture tests also required.

## First phone verification

1. Install 3.09 over 3.08 without clearing data. With **Persistent subject identity OFF**, verify the accepted 3.08 tracking and Predictive AF-C have not regressed.
2. Enable **Persistent subject identity**; check that Subject-aware and Focus tracking turn on automatically. Keep AF-C selected. Tap one person wearing a distinctive coloured top; have someone else cross and briefly obstruct them. The box must not jump to the other person.
3. Have the original subject turn and return from brief occlusion. The indicator should HOLD while unsure, then recover only on coherent observations. Captured JPG focus accuracy is a separate gate.
4. Repeat with two similar outfits, dim light, cat/dog, an arbitrary toy (patch fallback), lens switching, M9↔Monochrome, zoom, pause/resume. Ambiguous cases should HOLD/retire instead of confidently tracking a stranger.

**Release gate:** Android compilation and tests, exact 3.08 signed installer SHA-256, certificate, preserved 37 libraries and 301 assets, compiled settings in both profiles. This is an experimental candidate until on-phone evidence confirms correct subject identity.
