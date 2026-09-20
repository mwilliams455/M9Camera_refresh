# M9LIVEGL2A — controlled live input and M9 GPU target

Candidate following EXPOSUREPLAN1C commit 5165fd0be1ca30e2b20635c7ce1b4638f4051c87. The 17 Ultra bracket verified the exposure allocator but exposed a live preview built from several fitted display-luminance residuals. Main-lens backlight activated that stack much more strongly than telephoto. GL2A removes that active stack.

The photo preview requests an explicit sRGB-like Camera2 CONTRAST_CURVE (up to 64 points, spaced in output code). It retains AE and AWB. Android specifies that CONTRAST_CURVE disables complex colour LUT/chroma/nonlinear enhancements; FAST/HIGH_QUALITY colour matrices remain only an approximation to the ISP colour operation. Documentation: https://developer.android.com/reference/android/hardware/camera2/CaptureRequest#TONEMAP_MODE and #COLOR_CORRECTION_MODE.

Per returned physical-camera metadata, the preview inverts the actual reported monotonic curve, the reported colour matrix, white-balance gains and post-RAW boost. A read-only exporter reuses the production native physical-sensor context builder. Reconstructed sensor RGB receives the shared exposure-plan ratio before native white clipping, native sensor-to-ProPhoto D50, identity HSM, the M9 bridge, integer SAT2/M04_M05, firmware curve02 and TG1. SAT2 uses the production 14-bit rounding/branch/shift/LUT order. High-precision texture samplers are necessary: the shader test caught low-precision sampling differences before packaging.

There is no camera-ID appearance fit, Cobalt adapter, fitted gain/gamma/pair residual, extra RAW stream, CPU RAW rendering, per-frame pixel readback, still feedback or added preview delay. The inverse table/context is cached by camera, characteristics, neutral, reported curve, matrix, gains and boost. Existing atomic draw publication and shutter evidence retain the exposure and colour context together.

Missing/unsupported/noninvertible metadata takes an explicitly reported exposure-only OES fallback. It never applies RAW colour matrices to an unchecked fallback. `shutterPreview1W.source2A` records readiness, reason, camera, input domain, matrices, boost removal and limits. `curve02Live`/`sat2Live` describe actual enabled stages. Controlled curve reported in metadata is not proof the HAL obeys it in pixels.

## Preserved and changed boundaries

The exposure allocator, RAW native kernel, SAT2/curve02 assets and still-rendering call path are frozen. Removing the marked exporter block from M9R35Renderer.java must reproduce the entire parent file byte-for-byte. The preview request is separate from the RAW still builder. It does change the incoming YUV statistics used by the existing Auto algorithm: the policy arithmetic is unchanged, but Auto outcomes can change with the controlled input. This is intentional source normalization and needs device validation; do not call Auto calibrated.

This is a first architectural replacement, not demonstrated preview/JPEG parity. OES still contains ISP demosaic, shading and irreversible colour/gamut clipping. Inversion cannot recover clipped source channels or RAW highlight detail. Unequal green gains, singular colour matrices, missing post-RAW boost, unreported physical metadata or absent CONTRAST_CURVE take the fallback. No empirical camera-specific fallback is added.

Live TC20/RAW-tail and edge-placement normalization are not implemented in this candidate: the shader uses unity scene normalization and reports `unity_pending_live_linear_TC20_meter`. The still keeps its bounded TC20 and edge stages. The GPU TG1 conversion matches the native flat-pixel-pair operation but does not reproduce full-resolution horizontal 4:2:2 chroma sharing. Neither these remaining differences nor unknown HAL behavior should be hidden by another fitted display gain.

## Validation and next phone check

Host math: 3,126 assertions covering curve inversion transport, invalid curves, CCM inversion/layout, WB/boost/exposure order. Atomic draw test: 38 assertions, including publication during a draw and retained shutter evidence. Real exposure allocator: 2,561 negative-EV/energy assertions plus inherited 479 exposure assertions. Mesa GLES3 executes the production fragment shader with a 2D source fixture replacing only the external camera sampler. 8,192 vectors at each of three tungsten weights compare against the actual extracted frozen native C++ SAT2/curve02 function: 24,576 pixel comparisons, zero code difference on the recorded host. Full program and fallback pass the grey exposure bracket. These are synthetic host checks, not measured phone pixels or cadence.

Test main and telephoto with Auto/0, +1, -1 in the window scene, then one normal indoor scene. Capture the short screen recording and ordinary diagnostic bundle as before. First inspect source2A readiness/fallback and texture/result timing, then spatial tone/colour and the neutral/manual bracket. Confirm preview cadence and JPEG/DNG saves. If the metadata route is accepted but pixels remain wrong, inspect an unmodified controlled OES sample and actual transfer/colour behavior before tuning anything. Native RAW source input remains the stronger alternative if controlled OES proves unreliable; continuous RAW cadence would need separate evidence.

Keep this as a draft candidate. No merge until device checks support it.
