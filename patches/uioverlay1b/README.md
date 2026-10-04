# M9Cam 2.40 UIOVERLAY1B — straight manual rulers

Malcolm described 2.39 as a good first pass but reported a protruding grey square and asked for straight ISO/shutter scales instead of the circular dial (screenshots 49783.png and 49800.png). This incremental candidate follows 2.39; 2.38 remains the accepted photographic baseline.

## Change

The camera layout now includes a compact, flat manual panel. Its M9LinearManualView implements the existing KnobView contract for the unchanged manual console, so it receives the same device-specific KnobItemInfo objects and calls the original model selection listener. It draws upright text and straight ticks around a fixed centre marker. Drag left/right or tap a visible tick; keyboard/accessibility adjustment uses the same selection path. ISO, shutter, EV, focus and the existing white-balance control share the flat presentation. Only the active control is highlighted; the other values remain remembered by Photon.

The original hidden model-bound labels remain for existing observers, but reserve zero height and paint no background. The old dome background and height adjustment are skipped for the new view. The lens/render cluster rises only by the flat panel height. The lens/zoom controls use opaque rounded backgrounds with no separate GL blur footprint across the viewfinder boundary, addressing the reported protruding backdrop. Rounded controls also clip their touch foregrounds. AE-L stays on one line.

No changes to circularbarlib, capture/model code, physical exposure arithmetic, renderer, preview orientation/geometry, shader assets or native libraries. The existing manual-panel Back/swipe reset behaviour remains. Photo then Motion, settings beside the manual controls and M9-only renderer availability are retained. Monochrom has not been integrated.

## Validation

Android build succeeded. Seven selected suites, 50 tests, zero failures/errors/skips. New tests cover signed EV ordering and exact thirds, original shutter nanoseconds, descending focus distances, horizontal drag/tap/end stops, silent binding/reset, lens rebind and empty/fixed controls. Existing overlay/capture locks, AE-lock, timer, EV, bracketing and output contracts pass.

Hash-checked patch round trip passed: 14 changed/added files, 1,217 parent files identical. Packaging preserves all 25 native entries and every asset from accepted 2.38, verifies matching signing certificate/package, higher version 27240, compiled flat layout and 16 KiB ZIP alignment. No phone/emulator run: visual/touch confirmation remains pending.

## Recovery

assemble.py chains uioverlay1a into a fresh destination. verify_source.py takes the 2.39 source, 2.40 source and output-report path. The build runner/init script record the local Java 17, SDK and offline-cache paths; update those paths when restoring elsewhere. package.py takes the 2.40 source, built APK, accepted 2.38 APK, build tools 35.0.0 and delivery directory. It retains accepted 2.38 native bytes.

The private Git recovery bundle requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26), like previous recovery archives. Use its latest tip. No public push was authorized or performed.
