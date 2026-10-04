# M9Cam 2.41 UIOVERLAY1C — startup cancellation fix

The user reported that 2.40 crashes on opening. Their Photon log ends during startup and contains no fatal stack trace; it does not identify the thrown exception. The failure below was independently reproduced against the unchanged 2.40 view implementation in a resource-backed Android API 35 Robolectric test.

## Cause and fix

M9OverlayController.refresh() disables the new flat manual ruler until camera controls are ready. Android View.setEnabled(false) dispatches cancelPendingInputEvents. M9LinearManualView.onCancelPendingInputEvents() cancelled its own gesture but omitted the required superclass callback. Android consequently threw SuperNotCalledException before the camera screen was usable.

The production fix calls super.onCancelPendingInputEvents() before cancelling the ruler gesture. No other production Java or layout change is included. The straight ruler and clipped opaque controls remain. The build advances to version 2.41-m9uioverlay1c / 27241.

## Regression coverage

The new resource-backed lifecycle test inflates the actual flat-control layout, disables it as at startup, dispatches cancellation through its parent, re-enables it, and pauses/stops the host activity. It failed on the original implementation at View.setEnabled(false) with SuperNotCalledException. A second test covers disabling during a drag, a stale ACTION_UP, and a fresh gesture after pause/resume; it verifies that cancellation completes once without extra parameter writes.

Robolectric 4.16.1 is a test-only dependency. Tests explicitly use Android API 35 and a plain Application to isolate the UI from camera hardware/native startup. They are not a complete device camera launch or photographic validation. The accepted photographic baseline remains 2.38 BRACKET1A; 2.40 is a rejected startup candidate. Monochrom remains unmerged.

## Recovery

assemble.py chains the hash-checked uioverlay1b source into a fresh destination before applying this patch. verify_source.py takes parent 2.40 source, candidate 2.41 source, and output-report path. The runner/init script record the local Java 17 and SDK/cache paths; adjust those paths when restoring elsewhere. A first build needs the test dependencies downloaded; subsequent builds can use the recorded offline runner.

package.py takes source, built APK, accepted 2.38 APK, build tools 35.0.0, and output directory. It preserves all 25 accepted native library entries and checks every asset, signing certificate, package/version, and ZIP alignment. The private recovery bundle still requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26). Use its latest tip. Nothing was pushed publicly.

## Build result

Build succeeded; 8 selected suites / 52 tests, zero failures, errors or skips. Source verification found only three changed/added files and 1,229 identical parent files; patch round trip passed. Final signed APK SHA-256: c1cd4ca0457c18c5d66fa4ae5f78c3dc397a834fc5a8c5576d477059c6c8d8ac. Handset verification remains pending.
