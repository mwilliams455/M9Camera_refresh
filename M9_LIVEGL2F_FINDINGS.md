# GL2F — repair the preview tone-curve request and reject contradictory results

20 September 2026. Parent GL2E: `b91a4f42af54526ee79a6ac3068cf889680587e8`, tree `08de4525f2053fc4450550b21356d65fed8ebeae`. Branch `research/m9livegl2f-curvecontract`.

## New evidence and conclusion

The supplied 20:07:24 PRIMARY and screen recording finally contain paired incoming/rendered GPU pixels for the hazy 17 Ultra telephoto. The video shows the grey viewfinder and a saved JPEG with deep blacks. The paired probe itself is 622 ms before shutter, not the same frame as the saved JPEG; its camera-result and texture timestamps match exactly.

Auto EV and user EV are both zero. Reference and display exposure scales are both 0.998518. Incoming luma minimum/median/q99 is 18/46/101; both M9-rendered panels are 78/152/210. This places the visible amplification in the source-to-M9 preview transform, not Auto EV or a white UI overlay. It does not prove all incoming nonzero black values are spurious.

All three returned tone curves are nearly linear, with uniformly spaced input coordinates and less than 0.0075 deviation from identity. Our old request used nonuniform linear-input positions and uniformly spaced output values. This return is consistent with the HAL treating the submitted output ordinates as a uniform-input LUT. That is a hypothesis about the HAL, not a verified internal implementation. The concrete defect is that the app never checked agreement between the requested and reported curves before accepting a controlled source contract.

Replaying all 768 incoming RGB samples through the actual production shader and recorded source context reproduces the device output with a maximum 3-code difference and mean 0.576 code across 2,304 channels. Input readback quantization can account for small differences. The shader itself is unchanged.

Replacing only the decoder on those old pixels with sRGB makes the cat substantially too dark (median luma about 29 instead of 152). A SMPTE-170M interpretation gives about 53. Neither is established as the correct interpretation of those old pixels. GL2F therefore does not force a gamma decoder onto this stream, subtract a fitted black level, or change M9 target colour.

The texture tag `146931712` is Android `DATASPACE_JFIF`: full-range BT.601-625 / SMPTE-170M. This does not establish that the custom Camera2 transfer was honored. It also does not justify subtracting a studio-range pedestal. [Android DataSpace](https://developer.android.com/reference/android/hardware/DataSpace#DATASPACE_JFIF). Camera2 curves define the requested combined contrast/tone/gamma response; the API accepts explicit input/output points. [Android TonemapCurve](https://developer.android.com/reference/android/hardware/camera2/params/TonemapCurve).

## Implemented change

Only two production files change:

- `M9PreviewMath2A.srgbCurve` submits uniformly spaced **linear input** knots with sRGB-encoded output ordinates. The request now has the same meaning for a standards-conforming interpolator and an index-addressed LUT. Use the existing supported point count, capped at 64.
- `M9GpuPreview2A.from` compares every reported channel with the configured request. It evaluates both piecewise-linear curves at the union of their input knots, which bounds the entire curve. A maximum output difference above 3/255 rejects the source contract. The tolerance permits small LUT quantization and resampling; the recorded near-linear return differs by over 0.28 and is rejected.

An agreeing result still uses its **reported** inverse, the native physical sensor matrices, and the existing M9 shader. A contradictory result uses the existing processed-OES exposure-only fallback until agreement recovers. That fallback avoids applying an untrusted inverse/M9 transform, but is not an M9 preview-parity solution. Its status is explicit in the sidecar. Both successful and rejected contexts are cached; recovery occurs when metadata changes. There is no device name, camera ID, brightness histogram, or screenshot-derived fit in the selection.

New source diagnostics: `M9LIVEGL2F_CURVECONTRACT`, `requestedToneCurve2F`, `toneCurveRequestSampling2F`, `toneCurveMaxOutputError2F`, `toneCurveAllowedOutputError2F`, `toneCurveAgreement2F`, and `toneCurveMismatchPolicy2F`. GL2E's full reported curves and paired pixel probe remain available.

The shader, SAT2/curve02, native still renderer, calibration/WB, focus continuity, and Auto policy implementation are hash-frozen. Changing the preview source response can change Auto's measured input; its existing shared capture/preview exposure plan remains in effect. No saved-image colour or tone constants change.

## Validation and limits

- 254 assertions exercising the production request builder and source-context constructor with API stubs: uniform-input knots, sRGB ordinates, resampling equivalence, recorded mismatch rejection, per-channel rejection, quantized acceptance, cache, recovery, immutable inverse and missing metadata.
- Inherited 3,126 source-math assertions, 26 evidence-collector assertions, 38 atomic-frame assertions and GPU/native colour/inverse precision checks.
- GPU replay of 64 spatially deidentified colour pairs from the real device evidence. The full spatial sample remains local; the repository fixture omits the photo, pixel positions, capture timestamps and other capture metadata. A rejected-contract draw preserves the incoming RGB at this approximately unit exposure instead of raising the floor.
- Clean GL2E-to-GL2F overlay replay and hashes of 30 frozen production files pass.
- Dedicated Android CI must pass before delivering the APK. The CI workflow preserves prior focus/exposure/Auto checks and verifies packaged markers/assets.
- The new request has not been tested on the phone. Do not claim the haze is fixed or viewfinder/JPEG parity established yet.

## Next phone check

Use the 17 Ultra telephoto at Auto EV in the same scene, hold steady for two seconds, then capture one JPEG. Send that shot's PRIMARY and a viewfinder screenshot/short video. Inspect curve agreement first: if true, compare new paired input/render values and the visible JPEG. If false, the new diagnostics show the exact remaining conflict; do not disguise fallback as M9 rendering. Check the main lens and 15 Ultra as controls once the telephoto source contract is established.

Assembled `PhotonCamera/` remains untracked. Commit overlays, tests, workflow and findings only. Keep the PR draft pending phone validation.
