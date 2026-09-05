# M9EDGEPLACEMENT1A — comparison pass 1

Research-only. No live selector and no renderer mutation.

## Compared groups

### Confirmed BRIGHT_FAIL
Exact evening captures:
- 18:49:27
- 18:49:37
- 19:03:46
- 19:04:01
- 19:04:29
- 19:43:07

### Confirmed DARK_FAIL
September-4 v0.7ZZS visual-corpus ordinals:
- #4 fire engine / toy truck by bright window
- #40 backlit statue
- #73 sculpture / bright field
- #80 dark lane / bright background
- #98 backlit tree

### Boundary / dense-but-not-clearly-failed
- #86 shaded park / backlight
- #87 shaded park / backlight

### GOOD / M9ness controls
- `IMG_20260904_101204` = exact `GOOD + M9_STRONG` visual seed
- ordinary flowers / paths / street / sky / intentional low-key corpus = GOOD pool pending exact visual tagging

## 1. TC20 branch does not separate classes

Bright-tail branch distribution:
- five of six primarily median-limited
- 19:04:01 guard-limited

Dark-tail / boundary population:
- all 27 positive-MFM field captures were guard-limited
- all five confirmed DARK_FAIL ordinals are inside this positive-MFM population
- #86/#87 boundary frames are also inside the same positive-MFM / guard-limited population

Therefore:

```text
tc20Binding == median  != BRIGHT_FAIL
tc20Binding == guard   != DARK_FAIL
```

Branch remains useful context but cannot be authority.

## 2. Positive MFM magnitude does not separate DARK_FAIL from boundary

Prior visual review / exposure audit gave approximately:

| frame | visual class | achieved/representative assist |
|---|---|---:|
| #4 | DARK_FAIL | +0.259 EV |
| #40 | DARK_FAIL | +0.309 EV |
| #73 | DARK_FAIL | +0.242 EV |
| #80 | DARK_FAIL | +0.476 EV |
| #98 | DARK_FAIL | +0.322 EV |
| #86 | BOUNDARY | +0.532 EV |
| #87 | BOUNDARY | +0.473 EV |

The strongest assist in this subset is a boundary frame, not a confirmed failure.

Therefore neither `positive MFM` nor assist magnitude is a useful primary selector.

## 3. Representative DARK_FAIL mechanism: useful-body collapse

Exact diagnostic anchor:
`IMG_20260904_080247_1788505367414_00`

Preview / capture-side structure:
- preview global median ~98
- preview centre median ~57
- centre minus global ~-41
- spatial low-region median ~54
- strong spatial separation/backlight evidence
- physical ISO 64
- physical RAW q99 ~0.515
- physical hard clipping ~0.000098

Finished render:
- global median 17/255
- centre median 11/255
- middle-centre median 12/255
- centre q95 98/255
- middle-centre q95 81/255
- global dark fraction <=Y64 ~0.809
- `wholeFrameStarvationEvidence = 1`
- `localizedUpperPlacementEvidence = 0`
- `renderLiftNeedEvidence = 1`
- `renderHoldEvidence = 0`

This is qualitatively stronger than ordinary M9 density: useful body placement has collapsed, not merely shifted dark.

First DARK_FAIL hypothesis:

> Detect collapse of useful global/centre body while retaining Frozen for intentional or photographically healthy low-key scenes.

Rendered-luma features are appropriate offline truth labels and may also be a possible post-render gate, but should not be promoted until the five exact DARK_FAIL captures and broad GOOD controls are joined.

## 4. Representative BRIGHT_FAIL mechanism: fixed-key ambience loss

The matched 18:49:27 / 18:49:37 pair is the clearest evidence:
- second capture received ~+0.62 EV more physical capture energy
- TC20 reduced normalization by ~-0.72 EV
- rendered medians stayed ~93 / 92

Five of six bright failures were driven to essentially the same frozen TC20 median body key.

Yet their output is not globally extreme in the same way as DARK_FAIL. Example BESTFIT measurements:

| frame | Frozen global median | Frozen centre q95 |
|---|---:|---:|
| 18:49:27 | ~0.371 (~95/255) | ~0.851 (~217/255) |
| 18:49:37 | ~0.366 (~93/255) | ~0.869 (~222/255) |

A ~93–95 global median is not intrinsically a bright-image failure. The failure is that a low-key / ambience-bearing scene has been normalized too open relative to its scene structure.

First BRIGHT_FAIL hypothesis:

> Detect conflict between scene low-key/regional structure and a TC20-imposed mid-body key, not absolute JPEG brightness alone.

This explains why a simple global brightness threshold and the rejected sceneKey threshold both fail ordinary controls.

## 5. Bright and dark tails are asymmetric

Current best interpretation:

### DARK_FAIL
Mostly an **absolute useful-body adequacy** question:
- has global/centre/middle-centre body collapsed below usable photographic placement?
- is there little evidence that the darkness is intentional or locally adequate?

### BRIGHT_FAIL
Mostly a **relative scene-placement / ambience** question:
- is TC20 forcing a low-key scene toward a generic body key?
- are useful upper tones already well placed while lower-mid ambience is too open?

Therefore do not force one signed scalar rule to solve both tails.

## 6. Conservative selector implications

### DARK_FAIL probe family
Prioritize combinations of:
- whole-frame starvation
- centre / middle-centre adequacy
- global dark occupancy
- rendered centre q95
- intentional-dark / localized-adequacy evidence
- pre-render spatial low-region collapse proxies

A deliberately strict probe around the 08:02:47 shape may initially catch only severe failures. Missing subtle dark failures is preferable to lifting healthy M9 shadows.

### BRIGHT_FAIL probe family
Prioritize combinations of:
- TC20 median-target / branch-margin evidence
- structuralLowKeyScore / low-key body evidence
- 4x6 regional upper-body and q95 relationships
- rendered or predicted lower-mid key versus anchored upper tones

A first production-oriented gate does not need 6/6 recall. A 3/6 or 4/6 high-confidence rule with zero GOOD false activation is more consistent with the Frozen-default philosophy.

## 7. M9ness comparison is not yet ready for threshold fitting

`M9_STRONG` versus `M9_IMPROVABLE` remains a separate visual axis.

Evidence from BESTFIT1A already shows why:
- no one density treatment won every bright-tail scene
- Frozen won two of three decisive matched-density cases in TC20PLACEMENTSTAGE1A
- BESTFIT can lower lower-mid/global density while holding centre q95 nearly fixed, but preference remains scene-dependent

So M9ness should be used to evaluate treatment quality **after** placement class is known, not to activate EDGEPLACEMENT.

Current exact M9ness seed is only:
- `IMG_20260904_101204` = `GOOD + M9_STRONG`

Do not fit an M9ness classifier until more exact GOOD frames are visually tagged `M9_STRONG` and `M9_IMPROVABLE`.

## 8. Decision from comparison pass 1

Promising architecture remains:

```text
Frozen render
   |
   +-- severe useful-body collapse -> DARK_FAIL candidate
   |
   +-- low-key/scene-key conflict with anchored upper tones -> BRIGHT_FAIL candidate
   |
   +-- otherwise -> GOOD / Frozen
```

M9ness remains downstream:

```text
GOOD
  +-- M9_STRONG
  +-- M9_IMPROVABLE
```

No live correction should be added from this pass.

## 9. Next quantitative test

Once exact DARK_FAIL identities are recovered, run two separate zero-false-positive searches:

1. `DARK_FAIL vs GOOD+BOUNDARY`
   - start with render/body-collapse features
   - then identify pre-render proxies for any successful truth rule

2. `BRIGHT_FAIL vs GOOD`
   - start with low-key + TC20 fixed-key + regional-placement conjunctions
   - allow low recall initially

Primary ranking remains:
1. GOOD false positives
2. boundary false positives
3. tail recall
4. interpretability
