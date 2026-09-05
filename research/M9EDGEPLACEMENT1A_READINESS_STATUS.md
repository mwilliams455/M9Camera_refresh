# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot. No live selector is authorized from this state.

## Exact placement labels currently joined

### GOOD: 6

- `IMG_20260904_101204` — `M9_STRONG`; balanced exposure, held highlights, dense-but-separated shadows, restrained M9 rendering.
- `IMG_20260902_172954_1788366594738_00` — current JPEG explicitly judged already well placed; target approximately 0 to +0.15 EV.
- `IMG_20260902_174532_1788367532530_00` — intentional silhouette / gray-sky neutral PASS; true 0 EV capture; darkness is intentional.
- `191403` — globally dark surroundings with adequately placed subject; only a small modeled adjustment around +0.13 EV.
- `194427` — subject already looked adequately placed; only a small modeled adjustment around +0.115 EV.
- `202704` — high-AE healthy ordinary-object neutral control.

### BOUNDARY: 3

- `IMG_20260902_173219_1788366739251_00` — very dark coherent woodland; dense but not a clear placement failure.
- `182419` — ordinary indoor person; old positive pressure was a false positive and later moderated.
- `182739` — room with black dog; dark object correctly distinguished from global scene underexposure.

### BRIGHT_FAIL: 6

- `184927`
- `184937`
- `190346`
- `190401`
- `190429`
- `194307`

### DARK_FAIL: 3

- `IMG_20260903_094446_1788425086751_00` — dark woodland / protected openings; conservative RAW negative but JPEG useful body collapsed.
- `IMG_20260903_095258_1788425578865_00` — sky-protected foreground; JPEG foreground/body development failed despite plausible RAW negative.
- `IMG_20260904_164019_1788536419887_00` — recovered September-4 global #40, backlit statue; exact app render body collapses while bright background is retained.

Global DARK target count is therefore no longer the immediate blocker.

## September-4 Part-3 recovery

Archive bytes for `again again part 3.zip` became available.

Observed archive:

- 116 members
- 30 chronological capture stems
- 29 DNGs
- 87 JSONs
- no JPEG members

The original global visual ordinal offset was recovered independently using the preserved saturated-preview stress pair:

- Part-3 local #11 = `IMG_20260904_164035_1788536435593_00`, q95==255 and positive achieved capture intent -> global #41
- Part-3 local #13 = `IMG_20260904_164104_1788536464382_00`, q95==255 and neutral achieved intent -> global #43

Therefore:

`global visual ordinal = Part-3 local ordinal + 30`

This makes local #10 the retained global #40 backlit-statue DARK_FAIL.

Part-3 is a highly valuable compatible cohort because all sidecar-backed captures share the same 1.61 / sceneexposure-v8 / R3.8-H25-TG1 generation as #40.

## Same-build review pools from Part-3

These are **not yet placement labels**.

Priority GOOD-pool review:

- #32
- #35
- #39
- #45
- #46
- #47
- #51
- #52
- #56
- #57
- #59

Priority BOUNDARY review:

- #38
- #44
- #53
- #54
- #55
- #58

Additional DARK review candidate:

- `IMG_20260904_164048_1788536448208_00` (#42)

#42 remains unpromoted until direct visual judgement is recorded.

## Global readiness guard

`m9edgeplacement1a_readiness.py` defaults:

- minimum GOOD: 30
- minimum BOUNDARY: 2
- minimum target-tail examples: 2

Current confirmed counts:

- GOOD: **6 / 30**
- BOUNDARY: **3 / 2** — count threshold cleared
- BRIGHT_FAIL: **6 / 2** — target count cleared
- DARK_FAIL: **3 / 2** — target count cleared

Therefore both tail searches remain **NOT READY for interpretation** because GOOD is still too small.

The bottleneck has shifted from obtaining DARK positives to proving specificity against a much larger control set.

## Compatible-cohort readiness guard

`m9edgeplacement1a_cohort_metadata.py` and `m9edgeplacement1a_cohort_readiness.py` require failure examples to be challenged by compatible controls from the same build/schema generation wherever possible.

Default compatible-cohort minima:

- GOOD: 10
- BOUNDARY: 2
- target: 2

Part-3 supplies the right build generation and enough visually promising control candidates, but those candidates are deliberately **not counted as GOOD or BOUNDARY until visual labels are confirmed**.

So compatible-cohort readiness remains **NOT READY**.

Historical September-2 controls remain valuable global regressions but cannot substitute for 1.61/v8/R3.8 controls when validating #40-like failures.

## RENDERMETER1C disposition

Part-3 decisively rejects the old RENDERMETER1C evidence model as standalone DARK authority.

Across the 29 sidecar-backed Part-3 frames:

- `renderLiftNeedEvidence >= 0.95`: 24 / 29
- `wholeFrameStarvationEvidence >= 0.95`: 24 / 29
- `renderLiftNeedEvidence >= 0.50`: 25 / 29
- only 4 / 29 have `renderHoldEvidence > 0.10`

Ordinary-looking paths, trees and animal scenes can therefore receive the same nominal starvation/lift signature as confirmed #40.

Do not promote either:

- `renderLiftNeedEvidence == 1`
- `wholeFrameStarvationEvidence == 1`

as a selector.

The model remains useful as descriptive evidence only.

## Other simple DARK predictors still rejected

No standalone DARK authority from:

- preview darkness
- preview dark occupancy
- finished global darkness
- RAW q99
- TC20 guard binding
- TC20 guard-margin severity
- positive MFM / capture assist
- RENDERMETER1C starvation / lift scores

The target is specifically **wrong useful-body collapse**, while preserving coherent dense M9 photography and intentional low-key placement.

## RENDERGRID1A

New research extractor:

`m9edgeplacement1a_rendergrid.py`

It is diagnostic-only and produces no EV or live decision.

It applies to the finished frozen JPEG:

- exact firmware BT.601 Q14 Y
- the exact recovered M10-R 16x22 Integral mask at `0x4001349c`, sum 14160
- the same 4x6 / 24-region integer partition used by M10RMFMTEST1A

It then compares preview versus finished-render spatial relationships:

- Integral-weighted Y
- overall grid mean
- center8
- lower12
- upper6
- edge16
- inner8
- retention EVs
- relative spatial shifts
- direct 4x6 cell median/q95/dark-occupancy distributions

Part-3 exploratory evidence suggests #40 and #42 share a possible subtype involving positive exposure intent plus large upper/lower separation amplification while broad useful body remains extremely low.

This is only a hypothesis. No threshold is production authority.

## Current exploratory intent-collapse conjunction

Part-3-only research observation, not a rule:

- achieved intent >= about +0.10 EV
- upper/lower render-vs-preview separation shift >= about +1.5 EV
- broad render cell body remains very low
- recovered Integral-weighted field does not improve materially relative to overall mean

Within the currently inspected Part-3 segment this isolates:

- #40 confirmed DARK_FAIL
- #42 unconfirmed DARK candidate

while avoiding selected hard negatives such as #47 and boundary candidates #54/#55.

This must be tested on more archives and confirmed controls before even being treated as a candidate gate.

## Interpretation gate

A candidate EDGEPLACEMENT rule is not meaningful unless all of these pass:

1. global corpus readiness;
2. GOOD and BOUNDARY false-activation ranking;
3. per-feature coverage audit;
4. compatible build/schema cohort readiness;
5. Frozen regression;
6. blinded visual validation.

Frozen remains the mandatory fallback.

## Immediate next actions

1. Visually confirm enough Part-3 control candidates to create at least 10 same-build GOOD and 2 same-build BOUNDARY controls.
2. Run RENDERGRID1A on those confirmed controls plus #40 and any confirmed #42 disposition.
3. Search conservative single-feature / AND2 relationships only after labels are fixed.
4. Recover additional field archives when byte access becomes available, prioritizing exact mapping of #4, #73, #80, #86/#87 and #98.
5. Use #9/#41/#43/#120/#121 stress signatures as ordinal/safety anchors, not placement labels.
6. Keep BRIGHT_FAIL and DARK_FAIL correction treatments asymmetric if the evidence continues to support distinct mechanisms.
7. Keep M9ness separate from placement.

No live APK EDGEPLACEMENT correction is authorized from the current state.
