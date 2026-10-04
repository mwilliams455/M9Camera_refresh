# M9EDGEPLACEMENT1A — feature coverage / portability note

Research-only. No live selector and no renderer mutation.

## Why this note exists

The EDGEPLACEMENT control corpus now deliberately includes older visually accepted
GOOD/BOUNDARY captures as hard negatives. That improves photographic diversity,
but the diagnostic stack changed between field generations even though the
frozen renderer itself remained stable.

A candidate rule must therefore not earn apparent specificity because a feature
simply did not exist in an older control build.

## Exact compared anchors

### September 2 GOOD — `IMG_20260902_172954_1788366594738_00`

Build:
- `1.37-...-sceneexposure1d`
- instrumentation `LUMA2.4-SPATIAL2-FB1`
- scene schema `m9cam.sceneexposure.v4.signedpressure1d`
- frozen renderer schema `m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1`

Available shared primitives include:
- physical capture ISO / shutter / energy
- preview global median/q95/q99 and dark/bright fractions
- centre median and centre/global relationship
- orientation-aware 3x3 preview geometry
- TC20 gain / baseMedianGain / guard gain
- RAW q99/q99.5/q99.8 and hard clipping
- renderer RGB-channel clip fraction
- render near-white fraction

The PRIMARY sidecar does **not** expose the later render-meter / direct-rendered-luma evidence block.

### September 2 BOUNDARY — `IMG_20260902_173219_1788366739251_00`

Same `1.37` / sceneexposure-v4 generation and same frozen renderer family.

Important photographic negative-control facts:
- preview global median ~52
- preview q95 ~151
- preview q99 ~249
- preview dark fraction <=64 ~0.677
- centre median ~53
- visually very dark/coherent woodland, but not a clear placement failure

This is direct evidence that simple preview darkness / dark occupancy must not be
treated as DARK_FAIL.

### September 2 intentional silhouette GOOD — `IMG_20260902_174532_1788367532530_00`

Same `1.37` generation. Preview can be photographically unusual by design; the
scene was accepted as intentional darkness / neutral placement. This is a hard
negative against global shadow-lift logic.

### September 4 diagnostic dark anchor — `IMG_20260904_080247_1788505367414_00`

Build:
- `1.52-...-sceneexposure1h-...-rendermeter1c-...`
- instrumentation `LUMA2.4-SPATIAL2-FB1`
- scene schema `m9cam.sceneexposure.v8.renderaware1h`
- frozen renderer schema still `m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1`
- render-meter schema `m9cam.rendermeter.v3.evidence1c`

The newer build adds direct finished-render evidence, including:
- direct rendered global/centre/middle-centre luma statistics
- `wholeFrameStarvationEvidence`
- `localizedUpperPlacementEvidence`
- `globalBrightSupportEvidence`
- `renderLiftNeedEvidence`
- `renderHoldEvidence`

For this capture, preview global median is ~98, yet finished global median is ~17
and centre median ~11. This is the strongest current indication that DARK_FAIL is
about **useful-body collapse through the capture/render chain**, not merely a dark
preview.

## Feature-family status

### A. Portable-primitives candidate family

These are currently the best candidates for broad cross-build regression because
they are present in the older controls and newer generation:

1. capture:
   - `captureIso`
   - `captureShutterNs`
   - `captureEnergyIsoSeconds`

2. preview / scene geometry:
   - global median/q95/q99
   - global dark / bright occupancy
   - centre median
   - centre minus global
   - 3x3 spatial geometry / spatial separation where extracted consistently

3. TC20 / RAW:
   - `tc20Gain`
   - `baseMedianGain`
   - `tc20GuardGain`
   - `guardMarginAboveBaseEv` when derivable
   - RAW q99 / hard clipping

4. stable legacy renderer observations:
   - RGB-channel clip fraction
   - near-white fraction

Portable coverage does **not** mean these features are sufficient or valid as a
selector. It means they can be tested against a broader historical control set
without immediate schema-age bias.

### B. Same-cohort render-aware family

These are high-value truth/evidence signals but currently cohort-sensitive:

- rendered global/centre/middle-centre luma
- `renderLiftNeedEvidence`
- `renderHoldEvidence`
- `wholeFrameStarvationEvidence`
- `localizedUpperPlacementEvidence`
- `globalBrightSupportEvidence`

Until feature coverage proves otherwise, they should be interpreted only against
controls from a compatible build/schema cohort.

They may serve two different research roles:

1. **offline truth characterization** — describe what a failed finished render
   actually looks like;
2. **possible post-render exception gate** — only if same-cohort GOOD/BOUNDARY
   regression later proves such a gate is exceptionally specific.

Neither role authorizes live correction now.

## Key photographic comparison

The current dark evidence argues strongly against a preview-darkness threshold:

```text
173219 BOUNDARY:
preview global median ~52
preview dark<=64     ~67.7%
visually dense but not clear DARK_FAIL

080247 diagnostic dark candidate:
preview global median ~98
finished global median ~17
finished centre median ~11
finished dark<=64    ~80.9%
```

So a frame can look **much darker in preview statistics** yet remain a legitimate
boundary, while another frame with a substantially brighter preview can collapse
in the frozen finished render.

That moves the DARK research target toward:

> predict or detect collapse of useful rendered body relative to incoming scene
> structure, while protecting intentionally dark / dense M9 photography.

## Tooling added

`m9edgeplacement1a_feature_inventory.py` now produces:

- `feature_coverage_by_label.csv`
- `feature_coverage_by_cohort.csv`
- `feature_portability_status.csv`
- `feature_inventory_summary.json`

Statuses are coverage-only:
- `PORTABLE_CANDIDATE`
- `COHORT_SPECIFIC`
- `SINGLE_COHORT_ONLY`
- `PARTIAL_COVERAGE`

No status is photographic approval.

## Current interpretation rule

A candidate EDGEPLACEMENT rule must survive all of:

1. global corpus readiness;
2. GOOD + BOUNDARY false-activation ranking;
3. per-feature coverage audit;
4. compatible build/schema cohort readiness;
5. Frozen regression;
6. blinded visual validation.

The feature inventory is an additional diagnostic aid, not a replacement for any
of those gates.
