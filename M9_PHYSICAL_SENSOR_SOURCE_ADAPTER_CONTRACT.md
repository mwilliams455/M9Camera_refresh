# M9 Physical-Sensor Source Adapter Contract

Date: 2026-09-16
Branch: `research/sourceboundaryprobe1a-multisensor`

## Purpose

Define the portable boundary between an arbitrary RAW-capable physical camera module and the single shared Leica M9 target renderer.

The unit of adaptation is the **physical RAW source**, not a zoom label, focal-length category, or marketing lens name.

`0.6x`, `1x`, `3x`, `4.1x`, `ultrawide`, `main`, `tele`, and similar labels are diagnostics/UI descriptions only. They MUST NOT select photographic behaviour.

## Pipeline boundary

```text
physical RAW buffer
  -> PhysicalRawDescriptor
  -> source normalization / SourceAdapter
  -> CommonSceneFrame
  -> one shared M9 target renderer
```

Everything before `CommonSceneFrame` may vary when justified by physical sensor/module evidence.
Everything after `CommonSceneFrame` MUST be identical for every supported source.

## PhysicalRawDescriptor

A source descriptor should carry, with provenance and confidence where applicable:

1. RAW width and height
2. row stride and pixel stride
3. active-array and pre-correction active-array geometry
4. RAW buffer origin / crop origin
5. CFA layout and resolved Bayer phase at the actual buffer origin
6. static and dynamic black level, including plane ordering
7. static and dynamic white level
8. LensShadingMap / GainMap geometry and values
9. Camera2/DNG calibration transforms
10. Camera2/DNG color matrices
11. Camera2/DNG forward matrices
12. reference illuminants
13. live/as-shot neutral
14. sensitivity / ISO metadata and analogue/digital gain evidence when available
15. sensor noise-model metadata when available
16. evidence of vendor scaling, nonlinear RAW, PDAF masking, remosaic/binning, baked preprocessing, or other source quirks
17. physical camera identity only as provenance, never as a photographic policy selector
18. focal length/aperture only as provenance or physically relevant optical metadata, never as a target-renderer selector

Unknown or unproven values must remain explicitly unknown rather than silently inheriting the main camera's assumptions.

## SourceAdapter responsibilities

A SourceAdapter may perform only operations required to make physically different sources mean the same thing at the common-scene handoff, including:

- CFA/phase-correct demosaic input interpretation
- black/white normalization
- source shading normalization when justified by the RAW contract
- source colour calibration using the active physical sensor's metadata
- live neutral handling in the proven Camera2/DNG domain
- geometry/origin/stride handling
- sensor signal/noise-domain normalization when measured evidence proves it is necessary
- correction for proven vendor RAW preprocessing or scaling

A SourceAdapter MUST NOT contain:

- a Leica/M9 look selected by physical camera
- per-lens M9 HSMs
- per-lens M9 tone curves
- per-lens SAT3 changes
- per-lens curve02 changes
- per-lens BT.601 changes
- per-lens TG1 changes
- aesthetic tuning keyed to camera ID, focal length, zoom label, or lens name

## CommonSceneFrame contract

The common-scene boundary must eventually define and verify at least:

- colour space / white point / matrix convention
- linearity
- numeric range and clipping policy
- neutral-axis semantics
- exposure/signal scale semantics
- black-floor semantics
- treatment of negative matrix results
- expected noise/signal semantics, if a common noise domain is required
- geometry handed to the target renderer

The boundary should be testable independently of the M9 target stages.

## Selection policy

Source adaptation is selected or parameterized from physical RAW characteristics and measured sensor behaviour.

Camera ID may locate the active Camera2 characteristics object, but a literal camera ID must not become the reason for a colour/tone/noise look. Focal length and zoom label must not select source-normalization behaviour except where a physical optical parameter is directly part of the measured source correction (for example the active module's own shading data).

Two modules with similar focal lengths may require different source normalization. Two differently labelled modules may share the same normalization if their physical RAW contracts are equivalent.

## Current Xiaomi 15 Ultra validation matrix

The current device should be treated as a four-source portability test, not a main-vs-3x test:

- physical camera 2 / main: 4096x3072, RGGB
- physical camera 3 / ultrawide: 4096x3072, GRBG
- physical camera 4 / tele: 4096x3072, RGGB; currently exposes green/magenta contamination
- physical camera 5 / long tele: primary 4080x3072, RGGB; geometry portability still needs validation

Camera 4 is the first clearly failing source, not the definition of the solution.
Camera 5 is an important guard against hidden 4096-wide assumptions.
Camera 3 remains an important guard against hidden RGGB assumptions.

## SOURCEBOUNDARYPROBE1A rule

The probe must compare stages for any supported physical source using active input geometry and that source's own calibration/neutral data.

The diagnostic decision is generic:

> For any pair of physical sensors, the first stage showing a material between-sensor divergence in neutral/chroma/noise metrics is the first suspect boundary.

No corrective pixel change should be introduced until the first divergence is identified.

## Future source-noise abstraction

If the probe demonstrates that nominal ISO or source noise statistics are not comparable at the common-scene boundary, add a sensor signal/noise descriptor rather than a telephoto-specific denoiser.

Candidate inputs include Camera2 noise profile, sensitivity/analogue gain metadata, black-floor variance, channel covariance, clipping headroom, and empirically measured flat/dark-frame statistics. The objective is semantic equivalence at the source boundary, not cosmetic denoising.

## Non-negotiable invariant

**Physical-sensor-specific before common scene space. M9-specific after common scene space.**

A new sensor or device should be supportable by satisfying the source contract without changing the Leica target renderer.