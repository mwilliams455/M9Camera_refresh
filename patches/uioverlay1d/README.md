# M9Cam 2.42 UIOVERLAY1D — clear settings navigation

The user confirmed that the 2.41 startup fix worked, asked to hide video entries under Other capture modes, and questioned the gear's extra quick-controls step. This candidate keeps the accepted straight-control overlay and separates shooting shortcuts from application settings.

## Navigation

- The gear beside ISO / Shutter / EV / Focus calls the original settings-button action directly, opening the existing app settings screen.
- A 48 dp chevron beside AE-L opens Shooting controls: self-timer, grid, display aids, torch, white balance, zoom lens lock and Other capture modes. The redundant All settings row is removed from that panel.
- Other capture modes shows Night and Unlimited; Video and RAW Video are hidden. Photo then Motion remain on the main camera strip. Saved Photon mode ordinals and capture implementations are unchanged.
- The video-settings PreferenceScreen is hidden in both the M9 and fallback Photon settings hierarchies. Stored preference keys, defaults and values are retained. The M9 Advanced summary no longer advertises video and its former Video and app category is named App.

Image/capture/output/display/app preferences stay in the app settings hierarchy. Frequently used shooting actions remain accessible while composing. AE-L stays directly visible. No photographic processing change or Monochrom integration is included.

## Validation and recovery

Source verification checks the three-state timer dispatch, direct gear delegation, separate chevron, capture/save guards, hidden video entries, unchanged setting keys/defaults, unchanged photographic code, and patch round trip. The two real Android view-lifecycle tests from 2.41 remain in the build; no additional tests were added for simple menu visibility edits.

assemble.py chains uioverlay1c into a fresh destination. verify_source.py takes 2.41 source, 2.42 source and output-report path. The runner/init script contain local Java 17 and SDK/cache paths; adjust when restoring elsewhere. package.py takes source, built APK, accepted 2.38 APK, build tools 35.0.0 and output directory. It preserves all 25 accepted native libraries and verifies every asset, signature, version and ZIP alignment.

The recovery bundle requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26). Use the latest tip. Source is retained privately; no public push. This build needs phone UX confirmation; 2.41 startup and 2.38 photographic processing are the user-confirmed references.

## Build result

Build passed: 8 selected suites, 52 tests, zero failures/errors/skips. Source verification found 8 changed/added files and 1,225 identical parent files; patch round trip passed. Compiled chevron and hidden video preferences verified. Final APK SHA-256: 2ccb489ccfde1345a6bdb375a37170aeb23a189819b09bd7ec783447eb9cfe64.
