# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot.

## Exact-ID / exact-pattern labels currently joined

### GOOD: 6

- `IMG_20260904_101204` — `M9_STRONG`; balanced exposure, held highlights, dense-but-separated shadows, restrained M9 rendering.
- `IMG_20260902_172954_1788366594738_00` — current JPEG explicitly judged already well placed; photographic target approximately 0 to +0.15 EV.
- `IMG_20260902_174532_1788367532530_00` — intentional silhouette / gray-sky neutral PASS; true 0 EV capture; darkness is intentional.
- `191403` — globally dark surroundings with adequately placed subject; only a small modeled adjustment around +0.13 EV.
- `194427` — subject already looked adequately placed; later diagnostic modeled only a small adjustment around +0.115 EV.
- `202704` — high-AE healthy ordinary-object neutral control; diagnostic effectively neutral.

### BRIGHT_FAIL: 6

- 18:49:27
- 18:49:37
- 19:03:46
- 19:04:01
- 19:04:29
- 19:43:07

### BOUNDARY: 3

- `IMG_20260902_173219_1788366739251_00` — very dark coherent woodland; target approximately +0.3 to +0.5 EV and live FB1 about +0.263 EV; dense but not a clear placement failure.
- `182419` — ordinary indoor person; old positive pressure was a false positive and moderated to about +0.16 EV; retained as near-neutral boundary.
- `182739` — room with black dog; dark object correctly distinguished from scene underexposure, residual target about +0.19 EV; important dark-object boundary control.

### DARK_FAIL: 0 exact-ID joins

The five September-4 DARK_FAIL scenes remain visually confirmed, but their retained corpus ordinals have not yet been mapped back to exact capture stems.

## Visual labels known but not yet exact-ID joined

Confirmed visual `DARK_FAIL` by September-4 corpus ordinal:
- #4 — fire engine / toy truck by bright window
- #40 — backlit statue
- #73 — sculpture against bright field
- #80 — dark lane / bright background
- #98 — backlit tree

September-4 boundary / ambiguous ordinals still awaiting exact identity:
- #86
- #87

The missing DARK joins are an ordinal-to-filename mapping problem, not a visual-label uncertainty.

`IMG_20260904_080247_1788505367414_00` remains a strong diagnostic DARK candidate because its finished-render telemetry shows severe useful-body collapse, but it is **not** promoted to DARK_FAIL without direct visual confirmation.

## Global readiness guard

`m9edgeplacement1a_readiness.py` defaults:

- minimum `GOOD`: 30
- minimum `BOUNDARY`: 2
- minimum target-tail examples: 2

Current state:

- GOOD: **6 / 30**
- BOUNDARY: **3 / 2** — count threshold cleared
- BRIGHT_FAIL: **6 / 2** — target-count threshold cleared
- exact DARK_FAIL: **0 / 2**

Therefore:

- BRIGHT_FAIL rule interpretation: **NOT READY** — GOOD corpus still too small.
- DARK_FAIL rule interpretation: **NOT READY** — exact DARK_FAIL identities still absent and GOOD corpus too small.

Any conjunction/single-feature rankings generated before readiness is satisfied are exploratory only.

## Diagnostic-schema feature-coverage guard

Historical GOOD/BOUNDARY controls span older diagnostic builds than the September-4 BRIGHT_FAIL set. Missing diagnostics must never create artificial specificity.

`m9edgeplacement1a_rule_coverage.py` therefore audits every candidate rule after search.

Default per-feature minimum coverage before a candidate rule is eligible for interpretation:

- GOOD: 80%
- target tail: 80%
- BOUNDARY: 67%
- opposite tail: 50% when that exact cohort exists

An absent class is handled by readiness rather than pretending the feature has been validated there.

Missing values are never allowed to count as clean negatives.

## Build/schema cohort identity guard

Capture date alone is not sufficient protection against build drift. A control taken on the same day but produced by a different diagnostic build can still create false separation.

The research pipeline now includes:

- `m9edgeplacement1a_cohort_metadata.py`
- `m9edgeplacement1a_cohort_readiness.py`

`m9edgeplacement1a_cohort_metadata.py` reads existing JSON sidecars / diagnostic bundles and attaches **evaluation-only** identity fields:

- `m9Build.version`
- `m9Build.instrumentation`
- scene-exposure diagnostic schema
- render-meter diagnostic schema where available
- frozen renderer schema

These strings are never photographic classifier features.

Cohort-readiness priority is:

1. exact build + schema cohort key;
2. schema cohort key if build version is absent;
3. `IMG_YYYYMMDD` date only as a fallback for historical data with no cohort metadata.

Default compatible-cohort minimums:

- GOOD: 10
- BOUNDARY: 2
- target tail: 2

Every represented failure cohort must pass independently.

Important consequence:

> Historical September-2 GOOD controls improve diversity and global regression coverage, but they cannot by themselves validate a September-4 BRIGHT_FAIL/DARK_FAIL selector.

The current September-4 exact-pattern state is insufficient even under the older date fallback:

- known exact September-4 GOOD: **1** (`101204`)
- exact September-4 BOUNDARY: **0**
- exact September-4 BRIGHT_FAIL: **6**
- exact September-4 DARK_FAIL: **0**

The exact build/schema compatibility of `101204` versus the evening bright failures should be determined from their source JSONs rather than assumed from date.

## Interpretation gate

A candidate rule is not meaningful unless **all three** conditions pass:

1. global corpus readiness;
2. per-feature diagnostic coverage;
3. compatible build/schema cohort readiness.

Only then should zero-FP / tail-recall ranking be interpreted photographically.

## Current offline pipeline

```text
m9edgeplacement1a_replay.py
        |
        v
m9edgeplacement1a_conjunction_search.py
        |
        +--> candidate single / AND2 gates
        |
        v
m9edgeplacement1a_rule_coverage.py
        |
        v
m9edgeplacement1a_cohort_metadata.py
        |
        v
m9edgeplacement1a_readiness.py
        +
m9edgeplacement1a_cohort_readiness.py
        |
        v
human interpretation / Frozen regression / blinded visual validation
```

Cohort metadata is attached **after rule generation** so software/build identity can never accidentally become a photographic rule feature.

## Next data actions

1. Recover the five September-4 archive bytes and run `m9edgeplacement1a_archive_index.py` to map #4/#40/#73/#80/#98 and #86/#87 to exact `IMG_20260904_*` stems.
2. Use existing individual September-4 JSONs / diagnostic bundles wherever File Library exposes them to recover build/schema identity even before ZIP byte access is restored.
3. Expand exact visually accepted GOOD controls toward at least 30 globally, while also building **at least 10 compatible September-4/build-matched GOOD controls and 2 compatible boundaries** for the failure cohort.
4. Prioritize difficult negatives rather than redundant easy scenes:
   - ordinary daylight
   - flowers / foliage
   - paths / street scenes
   - ordinary indoor
   - intentional low-key / silhouette
   - dark-object scenes
   - high-AE but photographically healthy scenes
   - highlight-stress scenes where photographically acceptable
   - both `M9_STRONG` and `M9_IMPROVABLE` GOOD frames
5. When exact feature rows are available, run the complete guarded pipeline above.
6. Only interpret candidate rules when global readiness, feature coverage, and cohort readiness all pass.
7. Frozen regression and blinded visual validation remain mandatory before any live selector work.

No live APK correction is authorized from the current corpus state.
