# M9EXPOSUREPLAN1B: Motion capture-route correction

Parent: M9EXPOSUREPLAN1A, commit `75f8ec4f3bda6da7d79b66342c8a50f6c8215250`.

## What the 20 September device evidence establishes

The 43-second `39514.mp4` recording shows **Motion** selected, including while EV is adjusted and both captures are made. The metadata for 10:06:28, 10:08:31 and 10:08:50 independently reports `MOTION`. The three supplied PRIMARY records carry `exposurePlanRevision: M9EXPOSUREPLAN1A` but `intentApplied: false` and no immutable exposure plan. The new APK was running; its Photo-only plan gate excluded this actual test route.

Motion's inherited ZSL path drains already exposed RAWs from a preview buffer, then supplies the latest preview result/request to processing. It does not pass through the planned still-request tag. Hardware AE remained on and the manual EV dial changed hardware compensation. Recorded request ISO/time are not authoritative in AE-on requests. The ZSL metadata path also does not match each buffered RAW to its own timestamped result, so exact RAW/request identity cannot be inferred from those preview records.

| Recorded capture | ISO / exposure | TC20 gain | Raw hard clip diagnostic | Finished M9 bitmap median Y |
| --- | --- | --- | --- | --- |
| 10:08:31 | 50 / 766,646 ns | 1.1621 | 0.311% | 5 |
| 10:08:50 | 50 / 5,735,525 ns | 1.1374 | 6.274% | 52 |

The recorded exposure energy increased 7.48x (about 2.90 EV). This demonstrates that this sequence changed exposure. It is not a calibrated response measurement for the displayed +1.25 setting: framing/metering could change and the old ZSL path uses asynchronous preview metadata. It does not validate the new plan or small-EV preservation.

The gallery labels the opened file as `.dng`, and the inherited gallery loads DNGs through Glide. That view is not by itself proof of the final JPEG. However, the separately uploaded `39511.jpg` has mean Y about 99.31 and median 51.84, closely matching the 10:08:50 finished M9 bitmap's sparse measurements (mean 99.88, median 52). The photo's very bright window and dark foreground cannot simply be dismissed as the wrong gallery file. No original DNG was attached in this test, and the standalone 10:06:28 metadata is not the same shot as the 10:08:50 gallery image.

The native SAT2/curve02 path is still active. These findings give no reason to reintroduce Cobalt or change saturation/curve assets.

## Correction

- Extend the shared exposure-plan eligibility to M9 **Photo and Motion**.
- In those modes with GL preview active, route stills through one newly requested RAW at the planned ISO/shutter. M9 Motion no longer drains neutral-AE buffered RAW for the final photograph.
- Retain Motion's existing faster shutter-allocation limits, the existing single-RAW/no-HDR boundary and the GL1T continuous-preview policy.
- Keep non-M9 Motion's original ZSL behavior.
- Record `M9EXPOSUREPLAN1B`, `captureRoute: planned_single_RAW_request`, and `zeroShutterLagBufferUsed: false` in each attached plan.
- Keep the renderer, native color, shader, tone model, allocator, output quality and photographic assets byte-identical to EXPOSUREPLAN1A. This is a routing correction, not a newly tuned backlight curve.

Motion now incurs the same requested-still acquisition as Photo; it no longer promises zero shutter lag for M9 capture. Live preview remains on the continuous path. Device timing and visible continuity must be checked.

## Verification

472 host assertions pass using actual production plan, manual controls, allocator, MFM and capture-routing method. The earlier harness stubbed `isZslMode()` to false, so it could not discover this integration gap. The new harness compiles the actual method and exercises both Photo and Motion, including the non-M9 ZSL control. Exact parent/overlay and frozen-source hashes also pass. Android build status is tracked in the PR.

## Next phone test

Use the same window/toys scene in Motion. Leave ISO and shutter on Auto. Capture at EV0, then -1/3 and +1/3 with unchanged framing, followed by +/-1 if useful. Capture one ordinary indoor frame as a control. Retain corresponding JPEG, DNG, LIVEPAIR and PRIMARY/burst diagnostics, plus a screen recording.

First acceptance check: the PRIMARY plan exists, its mode is MOTION, its revision is M9EXPOSUREPLAN1B, and the requested still has AE off. The actual sensor result should be compared with the planned pair. Then assess preview/JPEG response, auto scene placement and continuous preview. The inherited empirical OES color/tone fit and scalar normalization's clipping limits remain unresolved until tested; this correction does not establish full visual parity.
