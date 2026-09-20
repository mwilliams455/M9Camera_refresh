# GL1W — atomic preview state and shutter evidence

20 September 2026. Parent GL1V: `6f78b15cdc3b432fe471bd1caa443297ee463e9b` (draft PR29).

The user reports GL1V works better on Xiaomi 15 Ultra but not Xiaomi 17 Ultra. Preserve the reported improvement. This candidate fixes a preview-state race and makes the main photo diagnostic contain the state used for the last GL draw. It does not claim to solve cross-device tone/colour parity or Auto metering.

## Latest 17 Ultra evidence

Attachments: `695.mp4`, `01-1789899751351.jpg`, and diagnostics for `IMG_20260920_112141_1789899701208_00`. The video includes Photo, gallery DNG then JPEG, and later EV adjustments. The supplied still is Photo EV0, Auto ISO/shutter; it is not a manual-exposure bracket.

The planned, requested and actual sensor exposure agree: ISO50, 2,292,713ns (approximately 1/436s), AE off. Auto EV is zero with neutral-deadband reason. Reference/intended exposure are equal, so intent scale is 1. RAW hard clipping is 0.03875%; TC20 requests +0.757EV and TONEBOUND limits the applied gain to +0.5EV. The top-level gain field is the unbounded request, not the final bounded value. The sampled JPEG median is 16; the supplied reduced JPEG closely matches these output statistics.

Production GL1V replay of recorded scene statistics gives sceneKey .35, gain -1.007EV, gamma 1.211, global pair strength 1 and spatial strength 1. The new GL1V gate therefore adds nothing for this particular composition: the old gate already qualifies fully. This is replay of the installed-source candidate, not a measured GPU uniform snapshot. Do not infer build identity solely from the unchanged EXPOSUREPLAN1B marker.

Current MFM replay counts no bright regions, returns a negative candidate of approximately -0.0235EV, then deadbands to zero. The relative threshold here is about Y177.86 and is within range; regional averaging still yields no qualifying region. Do not conflate this with the earlier 10:44 scene whose threshold exceeded Y255. The Auto policy still needs investigation with suitable scene/reference evidence.

The screen recording shows substantial tonal variation as composition changes. Approximate homography alignment of frames at 21.5s and 23s to the supplied JPEG gives median linear-luma differences of -0.51EV and -1.56EV respectively. These are encoded-video comparisons with moving framing, not a verified shutter-matched pair; neither is a sound basis for a new global curve. The active GL colour path preserves processed OES chroma with luma scaling; it does not execute the RAW renderer's native colour/SAT2/curve02 path.

The supplied two-entry burst contains capture/PRIMARY; the separate earlier five-entry bundle named in diagnostics (`M9_DIAGNOSTICS_BURST_1789899704271_5.json`) was not supplied. Old `previewAvailable:false` refers to the disabled CPU bitmap preview, not absence of the active GL preview.

## Source change

Previously, CameraFragment called exposure, illuminant and tone setters separately. Each requested a redraw, and the renderer read independently volatile scalar fields while the camera callback could be changing them. In particular, the four tone fields could come from different updates in a single draw. This race exists in source; the recording does not establish it as the sole cause of the 17 Ultra mismatch.

GL1W publishes a single immutable state after the callback has computed exposure, illuminant and tone. The GL draw reads that reference once and uses its values throughout. Existing numerical guards and all photographic functions are preserved. Each draw records that same state, the OES texture timestamp and command-submission monotonic time. A texture/result timestamp mismatch remains explicit; the patch does not synchronize the two streams or claim verified compositor presentation.

At shutter, the last draw snapshot is serialized once and attached to an immutable copy of the existing capture plan. The PRIMARY exposure-plan JSON now carries `shutterPreview1W`, including actual submitted uniform values, copied tone inputs, draw age, plan/camera identity, texture/result timestamps and the truthful active colour-path description. Missing, stale or mismatched draws are visible; no later preview update can replace the evidence. This uses the existing request-tag and PRIMARY transport, so diagnosis no longer depends solely on a separate LIVEPAIR bundle.

There is one small state/statistics copy per camera callback and one small draw record per render. JSON encoding occurs at shutter, not per frame. There is no GPU readback, new stream, RAW preview processing, new capture wait or extra sensor exposure.

## Verification and limits

43 focused assertions compile the actual production draw method and force a new state publication partway through its uniform calls. They verify one-state-per-draw behavior, later-frame adoption, immutable shutter evidence, timestamp/camera mismatch reporting, unavailable/stale state and inherited numeric guards. The existing 479 exposure/route and 84 spatial checks pass. A clean parent-file replay verifies the overlay; Android assembly and APK contract checks run in the dedicated workflow.

The manifest freezes the shader, tone model, auto allocator/policy, still renderer, native calibration, SAT2/curve02, manual controls and frame-count policy. CaptureController changes only to attach the immutable diagnostic to the same plan. No device-specific gain or colour adjustment is introduced. Do not promote or merge from host checks alone.

Next phone evidence: same fixed window framing at Auto/EV0 and a positive/negative EV, each with JPEG plus PRIMARY (or the burst containing PRIMARY), and an ordinary indoor control. The snapshot will distinguish GL input state/timestamp issues from tone-model mismatch without asking for a separate LIVEPAIR file. Repeat a small 15 Ultra control to check the user's reported improvement is retained. Saved manual EV response and Auto placement remain unvalidated by the current single EV0 capture.
