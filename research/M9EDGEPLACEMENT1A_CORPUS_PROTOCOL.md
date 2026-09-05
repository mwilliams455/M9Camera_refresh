# M9EDGEPLACEMENT1A corpus protocol

Research-only. No capture, renderer, TC20, colour, curve, SAT3, H25/TG1, JPEG quality, or DNG behaviour changes.

## Objective

Detect only the rare cases where the frozen M9 JPEG has clearly failed photographic placement:

- `BRIGHT_FAIL`: too open; ambience/density lost.
- `DARK_FAIL`: too dense; useful subject/body remains starved.
- `GOOD`: frozen renderer is already photographically correct and must remain untouched.

The optimization target is specificity on `GOOD`, not activation rate or maximal tail recall. Ambiguous frames remain Frozen.

## Confirmed BRIGHT_FAIL seed

The v2.81 handoff establishes six bright-tail examples. They are recorded in `m9edgeplacement1a_labels_seed.csv`.

Important diversity inside the class must be preserved: `190401` is highlight-guard limited while the other five are primarily median-limited. Therefore a useful selector cannot simply equate BRIGHT_FAIL with one TC20 binding branch.

## DARK_FAIL seed policy

Earlier capture/exposure work supplies useful starvation candidates (`191151`, `061349`, `181712`, `182155`, `183220`, `183146`), but they must not automatically be labelled `DARK_FAIL` here. EDGEPLACEMENT labels the *frozen JPEG outcome*, not merely a capture-side desire for more exposure. Promote each candidate to `DARK_FAIL` only after confirming the frozen JPEG itself is photographically too dense.

## GOOD corpus policy

`GOOD` must be substantially larger than either tail. Reuse ordinary frozen-M9 controls, including the broader control sweeps that rejected scene-key gating. Do not infer GOOD merely because a frame was not selected by an older experiment; label it from visual acceptance of the frozen JPEG.

## Candidate evidence

Prefer already-existing diagnostics:

- TC20 weighted median/base gain, tail guard, branch and branch margin;
- RAW tail/q99.x/hard clipping;
- physical Camera2 ISO, shutter and capture energy;
- achieved MFM intent;
- structuralLowKeyScore and related low-key evidence;
- global/centre dark and bright fractions;
- existing spatial/4x6 geometry and centre/global separation;
- existing render-meter observations for offline evaluation.

Do not use high ISO alone. Do not revive the rejected capture-normalized scene-key threshold as authority.

## Pass criterion

A promising exception gate should first demonstrate:

1. zero or extremely low false activation on GOOD;
2. support across more than one failure scene;
3. interpretable photographic/physical meaning;
4. Frozen fallback whenever confidence is not high;
5. no renderer mutation in EDGEPLACEMENT1A.

Only after a gate survives broad GOOD regression should bounded BESTFIT treatment be attached to BRIGHT_FAIL and an independently developed recovery treatment to DARK_FAIL.
