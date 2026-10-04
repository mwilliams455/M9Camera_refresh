# M9Cam 2.39 UIOVERLAY1A

UI-only test candidate over accepted 2.38 BRACKET1A, requested before merging Monochrom. User selected the refreshed design: horizontal lenses, lower-right render selector, Photo then Motion, and settings beside ISO/Shutter/EV/Focus.

The native overlay delegates to the existing manual TextViews and camera handlers. It preserves the CameraMode enum and saved ordinals. M9 is the only installed renderer; Monochrom, M10-R and M11 are disabled future cards. No render preference is introduced or changed. Mode/manual/settings actions recheck readiness, burst/processing/countdown/bracket/recording and final-save status at dispatch. The shutter remains the existing control. Popups and handler callbacks are removed on pause/destroy.

The previous lens-position preference is retained but disabled in this UI. All other preferences and capture defaults are unchanged. Top chrome shows M9, optional timer and AE-L; other capture modes are available in the gear menu and identified in the heading. Legacy Photon quick settings remain reachable by the existing downward swipe.

Manual proxy cells retain the original model-bound TextViews in the view hierarchy. Their original option cells are hidden, and value/selection/rotation mirror to the persistent row. The original wheel, model, observers and camera parameter code are unchanged. Back/swipe retains the existing manual-reset semantics. The lens row and render button rise together with the wheel.

## Validation

Android build passed; 44 tests across six targeted suites, no failures/errors/skips. Source scope and hash-checked patch round trip passed: 16 added/changed files, 1,209 parent files unchanged. All capture, rendering, physical exposure, circularbarlib, shaders, preview geometry and native sources remain exact 2.38. APK packaging preserves all assets and 25 native entries from accepted 2.38, verifies certificate/package/version, controls, ZIP integrity and 16 KiB alignment. No phone/emulator run was available. This is not user acceptance; 2.38 remains the accepted baseline.

## Reproduce

- `assemble.py <fresh-tree>` chains bracket1a, checks parent hashes and applies this patch.
- `verify_source.py <accepted-2.38-tree> <overlay-tree> <report.json>` checks isolation and patch round trip.
- `run_uioverlay_build.py` and `uioverlay_test_runtime.gradle` record the exact local Java 17 / SDK / offline dependency-cache build environment. Update their workspace paths for a new environment. Build inherited native prerequisites via sharpnessmenu1a/build_native.py if required by the inherited assembly chain.
- `package.py <overlay-tree> <built-apk> <accepted-2.38-apk> <build-tools-35.0.0> <delivery>` creates the signed upgrade. Accepted 2.38 APK SHA256 is ca30fd5c41e44095f8fc1d142a967cbfd03092b978cf690c61634ce1ea608711.

The private recovery bundle requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26). It is not a standalone checkout. No public push is authorized or performed.
