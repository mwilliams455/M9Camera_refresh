# M9Cam 2.44 UIOVERLAY1F — text mode strip and shooting icon panel

The user selected option 2 (Text strip) and requested a centred arrow opening icons to enable/disable shooting options.

## Behaviour

Photo then Motion remains below the shutter. Selected text is bright with a thin underline; inactive text is muted, and both retain 48 dp touch targets. The top chevron is constrained to the screen centre independently of the left torch/Night controls and right AE-L control. Status text occupies the space between the chevron and AE-L. A dark popup below the chevron contains six labelled stateful tiles: self-timer, grid, histogram, highlights, shadows and lens lock.

Taps toggle the actual option and keep the panel open. Timer and grid delegate to the existing Photon actions; display aids write the same existing display-only preferences as M9DisplayAidsController, using M9DisplayAids.withHistogram to retain the camera-info selection. Lens lock delegates to the existing LensZoomBarController action, and is unavailable without auto-switch or more than one lens choice. Holding the first five tiles open their existing choice sets. Last enabled choices use the private m9_overlay_ui preferences (quick_last_0..4); defaults on first explicit activation are 2 seconds, 3x3 grid, RGB histogram, 100% highlights and 0% shadows. Existing enabled choices are retained when toggled off/on. No capture preference defaults are changed.

Other capture modes remains a separate navigation row containing Unlimited. Video entries stay hidden. Popup/back/outside dismissal resets the chevron. Camera stop or a capture/processing/save lock closes the popup and its options dialog. Actions recheck availability, including from an already-open choice dialog. Accessibility exposes each tile's checked state and current value. Torch, Night, WB, app settings and the M9-only renderer selector retain 2.43 behaviour. Monochrom is not merged.

## Verification

Android build and all 62 tests across ten suites pass. Seven new Android-runtime panel tests exercise saved choice restoration across panel recreation, histogram/camera-info preservation, clipping thresholds including 0% shadows, busy/unsupported guards, lens-lock delegation and accessibility, long-press selection, dialog close and invalid saved values. One new Android-runtime geometry test covers 320/360/480 dp widths with AE-L visible and hidden. Its Photon app-service fixture was initialized before final passing run. Existing startup/cancel, manual ruler, mode, bracket, AE-L, self-timer, EV and save tests pass.

Fourteen files are added/changed; 1,230 parent files are identical. Patch application round trip passed. Photographic/capture code, shaders, assets, manual math and native sources match 2.43. All 25 native APK entries and every asset match accepted 2.38. Signature, version code 27244 and 16 KiB alignment verified. Device validation is pending; tests do not substitute for a phone launch or camera check.

## Recovery

assemble.py chains uioverlay1e into a fresh source destination. verify_source.py takes 2.43 source, 2.44 source and report path. The runner/init records local Java 17, SDK and cache paths. package.py takes source, built APK, accepted 2.38 APK, build tools 35.0.0 and output directory. The recovery bundle requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26); use its latest tip. No public push.

APK SHA-256: abbf263a9d67d33ade5b2d7c7c584907ecbd39e8432b1010227bd590b1c2c300
