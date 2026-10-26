# M9 / Monochrome focus overlay — LOCKED Balanced Extended Ticks handoff

**Date:** 2026-10-26  
**Decision:** FINAL, no more UI concepts. Approved design is **Variant A — Balanced Extended Ticks / DEFAULT** on the final image board `rangefinder_focus_ui_study_board.png`. The complete local downloadable handoff package also contains a crop `M9_BALANCED_EXTENDED_TICKS_LOCKED_REFERENCE.png`.  
**Next stage:** implement **FOCUSOVERLAY1A** as a visual-only Android patch, sign and send a test APK + ZIP.  
**Starting branch:** `codex/m9-autoeye1a-v3.10`; accepted signed parent `M9Cam_3.10_AUTOEYE1A.apk` (code 27310). The user says automatic Eye AF seems to work. Keep baseline and `main` unchanged; build on a new feature branch.

## Locked visual contract

Four separate, thin, **medium-length white right-angle corner ticks** around the measured focus target. No full connecting box, centre dot, crosshair, double corner outline, eye glyph, decorative logo, or permanent black-backed "Eye AF" label. This is the BALANCED variant, not neighbouring Fine, Defined, Eye-Dot, Crosshair or Amber concept variants.

- Active/acquired uses restrained white/off-white ticks; white does **not** mean optical sharpness has been proven.
- Holding/pending/lost retain accessible, appropriately understated amber/error state signalling; don't make lost appear focused.
- Keep current focus centre and geometry, crop, rotation and mirror transforms. Eye brackets must stay compact around the actual **eye**, not grow into full-face rectangles.
- Engineering start points (visual tuning only): ~1.5dp stroke, anti-aliasing, strokes about 20–24% of the shorter drawn box dimension clamped ~6–11dp, minimal shadow on bright backgrounds. The selected visual reference, not these estimates, is the design authority.
- Use a consistent tick family for eye, ordinary tracking, pet AF and focus-area overlays; ordinary tap-focus can be visually harmonised without changing tap logic. No brand-logo graphic in the actual camera overlay.

## Exact technical targets (reconstructed source)

The M9 repository is reconstruction/patch based. Reconstruct the exact 3.10 working tree by applying inherited patches through `autoeye1a`, with pinned offline models, then modify only presentation files:

1. `app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/TrackingFocusView.java`: change `onDraw(Canvas)` full `canvas.drawRect(x-halfX,y-halfY,x+halfX,y+halfY,paint)` to four unconnected balanced corner ticks. Preserve signatures and semantics of `show(...)`, `showHolding(...)`, `showPending(...)`, `setContentDescription`, `invalidate`, and lifecycle. Its inherited source is under `patches/aftracking3b/src/.../views/TrackingFocusView.java`.
2. `HumanSubjectFocusController.java`: 3.10 Eye AF calls `overlay.show(px,py,halfW,halfH,false)`, *then* attaches an `EyeBadge` `Drawable` which paints a large black-backed Eye AF label. Suppress/reduce that default duplicate visible badge, preserving semantic `contentDescription` and optional diagnostics. Do not alter ML Kit admission, actual eye coordinates or Camera2 updates. Source: `patches/autoeye1a/src/.../ui/camera/HumanSubjectFocusController.java`.
3. `PetFocusController.java`: shares `TrackingFocusView`, but also draws `PetBadge`; assess label crowding without changing pet recognition/ownership or diagnostics.
4. `FocusTrackingController.java`, `FocusAreaTouchController.java`: shared overlay calls must inherit new geometry, without changes to patch/semantic tracking, AF-C prediction, AF regions or ownership.
5. `FocusCircleView.java` and `TouchFocus.java`: if harmonising ordinary tap-focus, preserve **2.78 FOCUSPOINT1A** Monochrome startup tap-coordinate and visibility fixes.

**No modifications** to Camera2 AF algorithms, subject identity, default Eye AF, preview timing, shutter, AF-L, focus distances, AE/AWB, WB, exposure, RAW/DNG/JPEG, M9/Mono photographic rendering, native libraries or model assets.

## Required implementation and validation

- Create a fresh feature branch from `codex/m9-autoeye1a-v3.10` and an exact-source/apply verification package (proposed next version **3.11 FOCUSOVERLAY1A**, subject to repo numbering).
- Tests: corner length/dp, tiny and edge-bound regions, all four corners without connecting edges/center marks, colours/state labels/content descriptions, M9+Monochrome UI, scale/rotation/zoom/lens/mirror, false loss/focus claims and no ghost overlays after retap/shutter/pause/resume.
- Re-run inherited AF-C, face/profile eye, pet, arbitrary, shutter, tap/first-launch FocusPoint regressions. Do not bypass them.
- Build, independently verify APK signature/ZIP 16KB alignment and byte-for-byte retention of **37 inherited native libraries and 301 original assets**. Confirm both M9/Monochrome and no changes to imaging inputs/outputs.
- Deliver APK **plus compressed ZIP** (large direct APK downloads have previously failed in ChatGPT), GitHub Action run/artifact, hash and concrete phone tests.
- Phone acceptance: automatic Eye AF marker follows **visible eye** in a side-profile scene; no duplicated Eye AF text plaque; arbitrary selected object, two subjects crossing, pet AF, Spot/Custom, AF-S/manual and failure states remain correct; no change in saved-image processing.
- Do not merge until user has validated on device. **No further concept generation**.

## Implementation instruction

Continue from this handoff and implement the approved **Balanced Extended Ticks** as a UI-only patch over M9Cam 3.10, then build and deliver a signed APK and ZIP. Do not ask the user to re-select any icon variant.

**References:** [3.10 baseline](https://github.com/mwilliams455/M9Camera_refresh/tree/codex/m9-autoeye1a-v3.10) · [3.10 Eye AF source](https://github.com/mwilliams455/M9Camera_refresh/blob/codex/m9-autoeye1a-v3.10/patches/autoeye1a/src/com/particlesdevs/photoncamera/ui/camera/HumanSubjectFocusController.java) · [Shared overlay source](https://github.com/mwilliams455/M9Camera_refresh/blob/codex/m9-autoeye1a-v3.10/patches/aftracking3b/src/com/particlesdevs/photoncamera/ui/camera/views/TrackingFocusView.java) · [2.78 tap-focus fix](https://github.com/mwilliams455/M9Camera_refresh/blob/codex/m9-autoeye1a-v3.10/patches/focuspoint1a/README.md).
