# GL2C — inverse tone sampler precision

20 September 2026. Parent: GL2B `be80363dcd723a2fea6c2b455bbff670d1af102d` (tree `9862752ea08ce58283ed9740ee20c9fec6eb2595`). Branch: `research/m9livegl2c-inverseprecision`.

## Report and evidence limits

New local recording `upload/01-40123.mp4`: 53.345 s, 1440x3200 H.264, 60 fps, no audio. Main/1x selector, HUD 24 mm f/1.6. The device model and installed APK cannot be established from the recording alone. Do not infer them from the lens selector labels.

As the user points towards the bright sky, foliage becomes very dark. From roughly 35–45 s, raising EV from +0.5 through +1.75 to about +3/+3.25 produces abrupt grey and yellow-green plateaus in the viewfinder. The photo opened in the gallery at the end has much smoother tonal detail. This establishes an unacceptable preview/still appearance discrepancy. It does not measure matching-pixel exposure parity: orientation, time and display scale differ.

The displayed capture stem appears to be `IMG_20260920_173642_1789922202808_00`. Its PRIMARY/diagnostic-burst files have not arrived locally. A screen recording cannot identify whether the source-contract path or fallback is active, the current inverse curve/matrices, actual preview energy, or HAL pixel behaviour.

## Reproduced source defect

GL2A/GL2B store each inverse-tone value as high/low bytes in two RGBA8 texture rows. The shader sampled the two byte planes with hardware linear filtering and reconstructed the 16-bit value afterwards. Although mathematically linear in exact arithmetic, the actual normalized 8-bit filtering loses precision. High-byte carries can produce discontinuities and even local reversals.

A GLES3 float-output regression executes the production inverse function on 8,192 RGB inputs (24,576 channel samples), three distinct inverse curves and a dense ramp across byte carries. The unmodified GL2B shader fails with maximum linear error **0.0019617296260200368** against independent CPU interpolation of decoded texels. This is far above 16-bit transport precision. It is a measured defect on Mesa, not a hypothesis based solely on the video.

An additional exploratory 8-bit full-path bracket using previously supplied portrait matrices (NOT the missing new-shot metadata) found a 7/255 downward neutral step at +3.25 EV with the old sampler. The revised sampler removed inversions beyond the existing <=2/255 integer colour-rounding variation. This is **not a reproduction of the severe scene-wide posterization in the recording**; do not present GL2C as a confirmed cure for it or for telephoto haze.

## Correction

Use `texelFetch` to obtain adjacent high/low-byte texels, reconstruct each 16-bit linear value, then interpolate those values in high-precision shader arithmetic. Endpoint indices clamp correctly. No display-domain fit, colour offset, black subtraction, special camera ID or new metering rule is introduced.

- Shader revision: `M9LIVEGL2C_INVERSEPRECISION`.
- Source diagnostics report that revision and `inverseToneSampling=decode_16bit_texels_before_float_interpolation` when active; fallback reports `bypassed`.
- `M9PreviewMath2A` documentation now describes the required sampling order; byte generation is unchanged.
- APK version suffix adds `m9livegl2c`.

The corrected inverse test returns maximum linear error **1.3608522120289734e-7**, a strictly nondecreasing red ramp, exact black, and equivalent results with linear and nearest sampler parameters. Errors remain bounded across -4 to +4 EV.

The inherited native SAT2/curve02 oracle still matches **24,576 pixels with zero channel difference**. It also compiles the full external-OES program and executes the 2D fixture path and fallback. The new precision regression uses a float framebuffer only in the host test; the Android preview output format is unchanged.

## Frozen boundaries and validation

The manifest freezes the RAW renderer/native kernel/firmware assets, source matrices and white-balance construction, exposure allocator, preview exposure-scale calculation, MainRenderer camera-texture binding and GL2B focus fix. Only four assembled files change: shader, diagnostic revision, math documentation and build version. Shipping source lives in overlays; do not commit assembled `PhotonCamera/`.

Validation:

- Parent negative control fails specifically at inverse sampling precision.
- GL2C inverse precision and filter-independence checks pass (49,152 channel samples across two filter modes).
- Existing focus, math, atomic-publication and exposure tests retained.
- Clean GL2B -> GL2C overlay replay and photographic hash freeze pass.
- Dedicated CI workflow builds and checks exact packaged shader/curve bytes and revision markers before publishing an APK artifact.

Phone cadence and image parity remain unverified; the new sampler uses four direct texel fetches per channel instead of two hardware-filtered samples. Actual GPU cost must be checked on the device.

## Next decisive evidence

Ask for matching `_M9_PRIMARY.json` and `M9_DIAGNOSTICS_BURST_*.json` from the shot in this recording, plus which phone/build was used. Inspect `shutterPreview1W.source2A`, readiness/fallback reason, intended/actual exposure ratio and texture/result identity. Do not request all older JSONs again.

If GL2C still shows grey/green plateaus with a valid source contract, capture the unmodified OES input alongside transformed pixels under the same frame state. Metadata alone cannot certify that the HAL applied its reported curve/CCM or that the incoming stream retains recoverable shadow detail. Do not globally retune M9 colour, hardcode WB, or change Auto metering to conceal this rendering fault.

Telephoto haze and post-capture focus are still separate open hardware checks. GL2C retains GL2B's focus correction. No WB/yellow-cast correction is included.
