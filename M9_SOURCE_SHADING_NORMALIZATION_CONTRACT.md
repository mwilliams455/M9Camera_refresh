# M9 source shading normalization contract

Status: SOURCESHADING1A research contract

## Architectural invariant

Physical-sensor-specific before common scene space. M9-specific after common scene space.

The portable source path is:

`physical RAW -> RAW geometry/CFA -> black/white normalization -> source shading normalization -> sensor colour normalization (SOURCECAL) -> CommonSceneFrame -> one shared M9 target renderer`

Source shading normalization removes the source camera module's residual vignetting and colour shading. It must not create or tune Leica/M9 optical falloff. Any intentional M9 optical behavior belongs after `CommonSceneFrame` in the target renderer and is shared across source sensors.

## Camera2 shading semantics used by the source adapter

For a RAW-capable Camera2 source, the live `CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP` is the authoritative per-capture correction evidence when available.

- The map contains four fully interleaved Bayer-channel gains in API order `[R, G_even, G_odd, B]`.
- The map spans the entire active pixel array and is independent of scaler crop.
- The map is bilinearly interpolated between grid sample locations.
- If `SENSOR_INFO_LENS_SHADING_APPLIED == false`, the result map represents the complete correction needed for the RAW source.
- If `SENSOR_INFO_LENS_SHADING_APPLIED == true`, RAW has already received partial or full shading correction and the result map represents the remaining correction. A fully corrected RAW may therefore report an identity map.
- Live `LensShadingMap.getColumnCount()` / `getRowCount()` dimensions are used for the delivered map. This project does not guess map geometry.

These semantics are source-domain facts. They do not depend on phone manufacturer, marketing zoom value, camera ID, focal-length label, or Leica target behavior.

## Exactly-once rule

Shading correction must be applied exactly once relative to the RAW data actually received by the renderer.

A future photographic `SourceShadingNormalize` stage may apply the live remaining map only after all of the following are proven:

1. The RAW buffer's coordinate origin and dimensions are mapped correctly to the Camera2 active-array coordinate system.
2. CFA phase at the actual RAW buffer origin is known.
3. The map corresponds to the active physical sensor that produced the RAW buffer.
4. `SENSOR_INFO_LENS_SHADING_APPLIED` and the live remaining-map semantics are respected, preventing double correction.
5. The four API map channels are mapped to the correct Bayer samples without collapsing them to one luminance vignette factor.
6. Cross-sensor diagnostics show that the correction reduces source-domain spatial shading/chroma divergence rather than merely changing the rendered look.

If any required property is unknown, the adapter remains diagnostic/fail-closed for shading rather than inheriting assumptions from another sensor.

## Manufacturer portability

The adapter selects behavior from physical RAW characteristics and authoritative metadata, not from labels.

Allowed inputs include:

- RAW dimensions, strides, active/pre-correction arrays and proven origin;
- CFA layout and local phase;
- static/dynamic black and white levels;
- `SENSOR_INFO_LENS_SHADING_APPLIED`;
- live Camera2 lens-shading correction map and its dimensions;
- Camera2 calibration/color/forward matrices and reference illuminants;
- live neutral / color-correction state;
- proven vendor RAW preprocessing state;
- empirical calibration data only when platform metadata is absent or demonstrated unreliable, with explicit provenance.

Forbidden selectors for photographic behavior include:

- camera ID alone;
- focal length alone;
- `0.6x`, `1x`, `3x`, `4.1x` or similar zoom labels;
- `ultrawide`, `main`, `tele` or other marketing/module names;
- manufacturer name as a substitute for physical calibration evidence.

A manufacturer-specific quirk may be represented only as an explicitly proven source-format/preprocessing fact. It must still normalize to the same `CommonSceneFrame` contract.

## Relationship to SOURCECAL2A

SOURCECAL2A should no longer be interpreted as only a colour-matrix operation. At the architectural level, SOURCECAL is the source-normalization boundary and should orchestrate separable physical sub-stages.

The intended decomposition is:

1. `RawGeometryCfa`
2. `BlackWhiteNormalize`
3. `SourceShadingNormalize`
4. `SensorColorNormalize`
5. emit `CommonSceneFrame`

Keeping `SourceShadingNormalize` explicit is important because spatial shading errors and sensor colour-matrix errors are different failure classes and must remain independently measurable.

## SOURCESHADING1A scope

SOURCESHADING1A is diagnostic only. It records:

- whether RAW shading is reported as already applied;
- live remaining-map presence and dimensions;
- four-channel map statistics;
- center/corner/edge spatial samples;
- channel spread and red/blue-versus-green spatial axis;
- approximate center-to-corner correction in EV;
- active/pre-correction/crop geometry evidence;
- explicit correction eligibility blockers.

It does not modify RAW, demosaic, SOURCECAL matrices, TC20, SAT3, curve02, BT.601, TG1 or JPEG output.

The first photographic shading implementation must be justified by device captures from multiple physical sensors, not just the first failing tele module.

## Validation matrix

For the current Xiaomi 15 Ultra test device, use all four physical RAW sources as architecture guards:

- camera 2: current main-source baseline;
- camera 3: guards against RGGB-only/CFA assumptions;
- camera 4: first clearly observed source-domain green/magenta failure, but not the definition of the solution;
- camera 5: guards against hidden 4096-wide geometry assumptions.

For a future device, the same validation is performed from its physical RAW descriptors. No new M9 target-renderer branch should be required merely because the manufacturer or lens set changes.
