# GL1V spatial preview activation — 20 September 2026

Parent: EXPOSUREPLAN1B `bb3bca7cd1d9feb5200bf996c705d169fcfb6e31` (draft PR28).

## What this phone test establishes

The `615.mp4` recording shows Photo throughout, with no EV bracket. The 10:44:05 PRIMARY record contains EXPOSUREPLAN1B, a planned single-RAW request and `intentApplied: true`. User EV, auto EV and render intent offset are all zero. Requested and actual sensor values match exactly: ISO50, 1,516,447ns (approximately 1/659s), AE off. The exposure handoff is working for this capture. This is not device validation of Motion or the quarter-stop controls.

The still used SAT2 M04/M05, curve02, native sensor calibration and no Cobalt rendering dependency. TC20 gain was 1.03764 (+0.0533EV), raw hard clipping 1.904%, and output near-white fraction 6.980%. Its sampled final-bitmap mean/median were 81.237/43. The uploaded JPEG measured 81.198/43.181 at its reduced 1152x1536 resolution; this strongly supports its correspondence with the supplied capture. The recorded full output is 3072x4096. The recorded render time was 3,352ms.

## Separate meter and preview blind spots

Actual production Java was replayed with the supplied preview statistics:

- The auto meter's regional median was Y180.791. Its relative bright-region threshold was 180.791 × sqrt(2) = 255.677, above the maximum Y255. Therefore it counted zero bright regions even though the input had 28.89% of pixels at or above Y224. Positive confidence was zero, the negative candidate was -0.0216EV, and the deadband returned EV0. This explains the neutral decision; it does not establish that EV0 is the preferred M9 exposure.
- The preview classifier reported backlit=0, highlightPressure=1 and sceneKey=0.35. The steady-state gain/gamma were -1.007EV/1.211, and the existing GL1Q correction activated at only 0.13873. Bright global/centre medians hid the dark foreground from its global body/spread test.
- The 3x3 medians do retain that structure: the second-lowest tile is Y39 and the second-highest is Y224. At least two tiles support each end, with a 185-code regional spread.

## Bounded preview correction

GL1V adds a regional summary of the existing neutral 96x72 Y feed. It uses the second-lowest and second-highest 3x3 tile medians. Sorting makes this independent of quarter rotations/reflections, and a single dark or bright tile cannot qualify by itself. The additional activation reuses the existing shadow thresholds 68..108, spread thresholds 85..130 and global bright-support thresholds. It combines with the existing GL1Q activation using max().

Only the existing preview pair curve's activation changes. Its knots, shader, scene gain/gamma, still renderer, JPEG quality, native colour, SAT2/curve02 assets, exposure plan, MFM auto policy and Photo/Motion capture route are unchanged. User EV is not an input to the new gate. One small CPU pass over the already available 96x72 frame and reusable histogram scratch are added; there is no RAW preview request, GPU readback or full-resolution render.

The capture plan revision deliberately remains EXPOSUREPLAN1B. The new preview diagnostic marker is `M9LIVEGL1V_SPATIALGATE1A`; the APK version also appends `m9livegl1vspatialgate1a`.

## Offline comparison and limits

A video frame at 21.5s was aligned to the supplied JPEG using 362 homography inliers. With UI regions masked, the current preview is substantially brighter. A counterfactual reconstruction of the neutral OES luminance, using the current steady-state model, allows the existing correction to be evaluated at full activation without introducing a new curve.

On masked, non-extreme comparison pixels, median preview-to-JPEG linear-luma difference fell from about +2.21EV to +0.30EV; mean absolute difference fell from 2.15EV to 0.63EV. This is evidence supporting the candidate, **not on-device validation or measured RAW parity**. The reconstruction assumes steady-state parameters, uses an encoded video and approximate geometric alignment, and cannot recover clipped OES values. The preview colour path remains inherited processed-camera colour plus luma scaling. Full tone/colour parity is still unproven.

## Verification

84 focused assertions compile production regional summarization, the actual analyzer transport method, and the tone model. Cases include the supplied statistics, rotation/reflection, ordinary/low/high-key scenes, isolated bright/dark tiles, missing data, buffer bounds and EV independence. The existing 479 exposure/route assertions also pass. Exact source hashes freeze the photographic and capture paths. Android build and packaged-marker checks are tracked in the draft PR.

## Next phone evidence and auto work

Check the same window composition at EV0 first, then +/-0.25 with fixed framing and Auto ISO/shutter. Compare the visible preview to the saved JPEG, and include an ordinary indoor control. Retain **both** diagnostic burst files from each capture. This test's supplied two-entry bundle contains capture metadata and PRIMARY; PRIMARY names an earlier five-entry bundle `M9_DIAGNOSTICS_BURST_1789897448598_5.json` that was not supplied and may contain the live-pair state. Its contents have not been inspected. Do not call `previewAvailable:false` in the old CPU-preview diagnostic proof that GL preview was absent.

Auto metering remains unresolved. The relative threshold can become unreachable in bright-dominated scenes, and its inputs are vendor-processed Y, not M9-rendered scene luminance. Investigate that separately with multiple labelled scene/control pairs and available RAW headroom. Do not globally brighten the capture or change curve02 to hide the viewfinder mismatch. No EV-response bracket, original DNG or exact live-pair snapshot was supplied with this test.
