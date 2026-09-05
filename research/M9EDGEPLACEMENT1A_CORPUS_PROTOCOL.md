# M9EDGEPLACEMENT1A corpus protocol

Research-only. No capture, renderer, TC20, colour, curve, SAT3, H25/TG1, JPEG quality, or DNG behaviour changes.

## Objective

Detect only the rare cases where the frozen M9 JPEG has clearly failed photographic placement:

- `BRIGHT_FAIL`: too open; ambience/density lost.
- `DARK_FAIL`: too dense; useful subject/body remains starved.
- `GOOD`: frozen renderer is already photographically correct and must remain untouched.

The optimization target is specificity on `GOOD`, not activation rate or maximal tail recall. Ambiguous frames remain Frozen.

## Two-axis visual labelling

Do not collapse photographic placement and Leica-M9 character into one class.

Every visually reviewed frame may carry two independent labels:

### Axis A — placement

- `GOOD`
- `BRIGHT_FAIL`
- `DARK_FAIL`
- blank while unreviewed / ambiguous

Axis A is the only label used by the EDGEPLACEMENT exception-gate search.

### Axis B — M9ness

- `M9_STRONG`: current frozen JPEG already has convincing M9 character.
- `M9_IMPROVABLE`: placement can be acceptable, but tone/colour/density relationships could feel more M9-like.
- blank while unreviewed / when placement failure prevents a clean aesthetic judgement.

`M9_IMPROVABLE` is **not** an exception-placement class. A `GOOD + M9_IMPROVABLE` frame must remain a GOOD control for the placement selector. M9ness is an offline treatment-evaluation tag for later BESTFIT/render research, not authority to activate bright/dark correction.

This separation prevents a selector from learning that every merely less-M9-looking photograph is an exposure-placement failure.

## September 4 broad corpus

The accepted v0.7ZZS field corpus provides 121 JPEGs and 120 complete exact capture/RAW sets across:

- `photos.zip`
- `again part 1.zip`
- `again again part 2.zip`
- `again again part 3.zip`
- `again again 4.zip`

Use this as the dominant GOOD/control pool and dark-tail review pool. Preserve ordinary flowers, paths, street scenes, skies, intentional low-key/silhouette frames, ordinary indoor and ordinary daylight scenes as important negative controls when visually accepted.

Prior visual review identified several especially dense backlit candidates in this corpus (ordinals #4, #40, #73, #80 and #98). These are review candidates, not automatic labels, until exact capture identities are mapped and the frozen JPEG outcome is confirmed. Shaded-park frames #86–87 should also be retained as boundary/ambiguous examples rather than forced into a tail.

Preview-saturated stress frames #9, #41, #43, #120 and #121 are safety controls. Do not infer placement class from saturation alone.

## Confirmed BRIGHT_FAIL seed

The v2.81 handoff establishes six evening bright-tail examples. They are recorded in `m9edgeplacement1a_labels_seed.csv`.

Important diversity inside the class must be preserved: `190401` is highlight-guard limited while the other five are primarily median-limited. Therefore a useful selector cannot simply equate BRIGHT_FAIL with one TC20 binding branch.

## DARK_FAIL seed policy

Earlier capture/exposure work supplies useful starvation candidates (`191151`, `061349`, `181712`, `182155`, `183220`, `183146`), but they must not automatically be labelled `DARK_FAIL` here. EDGEPLACEMENT labels the *frozen JPEG outcome*, not merely a capture-side desire for more exposure. Promote each candidate to `DARK_FAIL` only after confirming the frozen JPEG itself is photographically too dense.

The September 4 `08:02:47` frame is a high-priority visual-confirmation candidate because existing finished-render telemetry reports approximately global median 17, centre median 11, >80% global occupancy at or below Y64, `wholeFrameStarvationEvidence=1`, `renderLiftNeedEvidence=1`, and `renderHoldEvidence=0`. These diagnostics justify review priority, not an automatic photographic label.

## GOOD corpus policy

`GOOD` must be substantially larger than either tail. Reuse ordinary frozen-M9 controls, including the broader control sweeps that rejected scene-key gating and the September 4 120-frame field corpus. Do not infer GOOD merely because a frame was not selected by an older experiment; label it from visual acceptance of the frozen JPEG.

Within GOOD, deliberately retain both `M9_STRONG` and `M9_IMPROVABLE` examples so the placement gate is forced to ignore aesthetic variation that is not a true bright/dark failure.

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
5. no renderer mutation in EDGEPLACEMENT1A;
6. no systematic activation merely because a GOOD frame is tagged `M9_IMPROVABLE`.

Only after a gate survives broad GOOD regression should bounded BESTFIT treatment be attached to BRIGHT_FAIL and an independently developed recovery treatment to DARK_FAIL.

M9ness refinement should then be evaluated separately, using `M9_STRONG` controls to prevent erosion of the already-successful frozen look.
