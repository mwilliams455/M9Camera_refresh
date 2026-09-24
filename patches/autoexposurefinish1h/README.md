# AUTOEXPOSUREFINISH1H — FIELDOWNERSHIP1A + FASTACQUIRE1A

Parent: **1.80 / AUTOEXPOSUREFINISH1G SOFTANCHOR1A**.

Phone validation of 1G found two separate usability issues:

1. Auto placement could occasionally return 0 EV in a very dark scene even
   though the rendered bracket showed substantial safe exposure headroom.
2. Large exposure deficits converged more slowly than necessary because every
   positive change was restricted to +0.25 EV per fresh rendered-meter sample.

The 2026-09-24 woodland capture exposed the first issue directly. Its neutral
rendered probe was extremely dark (approximately median 11, centre median 9,
centre Q25 5), but the older centre/surround backlight score interpreted scattered
bright canopy gaps as "backlight". At the same time the newer 4x6 body detector
correctly found no coherent backlit subject. The old centre score blocked the
whole-scene branch while the 4x6 branch declined backlight ownership, so neither
path applied exposure.

## FIELDOWNERSHIP1A

When a valid 4x6 rendered field map exists, it now owns the
backlight-vs-whole-scene classification:

- a qualified coherent 4x6 body owns backlight placement;
- if no qualified coherent body exists, a genuinely starved frame may fall
  through to whole-scene low-key placement;
- the older centre/surround backlight-confidence gate is retained only as the
  fallback for devices/samples without a valid field map.

This does **not** alter the low-key scene targets, body targets, headroom limits,
or M9-character ceiling. It only removes the classification dead zone.

## FASTACQUIRE1A

Positive placement keeps the existing +0.25 EV fine step, but may use a
**+0.50 EV** acquisition step while a large, high-confidence deficit remains.

Fast acquisition is allowed only when:

- the requested target is at least 0.50 EV above the held Auto value; and
- either:
  - whole-scene placement is unambiguously starved
    (very low global/centre/lower-quartile rendered values with a large dark
    fraction), or
  - backlight placement has a materially confident and severe coherent body.

Ordinary protected-open-anchor scenes remain capped at +0.25 EV total.
The severe soft-anchor branch may still reach its existing +0.50 EV ceiling.

Negative movement is unchanged: ordinary downward changes still require the
existing two fresh confirmations and release in 0.25-EV steps. Hard
highlight/headroom safety release remains immediate.

## Frozen photographic behavior

1H does not change:

- 1G protected-open-anchor thresholds or +0.25/+0.50 EV caps;
- 4x6 body-selection geometry;
- body-lock / target-lock temporal behavior;
- whole-scene or backlight brightness targets;
- highlight/headroom budgets;
- TC20 normalization;
- curve02, SAT2, tungsten, detail, source calibration or shading;
- JPEG/DNG/native renderer;
- WYSIWYG preview shader;
- shutter draw-lock or sidecar-spool behavior.

## New diagnostics

The Auto sidecar adds:

- `sceneOwnership`;
- `fieldMapOwnsClassification`;
- `qualifiedMultifieldBodyOwnsBacklight`;
- `fastAcquireEligible`;
- `positiveRiseStepEv`;
- `normalPositiveSlewEv`;
- `fastPositiveSlewEv`.

Version: **1.81-m9autoexposurefinish1h-fieldownership1a-fastacquire1a-tg1**.
