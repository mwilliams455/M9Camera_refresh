# M9Cam 2.31 DISPLAYAIDS1A

Parent: `725322974b0f1fc4b36cd56a64aa03f533adc445`, M9Cam 2.30 SHOOTINGPROFILES1A, accepted by Malcolm on 4 October 2026 ("It works!"). Requested next: easier histogram and shadow clipping, using the Monochrom work as a reference.

## Controls

A histogram-shaped button beside the grid button opens Display aids directly from the viewfinder. Choose Histogram (Off, Luminance or RGB), Highlights (Off or 100–95%) and Shadows (Off or 0–5%). Each choice returns to the small controls dialog. Aids off disables all three without removing camera information. The button description includes the current choices for accessibility.

Settings > Display exposes the same persistent options. The existing camera-info selector retains its old values and adds histogram-only and information-with-luminance choices. Existing defaults and user settings are preserved; both new warning controls default to off. Warnings are global, excluded from per-lens snapshots and ignored on imported per-lens restores. They are not photographic profile fields.

Normal M9 Photo, Night, Motion and Video views use the new separate overlay. Raw-video and Unlimited retain the legacy HUD path; when one of the new histogram choices is stored, that path displays the legacy combined HUD/RGB histogram. Their older settings picker can still choose its original 0–3 values.

## Measurements

- Luminance or RGB histogram, 64 measured bins and 11 visual guide sections. The guides are not calibrated RAW EV zones. Histogram height uses square-root display scaling.
- Flashing red when any displayed RGB channel reaches the highlight threshold. 100, 99, 98, 97, 96 and 95% correspond to 255, 252, 250, 247, 245 and 242 on the sampled 8-bit scale.
- Flashing blue when all three displayed RGB channels are at or below the shadow threshold. 0–5% correspond to 0, 3, 5, 8, 10 and 13. Off is a separate value, so 0% remains a useful black warning.
- These percentages describe displayed code values, not sensor saturation, scene luminance percentages, saved JPEG values or recoverable RAW detail. A small downsample may miss tiny isolated clipped pixels. Focus peaking already present in the preview can affect readings.

The architecture follows the accepted Monochrom display-aid implementation inspected at `mwilliams455/MMonochrome`, commit `1716e806cc66ec999faff4e820c0f6927d92ab3a`, `apk/mono1a/monoleicasettings1j/apply.py`. Its live histogram and highlight warning provided the reference. M9 adds blue shadows and a direct quick-control button. The Monochrom magenta-removal heuristic is intentionally not copied: it would alter real magenta in a colour histogram.

## Display and rendering boundary

A 128x96 PixelCopy readback is requested at most once every 150 ms, with one in flight. It crops the GL surface to the visible photo frame, excluding the blurred outer preview. Rounded-corner pixels are excluded from both measurements and masks. Overlay masks align to the same frame. Histogram text handles both positive and negative landscape rotations; the mask stays in the already oriented surface coordinates.

The sampling controller owns its lifecycle and rejects callbacks after pause, preference changes, lens changes, geometry changes or destruction. It never recycles a PixelCopy destination before its callback. The overlay discards data older than 750 ms. Sampling stops while aids are off or the fragment is paused. The controls do not intercept focus gestures.

Clipping masks and histogram are Android View overlays, outside the GL surface being sampled. They cannot feed back into later samples or enter JPEG/DNG processing or video encoding. Capture planning, preview shaders, saved-photo processing, queue snapshots, profiles, assets and native source remain unchanged. CameraFragment edits are limited to controller lifecycle and display/HUD dispatch. All 25 native libraries and all assets are preserved byte-for-byte from the accepted 2.30 APK.

## Verification

- Source verification: 1,129 existing app source files unchanged; allowed edits are limited to display integration, global warning keys, layouts and settings resources. Existing photographic routes and defaults retained.
- Exact 14-file patch round trip against parent source hashes.
- Android debug assembly passed. Sixteen selected suites: 109 tests, 108 passed, one existing skipped test, no failures/errors. The 13 new tests cover legacy choices, histogram choices, exact thresholds and every boundary, colour-channel clipping, real magenta, input immutability, transparent/rounded corners, crop geometry, malformed preferences, separate sample ownership, and lifecycle/in-flight exclusion.
- Package verification: accepted 2.30 control hash, every inherited asset and native byte, package/version, same signing certificate, 16 KiB ZIP alignment, compiled display controls and resources, final ZIP integrity and content hashes.
- No phone or emulator UI run was available. Device acceptance should check overlay alignment, both landscape directions, quick control choices, return after backgrounding and viewfinder responsiveness.

## Rebuild and recovery

1. `python3 patches/displayaids1a/assemble.py <fresh-tree>` chains the pinned 2.30 assembly and verifies every input/output hash.
2. Use inherited `patches/sharpnessmenu1a/build_native.py <tree> <NDK-27.0.12077973>` and build with Java 17 and the Android SDK.
3. Run `verify_source.py <parent-tree> <tree> <report.json>` and the display/profile/photographic tests.
4. Run `package.py <tree> <built-apk> <accepted-2.30-apk> <build-tools-35.0.0> <delivery>`.

Source is committed locally and included in the private recovery bundle. No public push was attempted; the inherited firmware bank's existing publication restriction still applies.

After handset acceptance, the next agreed work is preview-to-JPEG consistency. Preserve the accepted image processing and keep the fringing investigation parked.
