# M9Cam 3.11 FOCUSOVERLAY1A — Balanced Extended Ticks (design locked)

**Parent:** signed M9Cam 3.10 AUTOEYE1A, versionCode 27310, build from successful Actions run 40370915580.
**Branch:** `codex/m9-focusoverlay1a-balanced-ticks`. Keep `main` and 3.10 untouched until actual phone validation.

## Visual-only change

- Replace the shared full focus rectangle with four unconnected anti-aliased, white/warm-white right-angle corners. The segments are 22% of the short side, approximately 6–11 dp, in a cached 32-float array; black translucent under-stroke improves bright-background readability.
- White is **tracking/acquired**, not proof of optical sharpness. Pending / holding / lost remain amber with their original distinctly described state labels. Existing TalkBack descriptions are unchanged.
- Remove the duplicate permanent black-backed Eye AF badge and generic active text. Keep Eye AF's explicit accessible description, validated eye target and exact view-coordinate transform.
- Use the inherited overlay for human eye, pet, object and area indicators. No new overlay, no new models/permissions/menu.
- Keep ordinary tap-circle position, gesture, animation, layout and Monochrome 2.78 first-launch coordinate fix unchanged. No colour/exposure/reconstruction/rendering modifications.

## Testing and release

- JDK `FocusTickGeometryHostTest` tests 4×2 independent line segments, translation, small eye visual minimum, density, canvas-edge clipping, NaN/Inf, negatives and off-screen conditions.
- Inherited human Eye AF, profile admission, animal-eye, identity/predictor, tracking, manual focus, shutter and profile Android tests must pass.
- Package only from the exact signed 3.10 parent, SHA-256 `0700e8672ec750211d935b334796dbb726def78c66e3568232ecaeb1b185a1ae`. Verify prior signing cert, 16-KiB alignment, 37 native libraries and 301 assets **byte-for-byte**, and both M9/Monochrome menus.
- Deliver signed `M9Cam_3.11_FOCUSOVERLAY1A.apk` and ZIP for user to install over 3.10 without clearing preferences. Verify marker placement near one/profile eye, manual toy tap override, pet AF, Wide/Spot/Custom, bright background, lens and orientation changes and stale overlays. Optical focus success still requires captured-image checking.

**No merge until user inspects real phone screenshot/video.**
