# GL2E — locate the persistent 17 Ultra telephoto preview haze

20 September 2026. Parent GL2D: `8aefbcd63736c615b592c73d44b6d9d86f8d838c`, tree `a684f0fd5953735e8e1a5950518478582f453fed`. Branch `research/m9livegl2e-previewevidence`.

## Report and limits of the evidence

Malcolm reports the Xiaomi 17 Ultra telephoto is still white/hazy after delivery of GL2D. The earlier `1126.mp4` recording showed a raised preview grey floor while the displayed saved photograph retained deep blacks. Its matching 17:11:22 capture has M9/SOURCECAL/RAWSHADING/DEVICEPORT/TTL sidecars, but no matching PRIMARY or diagnostic burst in the supplied local set. There is no new GL2D capture or screen recording in this turn. Do not silently treat the earlier video as proof of current Auto EV or source-contract readiness.

The normal shader preserves true zero input. It can amplify an already nonzero floor through the source conversion/tone curve or exposure. GL2D's new Auto lift only accepts a broadly dark neutral-reference rendering; it adds no black offset. These facts do not establish the phone's incoming pixel range, whether it honors the reported tone curve, or the source of the haze. Subtracting 16/255, fitting contrast to a screenshot, changing WB, or disabling the M9 render for all telephotos is not supported by the evidence.

## Implemented diagnostic

`M9PreviewEvidence2E` draws three 32x24 panels from the exact same OES texture and immutable frame state, once per second:

1. `incomingOes`: sampled incoming RGB, before the app's M9 transform and exposure simulation. This is processed camera output, not RAW or the YUV plane.
2. `referenceRender`: the current M9 or explicit fallback path at neutral reference exposure (excluding intentional Auto/user EV). Reference scale is clamped to the existing preview bounds and recorded.
3. `displayRender`: the same path at the displayed exposure scale, with focus peaking excluded.

The 96x24 RGBA atlas is 9,216 bytes. Pixel-pack-buffer/fence readback uses a later zero-timeout poll, never a blocking GPU wait. Results are copied into immutable evidence before unmapping. Framebuffer bindings, pack buffer, viewport, scissor, texture unit/binding, exposure, peaking and diagnostic-mode uniform are restored. Actual phone performance remains unmeasured.

A tiny shader branch enables only the incoming-OES diagnostic panel. Its default/display value is zero; normal M9 arithmetic and inherited colour oracles remain intact. The normal draw explicitly sets zero, and the diagnostic restores zero even on failure. The evidence collector is independent of GL2D Auto metering: it also records manual EV and source-contract fallback states, and it never feeds or invalidates the Auto policy.

At shutter, `shutterPreview1W.pairedPixels2E` contains:

- Each panel's RGB bytes as `rgbHex` (32x24 pixels, RGB channel order, GL bottom-to-top rows), plus minimum, q01, median, q99 and maximum integer BT.601-like luma.
- Sample camera/mode, plan ID, user/Auto EV, capture user/Auto EV, observed/reference exposure, reference/display scales, source matrices and the full reported RGB tone curves.
- Texture/result timestamps and equality/delta; submission age; the SurfaceTexture dataspace tag on API 33+ (`-1` unavailable, `0` may mean unknown).
- Explicit `sameTextureForAllPanels=true`, `sameFrameAsShutter=false`, `displayPresentationVerified=false`, `focusPeakingIncluded=false`.

This is a recent paired probe, not a claim of exact shutter-frame, metadata-frame or display-compositor identity. Wrong-camera/mode or older-than-2.5-second evidence is rejected explicitly. A GPU failure disables only this evidence collector for that surface and records a reason. It does not change photographic rendering or metering. Camera switching cannot expose another camera's pixels as current evidence.

Reported RGB tone curves are defensively copied into the immutable source context and included in diagnostics. Source inversion math is unchanged.

## Validation

- 26 assertions using the actual evidence collector and recording GLES stubs: three-panel ordering, reference/display scale separation, RGB layout, delayed mapping, zero-timeout fence, state restoration, fallback/manual EV collection, timestamps/dataspace, stale/wrong-camera rejection and failure isolation.
- The atomic renderer test compiles the actual modified draw/snapshot methods with an evidence stub, retaining its 38 assertions. It forces a mid-draw state publication as before.
- Production shader test verifies 2,304 incoming RGB bytes unchanged, including zero/16/75 code rows, despite an 8x exposure uniform. Returning to normal mode restores M9 rendering and zero input stays black.
- Inherited GL2D policy/allocator, focus, exposure, source math, GPU/native colour and inverse-precision checks remain in the dedicated CI workflow.
- Clean GL2D -> GL2E overlay replay and frozen source checks pass locally.
- No phone haze cause or visual fix is claimed.

Exposure/Auto policy, still RAW render, native kernel, calibration, WB, SAT2, firmware curve02 and focus correction are frozen. Assembled `PhotonCamera/` remains untracked; commit overlays/workflow/tests/findings only.

## Decisive phone check

Install GL2E on the 17 Ultra. Select telephoto, leave EV on Auto, hold the hazy composition for two seconds, then take one photo. Supply that shot's `_M9_PRIMARY.json` and a viewfinder screenshot showing the haze. A main-lens shot in the same light is a useful control, but is not required before investigating the telephoto data. Keep the composition steady for the short probe interval.

Read `pairedPixels2E` before proposing colour or black-level changes. If absent/unavailable, inspect its reason and build identity. If incoming RGB is already raised, examine dataspace and the producer's actual transfer before changing the M9 target. If the floor appears only after conversion, replay the recorded RGB through the recorded inverse curve/matrices. If it appears only in `displayRender`, examine scale and exposure ownership. Even a raised incoming floor can be genuine scene light: do not infer a limited-range defect from the minimum alone.

Relevant Android contracts checked against official documentation: [SurfaceTexture.getDataSpace](https://developer.android.com/reference/android/graphics/SurfaceTexture#getDataSpace()) reports the latest acquired texture's tag on API 33+; [CaptureRequest colour transform](https://developer.android.com/reference/android/hardware/camera2/CaptureRequest#COLOR_CORRECTION_TRANSFORM) describes sensor-to-linear-sRGB conversion. Neither proves a device's pixels exactly match its metadata.
