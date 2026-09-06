# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY MORNING CROSS-COHORT1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG changes.

## Purpose

Challenge the unchanged `BRIGHT_LOWKEY_OPENING1A` seed against the existing September-5 morning field set after the 47-frame late-afternoon prospective cohort was closed.

This morning set is **cross-cohort hard-negative evidence**, not a later prospective validation batch. It therefore cannot substitute for a second future treatment-positive activation, but it can immediately expose specificity failures.

Existing provisional seed, unchanged:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

Threshold status remains `provisional_falsification_seed_not_frozen_not_live`.

## Morning set

Audited frames:

```text
084712
084858
085011
085126
085303
085321
085339
085353
085742
085848
085955
090211
090359
```

Result:

- frames audited: **13**
- full LOWKEY activations: **0/13**
- structural-score-qualified frames (`score >= 0.60`): **1/13**
- score-qualified frame: **085126**

## Critical GOOD / hard-negative controls

### 084712 — visually GOOD

- `structuralLowKeyScore = 0`
- LOWKEY: **OFF**

This is a healthy path/field control and does not enter the LOWKEY mechanism.

### 084858 — visually GOOD extreme-dark hard negative

- `structuralLowKeyScore ~= 0.53645`
- below the 0.60 structural floor
- LOWKEY: **OFF**

This is especially important because the finished JPEG is intentionally extremely dense yet photographically coherent. The branch does not infer BRIGHT correction from darkness itself.

## Strongest cross-cohort challenge: 085126

`085126` crosses both the structural and gain terms:

```text
structuralLowKeyScore ~= 0.99670
tc20Gain ~= 2.05191
finishedGlobalMedianY = 24
finishedGlobalQ95Y = 217
```

Result: **OFF on finished-body placement**.

This independently confirms the semantic importance of the finished-body term. A coherent low-key preview plus substantial TC20 gain is not enough; the finished JPEG must actually have been opened into the mid-body region before LOWKEY can activate.

## Remaining morning controls

| Frame | structuralLowKeyScore | LOWKEY |
|---|---:|---|
| 085011 | 0 | OFF |
| 085303 | ~0.00867 | OFF |
| 085321 | 0 | OFF |
| 085339 | 0 | OFF |
| 085353 | 0 | OFF |
| 085742 | 0 | OFF |
| 085848 | 0 | OFF |
| 085955 | 0 | OFF |
| 090211 | 0 | OFF |
| 090359 | 0 | OFF |

No PRIMARY-side treatment check is required for these score-OFF frames because they fail before gain/body evaluation.

## Combined evidence after this audit

### Late-afternoon untouched prospective cohort

- 47 frames
- 12 structural-score-qualified
- 1 full LOWKEY activation: `181559`
- 11 structural low-key controls rejected by gain and/or finished-body placement

### Morning cross-cohort controls

- 13 frames
- 1 structural-score-qualified
- 0 full LOWKEY activations
- `085126` rejected by finished body despite score ~0.997 and gain ~2.05

Combined currently inspected natural/control evidence:

```text
60 frames
13 structural-score-qualified
1 full LOWKEY activation
59 LOWKEY OFF
```

Do not interpret `1/60` as a production false-positive rate or prevalence estimate because the sets were collected for different research purposes and are not one statistically sampled population.

## Current conclusion

The unchanged LOWKEY conjunction continues to behave as intended:

```text
coherent low-key structure
AND meaningful renderer opening
AND finished JPEG lands in opened mid-body region
-> candidate
```

It is not behaving as:

```text
dark scene -> darken
```

The finished-body guard remains essential and should not be removed or weakened.

No threshold tuning is justified by this audit. In particular:

- do not raise the structural-score threshold around `181559`;
- do not derive treatment strength from structural score;
- do not remove the finished-body requirement;
- do not promote the branch live from one prospective treatment-positive activation.

## Next development question

The next useful offline problem is **severity separation**, not broader LOWKEY eligibility:

- `181559` is a natural mild case, preferring approximately RGB015–RGB025;
- historical confirmed severe BRIGHT_FAIL LOWKEY anchors `184927`, `184937`, and `194307` tolerated/preferred materially stronger RGB-pivot density.

Research should compare the mild prospective anchor against those severe historical anchors to identify a falsifiable severity feature without changing the now-promising LOWKEY eligibility seed.

A second later natural treatment-positive LOWKEY activation is still required before any production promotion.
