# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot.

## Exact-ID labels currently joined

- `GOOD`: 1
  - `IMG_20260904_101204` (`M9_STRONG`)
- `BRIGHT_FAIL`: 6
  - 18:49:27
  - 18:49:37
  - 19:03:46
  - 19:04:01
  - 19:04:29
  - 19:43:07
- `BOUNDARY`: 0 exact-ID joins
- `DARK_FAIL`: 0 exact-ID joins

## Visual labels known but not yet exact-ID joined

Confirmed visual `DARK_FAIL` by September-4 corpus ordinal:
- #4
- #40
- #73
- #80
- #98

Boundary / ambiguous by corpus ordinal:
- #86
- #87

The missing exact joins are an ordinal-to-filename mapping problem, not a visual-label uncertainty.

## Readiness guard

`m9edgeplacement1a_readiness.py` defaults:

- minimum `GOOD`: 30
- minimum `BOUNDARY`: 2
- minimum target-tail examples: 2

Applying those minima to the currently exact-joined seed gives:

- BRIGHT_FAIL rule interpretation: **NOT READY**
- DARK_FAIL rule interpretation: **NOT READY**

Reason:
- BRIGHT has enough positive examples but too few exact GOOD/boundary controls.
- DARK has visually confirmed positives but they are not yet joined to diagnostic capture identities.

Any conjunction/single-feature rankings generated before readiness is satisfied are exploratory only. A zero-false-positive result on the present exact-ID seed must not be treated as evidence for promotion.

## Next data action

Recover the five September-4 archive bytes and run `m9edgeplacement1a_archive_index.py` to map the retained visual ordinals back to exact `IMG_20260904_*` capture stems.

Then populate at least 30 visually accepted exact GOOD controls, including:
- ordinary daylight
- flowers / foliage
- paths / street scenes
- ordinary indoor
- intentional low-key / silhouette
- highlight-stress controls where photographically acceptable
- both `M9_STRONG` and `M9_IMPROVABLE` GOOD frames

Once those exact joins exist, run:

1. `m9edgeplacement1a_replay.py`
2. `m9edgeplacement1a_conjunction_search.py`
3. `m9edgeplacement1a_readiness.py`

Only interpret candidate rules when readiness passes. Even then, Frozen regression and visual validation remain mandatory before any live selector work.
