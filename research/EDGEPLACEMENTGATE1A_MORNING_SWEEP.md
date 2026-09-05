# EDGEPLACEMENTGATE1A morning prospective sweep — 2026-09-05

Research-only. No photographic pixel mutation.

## Uploaded cohort

Dropbox `/chatgpt/M9/exposure` contained 13 complete morning capture sets from `084712` through `090359`.

The previously named `084154`, `084325`, `084328`, `084333`, and `084525` sets were not present in this folder and are therefore not counted as tested here.

## Gate condition 1: achieved capture intent

Current provisional selector requires `captureEnergyVsPhotonOnlyEv >= +0.10 EV` before any finished-placement evidence can activate.

| capture | captureEnergyVsPhotonOnlyEv | result at intent gate |
|---|---:|---|
| 084712 | +0.000000 | OFF |
| 084858 | +0.000000 | **OFF** |
| 085011 | +0.000000 | OFF |
| 085126 | +0.000000 | OFF |
| 085303 | +0.000000 | OFF |
| 085321 | +0.084064 | OFF |
| 085339 | +0.163498 | continue |
| 085353 | +0.137503 | continue |
| 085742 | ~0.000000 | OFF |
| 085848 | -0.009848 | OFF |
| 085955 | +0.000000 | OFF |
| 090211 | -0.011588 | OFF |
| 090359 | -0.006603 | OFF |

This is an important prospective falsification success: `084858`, the strongest known visually-GOOD extreme-dark hard negative, is excluded before rendered darkness or TC20 meter demand can influence the selector.

## Remaining prospective cases

Only `085339` and `085353` cross +0.10 EV.

Existing `_M9_PRIMARY.json` coarse rendered summaries do not show an obvious statue-style useful-body disappearance:

- `085339`: global median 58, center median 70, center q95 236.
- `085353`: global median 46, center median 59, center q95 233.

Those coarse summaries are not sufficient to claim the full gate is OFF. Exact selector evaluation also requires the finished 16x22 Integral geometry / 4x6 direct cell medians used by `m9edgeplacement1a_rendergrid.py`.

Dropbox currently exposes the JPEG files but not a byte/pixel buffer usable by the analysis runtime, so no exact retrospective 4x6 calculation is claimed for these two files.

## Next step

Build `EDGEPLACEMENTGATE1A` as a pixel-neutral telemetry overlay on top of `m9metadatafix1a`:

- scan the already-finished oriented bitmap before unchanged JPEG95 encoding;
- exact firmware BT.601 Q14 Y: `(4899R + 9617G + 1868B) >> 14`;
- record finished 16x22 mean grid;
- apply recovered Integral mask, sum 14160;
- record 4x6 mean topology and direct 4x6 medians;
- record render Integral/mean, upper6/lower12, center8, edge16/inner8 and median P75;
- record timing overhead;
- do not change capture AE, TC20 gain, renderer gain, SAT3, curve02, BT.601/TG1, JPEG quality, or metadata behavior.

The app-side telemetry will then be combined with `_M9.json` preview grid and achieved intent offline. No live lift is authorized until prospective hard-negative activation remains zero.