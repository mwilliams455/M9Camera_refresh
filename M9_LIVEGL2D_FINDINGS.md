# GL2D — restrained Auto placement from the M9-rendered preview

20 September 2026. Parent: GL2C documentation head `49fd2521ebd3ab98ab96e801bb2a11c440577599`, source tree `903df183788e04e709c1f576e41e4bcd48c5b648`. Branch `research/m9livegl2d-autoplacement`.

## User request and gap

Malcolm reports GL2C looks better. New requirement: when the scene looks very dark and EV remains Auto, brighten it automatically, carry that intent into the saved image, and retain restrained M9 appearance.

The existing MFM meter uses relative geometry in a pre-render Y grid, with +0.75/-0.5 EV bounds. A uniformly dark scene can have no relative contrast and therefore no assist. It does not measure the M9-rendered viewfinder. Increasing its fixed gain would not close that information gap.

## Implemented behaviour

A small GPU meter uses the **unchanged GL2C M9 shader** to render seven 32x24 probes of the same camera texture at neutral-reference exposure plus 0, +0.25, +0.5, +0.75, +1, +1.25 and +1.5 EV. These are display predictions from one frame, not seven sensor captures and not HDR. The meter does not include the currently applied user/automatic EV, so an automatic lift cannot provoke a compensating darkening or accumulate in a feedback loop.

The added policy requires a broadly dark frame: centre-weighted median below 40/255 and more than 55% of pixels below luma code 32. It searches for the smallest safe bracket approaching a modest shadow median of 60/255, not a middle-grey normalization. It rejects candidates adding over 1.5 percentage points of channel clipping, over 4 percentage points of bright pixels, or a median above 80. Total positive Auto placement is capped at +1.5 EV. Already-clipped windows do not, by themselves, prevent a lift; small highlights can be missed by this coarse meter, so the clipping budget is a sampled guard, not a full-RAW guarantee.

A soft confidence ramp suppresses threshold flicker. Upward change is at most +0.25 EV per fresh GPU sample; repeated camera callbacks cannot increase it again. Reduction is immediate when a new scene no longer supports the lift. Images with no measured recoverable signal receive no extra boost. Healthy scenes and isolated dark objects do not trigger the new lift. Existing signed MFM placement remains the fallback/baseline; the new assist is combined by maximum, not added on top of it.

Manual control:

- EV Auto (zero combined EV) permits new placement decisions.
- Choosing nonzero EV holds the Auto baseline already displayed, then adds the user's EV through the shared exposure plan. This avoids +0.25 EV accidentally darkening the preview by dropping a larger Auto lift.
- Returning to Auto resumes scene decisions.
- Manual ISO or shutter disables this automatic placement.
- Unlike the old MFM geometry assist, this rendered-darkness measurement may assist Auto on a tripod; tripod still controls shutter/ISO allocation.

This is an app exposure policy designed to preserve the current M9 rendering. Thresholds are not claimed as recovered Leica firmware constants or numerical reproduction of M9 metering.

## Capture/render connection

`IsoExpoSelector.planM9LiveExposure1A` calculates the unchanged neutral reference first, asks `M9AutoExposure2D` for total Auto EV, then allocates the intended ISO/shutter using Auto EV plus user EV. That immutable plan continues to drive the live exposure scale and the single RAW capture request. Existing TC20 intent normalization measures against the neutral reference, so it does not cancel the new lift. Integer ISO/shutter rounding and physical limits still apply.

`M9ExposurePlan1A` revision is `M9EXPOSUREPLAN2D`. It carries an immutable placement diagnostic snapshot preserved when shutter evidence is attached. PRIMARY `renderedAutoPlacement2D` records meter validity/status, reason, sampled bracket, timing, neutral reference energy, recommendation, applied Auto EV and user EV.

The colour/tonal transform, firmware SAT2/curve02, WB/source calibration, RAW renderer/native kernel, JPEG encoding and GL2B focus correction are frozen. Exposure and the GL metering pass change. Still TC20 can retain its existing bounded +/-0.5 EV normalization relative to the live approximation; this remains a parity limitation, not a newly corrected colour/tone path.

## GL behaviour and ownership

`M9PreviewMeter2D` runs only on the GL thread. At most four probes per second draw a 224x24 atlas (5,376 pixels / 21,504 RGBA bytes). A pixel-pack buffer and fence defer mapping until a later zero-timeout completion poll. No new RAW preview reader, CPU demosaic or blocking GPU wait is introduced. Read/draw framebuffer, pixel-pack binding, texture unit/binding, viewport, scissor state and exposure/peaking uniforms are restored. Focus peaking is disabled only inside measurement draws.

The sample is accepted only for matching camera/mode, recent submission (<=1.2 s), reference energy within 0.25 EV, matching source camera, and texture/result timestamps within 150 ms. This is bounded correspondence, not proof of exact frame synchronization. Unsupported colour-contract fallbacks are not treated as M9 meter input. A failed readback disables the meter for that GL surface and logs/publishes a reason; the old meter remains available. Surface recreation resets Auto state. Camera/mode switches discard ownership of the previous Auto baseline.

Actual phone frame rate, GPU mapping cost and visual Auto placement remain unverified. The readback is small/nonblocking by design, but that is not a measured cadence claim.

## Validation

- Production pure policy plus actual allocator tests: darkness, healthy scenes, clipped background, new highlight clipping, overshoot, all-black samples, isolated dark objects, malformed metrics, atlas layout, rise throttling, manual EV handover, manual ISO/shutter, return to Auto, stale/wrong-camera/changed-energy/mismatched-timestamp samples, immutable plan diagnostics and TC20 intent preservation.
- Actual meter methods against recording GLES stubs: deferred mapping, zero-timeout fence poll, four-Hz throttle, matching context, manual control gates, GL state restoration and failure fallback.
- Production GLSL exposure atlases fed to the actual Java meter: dark scene selected +1.5 EV (median 22 -> 67), healthy scene no new lift, all-black no new lift, dark foreground with an already-clipped window +1.5 EV, highlight-risk scene only +0.25 EV, isolated dark object no lift. Synthetic identity-matrix input fixtures are not phone scene validation.
- Existing exposure-floor, manual-dial, focus, atomic publication and colour precision tests retained.
- Inherited native colour and packed inverse precision checks retained.
- Clean GL2C -> GL2D overlay replay and frozen photographic byte checks pass.
- Dedicated CI builds the APK and verifies packaged shader/curve bytes and revision markers.

New tests: `patches/tests/m9livegl2d/`. The inherited fake-hardware compiler conditionally includes the new policy; the atomic renderer test adds a meter stub while keeping its actual draw-body test. Source is shipped through `patches/m9cam-m9livegl2d.patch`, not by committing assembled `PhotonCamera/`.

## Phone check

Use Auto ISO/shutter/EV in a dark backlit scene, hold composition for about two seconds, and capture. Preview and saved JPEG should both receive the restrained lift. Move to a normally lit scene and confirm it does not stay brightened. Then choose a small positive/negative EV: the image should move in the requested direction, with Auto no longer changing its baseline until returned to Auto. Check both sensors and watch preview cadence. PRIMARY `renderedAutoPlacement2D` is the decisive record if the lift does not occur or is too large.

GL2C's severe posterization is improved by user report but not independently established as fully resolved. Telephoto haze, post-capture focus validation and the source-WB yellow cast remain separate topics. No WB correction is included here.
