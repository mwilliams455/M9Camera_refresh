# M9 BESTFIT1A — BRIGHT BROADOPENING NEARMISS1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, colour science, JPEG quality, or DNG change.

## Purpose

Challenge `BROADOPENING1A` against the already documented September-5 BRIGHT/MIDKEY near-miss neighborhood rather than only the structurally-low-key subset.

The sign diagnostic remains:

```text
medianOpeningEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95OpeningEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BROAD_POSITIVE = medianOpeningEv > 0 AND q95OpeningEv > 0
```

This is a cross-pipeline placement diagnostic only, not exposure EV and not treatment authority.

## Seven previously documented near-misses

| frame | preview median -> finished | median proxy | preview q95 -> finished | q95 proxy | sign class |
|---|---|---:|---|---:|---|
| 173028 | 137 -> 85 | -0.689 | 186 -> 162 | -0.199 | RETAINED_OR_DENSER |
| 173100 | 137 -> 89 | -0.622 | 207 -> 221 | +0.094 | UPPER_POSITIVE_BODY_NONPOSITIVE |
| 173208 | 144 -> 92 | -0.646 | 206 -> 180 | -0.195 | RETAINED_OR_DENSER |
| 175115 | 93 -> 81 | -0.199 | 200 -> 188 | -0.089 | RETAINED_OR_DENSER |
| 175307 | 112 -> 82 | -0.450 | 203 -> 180 | -0.173 | RETAINED_OR_DENSER |
| 175833 | 130 -> 87 | -0.579 | 166 -> 139 | -0.256 | RETAINED_OR_DENSER |
| **181404** | **78 -> 82** | **+0.072** | **192 -> 196** | **+0.030** | **BROAD_POSITIVE** |

Result:

```text
BROAD_POSITIVE: 1 / 7
mixed q95-only redistribution: 1 / 7
non-positive body opening: 6 / 7
```

The sole broad-positive near-miss is the already known `181404` LOWKEY boundary/HOLD case.

## Why 173100 matters

`173100` is a useful falsifier for q95 authority:

```text
body: 137 -> 89      strongly denser
q95:  207 -> 221     slightly brighter
```

This is exactly the kind of cross-stage tonal redistribution that a q95-only rule would misread as opening.

The conjunction of global median and q95 signs correctly leaves it outside `BROAD_POSITIVE`.

## Comparison to 181559

Prospective NATURAL_MILD `181559`:

```text
preview median 66 -> finished 82   ~= +0.313
preview q95    141 -> finished 161 ~= +0.191
broad minimum                      ~= +0.191
```

Boundary/HOLD `181404`:

```text
preview median 78 -> finished 82   ~= +0.072
preview q95    192 -> finished 196 ~= +0.030
broad minimum                      ~= +0.030
```

The two are directionally consistent but differ materially in magnitude. This is encouraging as a ranking diagnostic, but it must not be converted into a strength threshold from two broad-positive frames.

## Combined retrospective picture

Evidence now checked includes:

- 29 same-build Part-3 pairs: **0/29 BROAD_POSITIVE**;
- 10 visually labeled Part-3 GOOD controls: **0/10 BROAD_POSITIVE**;
- 2 visually labeled Part-3 BOUNDARY controls: **0/2 BROAD_POSITIVE**;
- 7 September-5 BRIGHT near-misses: **1/7 BROAD_POSITIVE**, the known `181404` HOLD;
- 12 structurally-low-key September-5 natural frames: only `181559` has positive global median opening; q95 corroborates it;
- `181559`: BROAD_POSITIVE and exact mild-treatment positive.

These groups overlap in purpose and should not be combined into a statistical prevalence estimate. They are falsification sets, not random samples.

## Interpretation

Current evidence supports a narrow semantic claim:

> `BROAD_POSITIVE` is useful evidence that the frozen render opened both the useful body and upper-body relative to preview placement.

Current evidence does **not** support:

> every BROAD_POSITIVE frame needs correction.

`181404` is the direct counterexample to that stronger claim.

Therefore the correct role remains:

```text
LOWKEY / BRIGHT morphology
  -> BROADOPENING corroboration
       not broad-positive -> strong HOLD evidence
       broad-positive     -> opened-mechanism evidence
  -> visual/severity stage still decides HOLD vs NATURAL_MILD
```

## Development consequence

Do not add `BROAD_POSITIVE` as automatic treatment authority yet.

It is now sufficiently promising to retain as the leading HOLD-vs-opened **corroborating diagnostic**, while severity remains categorical and conservative.

The next useful falsifier is any visually GOOD ordinary frame with a materially positive broad-opening minimum. Existing paired data should continue to be mined for that before new shooting is requested.
