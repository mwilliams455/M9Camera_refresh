# SCENEEXPOSURE1B draft — M9 quality-preserving diagnostic calibration

SCENEEXPOSURE1B is deliberately **diagnostic-only**. It must not change the actual photograph.

## Frozen photographic contract

The following remain untouched by this draft:

- live Photon exposure arithmetic;
- live FB1 behavior;
- M9 motion shutter/ISO allocation;
- R3.8 / H25 / TG1;
- TC20;
- Cobalt main-camera calibration;
- SAT3 M06/M07;
- curve02;
- exact BT.601 horizontal 4:2:2;
- 12 MP output;
- JPEG quality 95;
- PERF3I / CVDIRECT1A / BITMAPDIRECT1A / ORIENTFUSE8A rendering path.

`apply-m9cam-sceneexposure1b.py` hashes the live exposure selector, metadata writer, and M9 renderer before and after applying 1B and fails if any of them changes.

The build is therefore suitable only for comparing recommendations. It is **not** approval to make the new recommendation live.

## Why 1B exists

Four device controls exposed a narrow calibration problem in SCENEEXPOSURE1A:

| Control | 1A signed recommendation | 1B draft target |
| --- | ---: | ---: |
| ordinary indoor | ~0.00 EV | ~+0.35 EV |
| severe window backlight | ~+1.19 EV | preserve ~+1.19 EV |
| hydrangea, healthy center + dark periphery | ~+0.67 EV | reduce to ~+0.30 EV |
| moving bus, dark interior + bright exterior | ~+1.24 EV | preserve ~+1.24 EV |

The renderer is not being used to compensate for these exposure decisions. The purpose is to improve scene-brightness intent while retaining M9-style contrast and shadow density.

## 1B changes

### 1. Ordinary-body shoulder

`BODY_MEDIAN_ZERO_NEED_Y` moves from 112 to 138.

This lets an ordinary indoor body around preview median Y~115 generate a modest positive recommendation instead of falling into the neutral deadband.

It does **not** raise the maximum positive EV and does not alter severe-backlight logic.

### 2. Healthy-center protection

A new protection term is derived from:

- center median;
- center-minus-global median;
- current backlight pressure.

When the center is already healthy and the positive spatial/backlight pressure is only moderate, the recommendation is attenuated. This is aimed at the hydrangea failure mode where dark peripheral foliage was treated like an underexposed subject.

### 3. Severe-backlight preservation

Healthy-center attenuation fades out between backlight pressure 0.72 and 0.90 and is fully disabled at/above 0.90.

This preserves the strong 1A response in genuine window/interior starvation and moving-bus backlight controls.

### 4. Negative path remains frozen

Negative/high-key pressure is unchanged from 1A until genuine negative controls are captured. A small clipped lamp/window/specular must still not by itself force negative EV.

## Draft regression predictions

Using the recorded preview-luma inputs from the four controls, the 1B positive path predicts approximately:

- ordinary indoor: **+0.350 EV**;
- severe window backlight: **+1.192 EV**;
- hydrangea: **+0.305 EV**;
- moving bus: **+1.235 EV**.

These are development targets, not live exposure instructions.

## Acceptance gate

Before any live promotion, device validation should include at minimum:

1. repeat ordinary indoor;
2. repeat severe window backlight;
3. repeat healthy-center outdoor subject;
4. moving subject / moving platform backlight;
5. balanced outdoor scene that should remain near 0 EV;
6. broad high-key/reflective scene capable of producing negative EV;
7. intentional silhouette/high-contrast scene;
8. small isolated bright source with otherwise normal body exposure.

For every frame compare:

- JPEG appearance and M9-style contrast;
- `m9SceneExposureDiagnostic`;
- `m9ExposureAudit`;
- RAW headroom where DNG is available;
- motion allocation independently from scene-brightness intent.

Do not promote 1B live merely because CI passes. Device evidence and preservation of the M9 photographic character are the acceptance gates.
