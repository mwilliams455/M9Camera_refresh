# M9Cam 2.32 PREVIEWBRIGHTNESS1A

Parent: `c3f63962b54f63590dda9fdb0cab90156cafc2a9`, phone-accepted M9Cam 2.31 DISPLAYAIDS1A. Malcolm confirmed on 4 October 2026: "It definitely works." The controls phase is complete. Current task is preview brightness/exposure consistency, preserving the accepted JPEG appearance.

## Confirmed gap and scope

The accepted saved renderer applies a TC20 scene-tone gain bounded to -0.5 through +0.5 EV. The preview predictor and shader previously allowed -0.5 through 0 EV only. Positive correction was intentionally deferred because live RAW highlight-tail measurements are unavailable. Existing supplied capture diagnostics contain actual examples of JPEG tone corrections of +0.50 and +0.1807 EV with preview tone gain at unity.

This candidate estimates both halves of that same bounded tone correction from the existing neutral-reference GPU probe. It changes the preview only. Saved JPEG/DNG code, all 25 native libraries, capture exposure planning, Auto/tap metering, settings, profiles and 2.31 display aids remain unchanged. There are no new controls and no global fixed brightness offset.

This is a first correction to a confirmed discrepancy, not a claim of complete WYSIWYG or identical ISP/RAW input. The camera's processed OES preview cannot recover clipped data, undo every ISP operation or exactly reproduce RAW spatial rendering.

## Prediction and safety boundaries

The existing four-panel, 32x24 GPU readback remains at its existing 250 ms eligibility cadence. There is no new panel, PBO, extra readback, full-resolution CPU processing or synchronous GPU wait. The fourth panel now packs neutral linear luminance in RG and maximum reconstructed physical-sensor RGB in BA, both as U16. Headroom is measured before the native white clip; luminance retains its original calculation.

Java retains the allocation-stable 12-bit centre-weighted luminance histogram and adds a persistent integer headroom histogram. Estimated tail selection follows the saved renderer's adaptive quantile and isolated-tail formulas, excluding samples encoded at sensor white, with the reconstructed maximum RGB channel as a conservative proxy. This is not the RAW CFA population, and must never be described as measured RAW headroom. Fully clipped headroom cannot authorize lift. Its guard has the existing unity floor, so it only restricts positive gain and does not invent darkening.

The requested gain is the smaller of the centre-weighted base gain and estimated headroom guard, then bounded to +/-0.5 EV. Existing 0.125 EV-per-sample slew and 0.04 EV deadband are retained. Positive prediction requires current and sampled non-held source contracts and texture/result timestamps within 150 ms. Invalid, stale or foreign camera/mode evidence reverts to unity; loss of positive-source eligibility immediately removes any positive held correction. The old negative behavior and incomplete-source exposure-only fallback remain.

The probe uses reference exposure, not selected exposure. User EV/Auto placement remains in the actual display sensor energy, preventing the tone estimator from compensating it away. The Auto/tap exposure probe still forces TC20 gain to exactly unity. Preview corrections cannot feed back into that camera-exposure policy.

The shader applies the estimate at the existing seam before firmware saturation and contrast. All existing colour matrices, curves, TG1 and exposure multiplication stay unchanged. Source identity, shutter plan selection and camera requests are unchanged.

## Diagnostics

The exact draw snapshot now records `uniformPreviewToneGain` alongside `uniformExposureScale`. Paired evidence records its sampled display gain, estimated headroom, base/guard gains, bounds and limitations. It no longer labels the latest asynchronous gain as though it were necessarily used for the older sampled display panel. The latest gain is separately available. Legacy `sourceContract.toneNormalization` text is not the authoritative tone-gain record; use the draw uniform and paired evidence fields.

Diagnostics remain optional. No new files are produced when the existing diagnostic switch is off.

## Verification

- Android build passed; 17 selected suites: 122 tests, 121 passed, one existing skipped test, no failures/errors. Thirteen new tests cover positive/negative bounds, headroom constraints, clipped/black data, panel addressing, read-only inputs, sample independence, bounded slew/deadband, nonfinite inputs and source/timestamp eligibility.
- Real production fragment shader compiled on Mesa GLES. 1,200 negative/unity pixels are byte-identical to 2.31. 1,800 positive pixels across all 25 saturation/contrast combinations exactly match the CPU firmware oracle. Packed luminance/headroom matches the U16 oracle exactly for the test inputs. Fallback remains unchanged, the tone probe is independent of applied display gain, and tested EV responses remain monotonic.
- Source verification checks 1,137 unchanged existing app source files, the five allowed preview changes, unchanged saved renderer/native/capture/Auto/tap sources, unchanged menus/profiles/display controls and the neutral-reference/unity-meter boundaries. The seven-file patch reproduces every manifest hash exactly.
- Private historical GPU/Java replay: tone-gain error decreased from 0.5000 to 0.3012 EV in one sample and 0.1807 to 0.0012 EV in another. These are two historical 8-bit OES panels compared with recorded JPEG tone gains, not paired new-phone images or proof of end-to-end parity. No photo-derived fit, lens offset or WB correction was introduced.
- Packaging preserves every 2.31 asset except the intended preview fragment shader, plus all 25 native libraries byte-for-byte. Signing certificate, package/version, 16 KiB alignment, compiled controls and ZIP integrity checked.
- Phone validation remains pending. Keep 2.31 as the accepted fallback.

## Phone check

Use the same framing before/after capture. Check a dim indoor scene and a brighter/window scene; compare viewfinder brightness with the saved JPEG. Check EV 0, -0.7 and +0.7 and one tap-meter action. The preview should track those exposure changes without settling back toward its old brightness. Try the lenses already in normal use, then background/reopen and check responsiveness. For a remaining mismatch, enable existing diagnostics and send the JPEG and PRIMARY JSON; the new draw/sample gain fields make the next discrepancy measurable. A same-framing preview screenshot is helpful but is not exact same-instant sensor evidence.

## Recovery and next work

`assemble.py <fresh-tree>` chains the exact 2.31 source. Use inherited `sharpnessmenu1a/build_native.py`, Java 17 and the Android SDK. Run `verify_source.py <2.31-tree> <candidate-tree> <report.json>` and `verify_preview.py <candidate-tree> <output-directory> <2.31-tree>`. Package using `package.py <candidate-tree> <built-apk> <accepted-2.31-apk> <build-tools-35.0.0> <delivery>`.

Source is local and included in the private recovery bundle; no public push is attempted. The inherited firmware-bank publication restriction remains applicable.

After brightness/exposure, continue preview colour and framing consistency with the accepted image as control. Cross-lens calibration and fringing investigations stay parked. Malcolm then wants an architectural review for a combined M9 Colour + M Monochrom app: share camera UI and infrastructure while preserving each accepted photographic pipeline, exposure behavior, DNG handling and per-mode settings. Optional M9 B&W/Vintage work is deferred behind that merger review.
