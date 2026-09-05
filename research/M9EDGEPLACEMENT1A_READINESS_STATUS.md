# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot. No live selector is authorized from this state.

## Exact placement labels currently joined

### GOOD: 16

Historical/global controls remain joined, and Part-3 now contributes 10 confirmed same-build R3.8 controls:

- `IMG_20260904_163553_1788536153169_00` (#35)
- `IMG_20260904_163847_1788536327166_00` (#39)
- `IMG_20260904_164247_1788536567395_00` (#45)
- `IMG_20260904_164331_1788536611192_00` (#46)
- `IMG_20260904_164402_1788536642539_00` (#47)
- `IMG_20260904_164510_1788536710636_00` (#51)
- `IMG_20260904_164525_1788536725121_00` (#52)
- `IMG_20260904_164707_1788536827532_00` (#56)
- `IMG_20260904_164736_1788536856690_00` (#57)
- `IMG_20260904_164814_1788536894347_00` (#59)

These deliberately include difficult hard negatives such as bright white swans on dark backgrounds and strong sun/shade transitions.

Additional existing GOOD controls:

- `IMG_20260904_101204` — `M9_STRONG`
- `IMG_20260902_172954_1788366594738_00`
- `IMG_20260902_174532_1788367532530_00`
- `191403`
- `194427`
- `202704`

### BOUNDARY: 5

New same-build Part-3 boundaries:

- `IMG_20260904_163702_1788536222457_00` (#38) — very dark coherent woodland/backlit path
- `IMG_20260904_164622_1788536782716_00` (#54) — backlit pond/silhouette relationship

Existing historical boundaries:

- `IMG_20260902_173219_1788366739251_00`
- `182419`
- `182739`

Other dense Part-3 frames such as #44/#55/#58 remain unlabelled review material rather than being forced into BOUNDARY.

### BRIGHT_FAIL: 6

- `184927`
- `184937`
- `190346`
- `190401`
- `190429`
- `194307`

### DARK_FAIL: 3

- `IMG_20260903_094446_1788425086751_00`
- `IMG_20260903_095258_1788425578865_00`
- `IMG_20260904_164019_1788536419887_00` — recovered global #40 backlit statue

Additional unpromoted DARK candidate:

- `IMG_20260904_164048_1788536448208_00` (#42)

## September-4 Part-3 recovery

`again again part 3.zip` is now byte-accessible.

Observed archive:

- 116 members
- 30 chronological capture stems
- 29 DNGs
- 87 JSONs
- no JPEG members

The original visual offset was recovered from the preserved q95==255 stress pair:

- local #11 = `IMG_20260904_164035_1788536435593_00`, q95==255 with positive achieved intent -> global #41
- local #13 = `IMG_20260904_164104_1788536464382_00`, q95==255 with neutral intent -> global #43

Therefore:

`global visual ordinal = Part-3 local ordinal + 30`

This establishes local #10 as global #40.

All sidecar-backed Part-3 captures share the same 1.61 / sceneexposure-v8 / frozen R3.8-H25-TG1 generation, making them valid compatible-cohort controls for #40.

## Global readiness guard

`m9edgeplacement1a_readiness.py` defaults:

- minimum GOOD: 30
- minimum BOUNDARY: 2
- minimum target-tail examples: 2

Current confirmed counts:

- GOOD: **16 / 30**
- BOUNDARY: **5 / 2** — cleared
- BRIGHT_FAIL: **6 / 2** — cleared
- DARK_FAIL: **3 / 2** — cleared

Therefore global rule interpretation remains **NOT READY** because GOOD is still short by **14** controls.

This is now the only global-count blocker.

## Compatible-cohort readiness

Default compatible-cohort minima:

- GOOD: 10
- BOUNDARY: 2
- target: 2

For the exact 1.61/v8/R3.8 Part-3 generation containing #40:

- compatible GOOD: **10 / 10** — cleared
- compatible BOUNDARY: **2 / 2** — cleared
- compatible confirmed DARK_FAIL: **1 / 2** — not cleared

So same-build control specificity is now testable, but same-build DARK recall is not yet testable because #40 is the only confirmed positive in this generation.

#42 is intentionally not used to satisfy readiness until its photographic label is independently fixed.

## RENDERMETER1C disposition

Part-3 decisively rejects the old RENDERMETER1C evidence model as standalone DARK authority.

Across the 29 sidecar-backed Part-3 frames:

- `renderLiftNeedEvidence >= 0.95`: 24 / 29
- `wholeFrameStarvationEvidence >= 0.95`: 24 / 29
- `renderLiftNeedEvidence >= 0.50`: 25 / 29
- only 4 / 29 have `renderHoldEvidence > 0.10`

Ordinary-looking paths, trees and animal scenes can therefore receive the same nominal starvation/lift signature as #40.

Do not promote `renderLiftNeedEvidence` or `wholeFrameStarvationEvidence` as live authority.

## RENDERGRID1A

`research/m9edgeplacement1a_rendergrid.py` is now in CI and produces diagnostic-only finished-render spatial evidence using:

- exact firmware BT.601 Q14 Y
- exact recovered M10-R 16x22 Integral mask at `0x4001349c`, sum 14160
- the same 4x6 / 24-region integer partition as M10RMFMTEST1A

It generates no correction EV and no live selector decision.

CI dependency handling is explicit (`numpy` + `Pillow`), and the full RENDERGRID self-test is passing.

## INTENTCOLLAPSE1A directional result

Part-3 measured observations are preserved in:

`research/m9edgeplacement1a_part3_intentcollapse_observations.csv`

The current descriptive conjunction is:

- achieved intent >= approximately +0.10 EV
- upper/lower render-vs-preview separation shift >= approximately +1.5 EV
- broad render cell body very low (`P75` median approximately <=30)
- Integral relative shift approximately <=+0.15 EV

On the fixed Part-3 control set it activates:

- #40 — confirmed DARK_FAIL
- #42 — unconfirmed DARK candidate

and activates:

- confirmed GOOD: **0 / 10**
- confirmed BOUNDARY: **0 / 2**

This is useful falsification progress but **not validation**. The thresholds were observed in the same small cohort and remain vulnerable to overfitting.

Particularly important hard negatives that remain protected include:

- #47 — positive-intent white swan against dark surroundings
- #54 — positive-intent backlit pond boundary
- #41 — saturated-preview stress frame

## Simple DARK predictors remain rejected

No standalone authority from:

- preview darkness
- preview dark occupancy
- finished global darkness
- RAW q99
- TC20 guard binding
- guard-margin severity
- positive MFM / capture intent
- RENDERMETER1C starvation/lift score
- upper/lower spatial shift alone

The target remains specifically **wrong useful-body collapse**, while preserving coherent dense M9 photography.

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

1. Add at least **14 more confirmed GOOD** controls globally.
2. Recover another exact DARK_FAIL from the 1.61/v8/R3.8 generation, preferably one of retained #4/#73/#80/#98 if its archive matches the same build.
3. Keep #42 as an independent falsification candidate; do not use it to tune and validate the same rule simultaneously.
4. Repeat RENDERGRID1A on every newly recovered archive before changing the live renderer.
5. Use #9/#41/#43/#120/#121 as stress/ordinal anchors, not placement labels.
6. Keep BRIGHT_FAIL and DARK_FAIL treatments asymmetric unless evidence later supports a common treatment.
7. Keep M9ness independent from placement.

No live APK EDGEPLACEMENT correction is authorized from the current state.
