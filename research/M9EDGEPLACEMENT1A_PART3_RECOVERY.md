# M9EDGEPLACEMENT1A — September-4 Part-3 recovery (corrected)

Research-only. No live selector and no photographic renderer mutation.

## Archive state

Mounted archive: `again again part 3.zip`

Observed shape:

- 116 ZIP members
- 30 chronological capture stems
- 29 DNGs
- 87 JSON files
- no JPEG members

Chronological capture range:

- first retained stem: `IMG_20260904_163347_1788536027742_00`
- last retained stem: `IMG_20260904_164845_1788536925171_00`

Because the archive contains no JPEG members, chronological capture position is
**not automatically the original 121-JPEG visual-review ordinal**.

## Correction to the earlier +30 offset inference

An earlier research pass attempted to anchor Part-3 using two local captures:

- `IMG_20260904_164035_1788536435593_00`: preview q95==255 with ~+0.070 EV achieved intent
- `IMG_20260904_164104_1788536464382_00`: preview q95==255 with zero achieved intent

Those signatures resembled retained global safety controls #41/#43, and the pass
incorrectly inferred:

`global ordinal = local chronological ordinal + 30`

That inference is now **retracted**.

The q95/MFM pattern was not a unique global identity key. It is useful as a
safety phenotype, not as an ordinal fingerprint.

Consequences:

- `IMG_20260904_164019_1788536419887_00` is no longer asserted to be #40.
- `IMG_20260904_164035_1788536435593_00` is no longer asserted to be #41.
- `IMG_20260904_164104_1788536464382_00` is no longer asserted to be #43.
- all previously written Part-3 global ordinal annotations on GOOD/BOUNDARY
  controls are withdrawn.

Their **photographic placement labels remain valid where they were visually fixed
from the rendered photograph**; only the global ordinal labels were contaminated.

## New visual anchor: likely #73

The original reviewer identified the uploaded
`IMG_20260904_164048_1788536448208_00.dng` as likely visual corpus #73.

A direct demosaic/render inspection shows a carved statue/sculpture against a
bright sky/field. This matches the retained visual description of #73:

> sculpture against bright field — substantially too dense

The exact capture also belongs to the same 1.61 / sceneexposure-v8 / frozen
R3.8-H25-TG1 generation as the rest of Part-3.

Current treatment:

- exact capture `IMG_20260904_164048_1788536448208_00` is accepted as a
  `DARK_FAIL` visual identity candidate with strong reviewer support;
- the specific global ordinal `#73` remains marked as a **likely visual anchor**
  until another independent scene/ordinal anchor confirms the archive ordering;
- no complete Part-3 global offset is inferred from this single anchor.

This is deliberately more conservative than assuming chronological local order
must equal the original viewer order.

## Reopened #40 identity

Retained global #40 remains:

- backlit statue
- confirmed visual `DARK_FAIL`
- exact capture identity pending

`IMG_20260904_164019_1788536419887_00` is still a very strong DARK candidate in
its own right:

- finished global median ~5
- center median ~5
- middle-center median ~4
- global dark fraction <=Y64 ~0.877
- RAW not broadly clipped
- large positive capture intent

But those diagnostics do not make it #40. It is therefore kept as
`REVIEW_DARK_CANDIDATE`, not a confirmed ordinal join.

## Same-build cohort remains valid

The ordinal correction does **not** invalidate the Part-3 build cohort.

All sidecar-backed Part-3 captures still share:

- build generation 1.61
- scene schema `m9cam.sceneexposure.v8.renderaware1h`
- frozen renderer schema
  `m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1`

Directly reviewed GOOD and BOUNDARY controls remain useful because those labels
were assigned from the photographs, not from their mistaken global ordinals.

## RENDERMETER1C disposition unchanged

The same-build cohort still falsifies RENDERMETER1C as standalone DARK authority.
Across 29 sidecar-backed Part-3 frames:

- `renderLiftNeedEvidence >= 0.95`: 24 / 29
- `wholeFrameStarvationEvidence >= 0.95`: 24 / 29
- `renderLiftNeedEvidence >= 0.50`: 25 / 29
- only 4 / 29 have `renderHoldEvidence > 0.10`

Ordinary healthy-looking photographs can therefore receive the same nominal
starvation/lift signature as true dark failures.

## RENDERGRID / INTENTCOLLAPSE interpretation after correction

The measured spatial result itself survives, but the positive/candidate roles
swap:

- `164048` — likely #73, now the confirmed/strongly anchored DARK example;
- `164019` — unconfirmed DARK candidate.

Both share the same unusual Part-3 spatial pattern:

- positive achieved capture intent;
- large render-vs-preview upper/lower separation increase;
- very low broad rendered cell body;
- little Integral-weighted improvement relative to overall rendered mean.

The conjunction still has zero activations on the fixed 10 GOOD and 2 BOUNDARY
controls, but it is **not independent validation** because both statue frames
participated in forming the hypothesis.

## Ordinal-recovery rule from this point

1. telemetry similarity is never sufficient to claim a visual ordinal;
2. user/original-reviewer scene recognition is the highest-value identity anchor;
3. a complete archive offset/order needs at least two independent visual anchors
   or actual JPEG-instance order;
4. placement labels derived directly from rendered photographs may survive an
   ordinal correction;
5. any analysis keyed to the old +30 Part-3 numbering must be treated as stale.

No live APK correction is authorized by this recovery.
