# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot. No live selector is authorized from this state.

## Confirmed placement counts

### GOOD: 19

Ten Part-3 same-build R3.8 controls remain confirmed by direct visual review, but all previously assigned Part-3 global ordinal numbers are withdrawn. Their placement labels do not depend on the invalid ordinal mapping.

Three new prospective September-5 visual-first controls are now confirmed GOOD:

- `IMG_20260905_084106_1788594066806_00` — sunny path/tree; deep local shadow remains coherent
- `IMG_20260905_084129_1788594089422_00` — sunny path; strong luminance split remains photographically healthy
- `IMG_20260905_084146_1788594106149_00` — sunny path hard negative; healthy result despite approximately +0.176 EV actual capture intent

Additional historical/global GOOD controls remain joined, including `IMG_20260904_101204` (`M9_STRONG`).

### BOUNDARY: 6

Existing five boundaries remain. New prospective boundary:

- `IMG_20260905_084154_1788594114928_00` — direct-sun stress frame. Foreground is extremely dense but a silhouette/direct-sun interpretation remains photographically plausible; do not auto-promote to DARK_FAIL without explicit reviewer judgement.

### BRIGHT_FAIL: 6

Unchanged evening bright-tail set.

### DARK_FAIL: 3

- `IMG_20260903_094446_1788425086751_00`
- `IMG_20260903_095258_1788425578865_00`
- `IMG_20260904_164048_1788536448208_00` — likely retained visual #73, sculpture/statue against bright field/sky

`IMG_20260904_164019_1788536419887_00` remains an unconfirmed same-build DARK candidate. Its previous #40 assignment has been retracted.

## September-5 prospective field result

The new field sequence is valuable because it is labelled directly by exact filename rather than reconstructed viewer ordinal.

Visual-first labels were fixed before telemetry interpretation:

| capture | label | actual capture offset vs Photon | TC20 base gain | TC20 guard gain | finished global median | center median | q95 |
|---|---|---:|---:|---:|---:|---:|---:|
| 084106 | GOOD | 0 EV | 4.216x | 2.233x | 43 | 57 | 224 |
| 084129 | GOOD | 0 EV | 3.544x | 2.301x | 49 | 99 | 230 |
| 084146 | GOOD | +0.176 EV | 1.968x | 1.910x | 78 | 110 | 227 |
| 084154 | BOUNDARY | +0.433 EV | 4.040x | 1.300x | 23 | 39 | 195 |

All four frames are TC20 highlight-guard limited (`guardGain < baseMedianGain`). Therefore guard binding is again falsified as a placement class selector.

The set also strengthens two existing negatives:

1. **absolute finished darkness is insufficient** — 084106 is visually GOOD with global median 43 and >58% of sampled output at or below Y64;
2. **positive capture intent is insufficient** — 084146 is GOOD after +0.176 EV actual capture offset.

084154 is especially useful as a hard boundary. It has the largest body collapse in this four-frame set and approximately +0.433 EV actual capture offset, yet direct sun in frame makes automatic lifting unsafe. It should challenge any INTENTCOLLAPSE-like gate before production promotion.

No thresholds are tuned from this four-frame set.

## Part-3 ordinal correction

The earlier `+30` Part-3 global offset is withdrawn. Telemetry stress signatures were not unique ordinal identities. `164048` remains the strongest visual anchor as likely #73, but no complete ordinal reconstruction is required for the prospective test path.

## Global readiness guard

Defaults:

- minimum GOOD: 30
- minimum BOUNDARY: 2
- minimum target-tail examples: 2

Current counts:

- GOOD: **19 / 30**
- BOUNDARY: **6 / 2** — cleared
- BRIGHT_FAIL: **6 / 2** — cleared
- DARK_FAIL: **3 / 2** — cleared

Global interpretation remains **NOT READY** because GOOD is short by **11** controls.

## Compatible-cohort readiness

For the 1.61 / sceneexposure-v8 / frozen R3.8 Part-3 generation:

- compatible GOOD: **10 / 10** — cleared
- compatible BOUNDARY: **2 / 2** — cleared
- compatible confirmed DARK_FAIL: **1 / 2** — not cleared

The September-5 prospective frames are not silently folded into this historical Part-3 cohort count unless exact build/schema compatibility is explicitly established.

## RENDERMETER1C disposition unchanged

RENDERMETER1C remains descriptive evidence only, not standalone DARK authority.

## RENDERGRID1A / INTENTCOLLAPSE1A

The current Part-3 descriptive conjunction remains research-only. The new direct-sun boundary 084154 should be treated as a prospective hard negative when equivalent finished-render spatial features are available. Its combination of positive intent, low finished body and severe guard binding makes it exactly the kind of photograph a naïve DARK rule could wrongly lift.

## Immediate next actions

1. Continue prospective exact-filename testing rather than archive-order reconstruction.
2. Add at least **11 more confirmed GOOD** controls globally.
3. Seek several independently judged DARK_FAIL and BRIGHT_FAIL examples, while retaining intentional silhouettes/direct-sun frames as boundaries.
4. Judge JPEG placement first, then inspect telemetry.
5. Do not tune a rule from the same small set used to invent it.
6. Keep M9ness independent from placement.
7. Frozen remains mandatory fallback.

No live APK EDGEPLACEMENT correction is authorized from the current state.
