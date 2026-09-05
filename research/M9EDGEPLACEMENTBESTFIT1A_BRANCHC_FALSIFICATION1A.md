# M9EDGEPLACEMENTBESTFIT1A — BRANCHC FALSIFICATION1A

## Status
Research-only. No capture mutation. No renderer mutation. No change to canonical BESTFIT1A thresholds.

## Question
Is `FOREGROUND_COLLAPSE` (Branch C) merely isolating `144210` through a fragile threshold combination, or is its morphology genuinely unusual relative to the existing Part-3 corpus?

## Canonical provisional Branch C
All conditions must hold:

- finished upper/lower shift >= +1.20 EV
- finished lower-12 mean <= 18 Y
- finished upper-6 mean >= 140 Y
- finished 16x22 cell-median P75 >= 120 Y
- matched center retention >= -1.00 EV

`144210` exact diagnostic values remain:

- upper/lower shift: +1.444 EV
- lower-12: 13.75 Y
- upper-6: ~167.2 Y
- cell-median P75: 161.75 Y
- center retention: -0.295 EV

## Part-3 broad screen
The existing validated R3.8-Y proxy was used to screen 28 Part-3 DNG frames. This proxy had previously shown P75 error of only 0.25–1.75 Y on exact historical anchors and is used here only for falsification screening.

Result:

- Branch-C activations: **0 / 28**
- This includes multiple dark-foreground / bright-background compositions.

Closest proxy misses included `164035`, `164647`, `164557`, and `164622`.

## One-at-a-time threshold sensitivity
Each Branch-C threshold was varied independently over a broad neighborhood while holding the others canonical.

Tested ranges included:

- upper/lower shift minimum: 0.8 to 1.5 EV
- lower-12 maximum: 12 to 35 Y
- upper-6 minimum: 80 to 170 Y
- cell-median P75 minimum: 60 to 160 Y
- center-retention minimum: -1.8 to -0.4 EV

Result:

- no Part-3 proxy frame became Branch C under any one-at-a-time perturbation
- `144210` remains ON over a broad useful neighborhood and turns OFF only when the corresponding threshold crosses its actual value
- exact good controls `143432` and `143532` remain OFF in these one-at-a-time sweeps

## Leave-one-condition-out ablation
Each of the five Branch-C conditions was removed entirely, one at a time.

Result:

- no Part-3 proxy frame activated
- `144210` remained active

This shows that no single condition is solely responsible for excluding the existing Part-3 negatives.

## Full-12 MP verification of the four closest proxy misses
To remove proxy-geometry uncertainty, the four closest misses were rerendered at full 4096x3072 source geometry using the frozen R3.8-H25/SAT3/curve02 path with TC20 reconstructed on the 1600-side meter.

| Frame | U/L shift | lower-12 Y | upper-6 Y | P75 Y | center retention | Canonical C |
|---|---:|---:|---:|---:|---:|---|
| 164035 | +1.692 | 14.41 | 98.54 | 55.0 | -1.206 | OFF |
| 164647 | +1.566 | 8.34 | 90.24 | 42.63 | -1.087 | OFF |
| 164557 | +1.619 | 26.90 | 136.19 | 73.5 | -1.640 | OFF |
| 164622 | +1.114 | 29.95 | 139.55 | 84.0 | -1.177 | OFF |

Important observations:

- `164622` nearly touches the 140-Y upper threshold, but fails the other four Branch-C conditions.
- `164035` and `164647` satisfy the dark-lower + large-shift shape, but the upper field and global P75 do not survive strongly enough and center retention is too weak.
- `164557` has a fairly bright upper field but is not a lower-field-only failure; its lower field and center are both too collapsed.

## Interpretation
Within the current corpus, Branch C does **not** look like a one-threshold or one-scene overfit. `144210` occupies a morphology that is separated from the available hard negatives by several independent dimensions.

This is stronger evidence for keeping Branch C as a distinct selector morphology.

It is **not** sufficient evidence for production promotion because Branch C still has only one strong positive treatment anchor. The correct next evidence remains prospective: another naturally occurring foreground-placement failure (or a hard negative that falls much closer to the conjunction).

## Frozen constraints
Do not:

- change TC20
- change capture AE
- change curve02
- change SAT3/HSM
- globally lift shadows
- weaken normal HOLD rendering
- wire Branch C or treatment into the live renderer yet
