# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_MIDKEY_NORMALIZATION1A PROSPECTIVE FALSIFICATION

Research-only. No live APK, capture policy, TC20, curve02, color science, or frozen renderer change.

## Cohort

Untouched prospective Dropbox cohort captured 2026-09-05 from 17:29:39 through 18:27:56.

- 47 photographs
- JPEG + DNG + `_M9.json` + `_M9_PRIMARY.json` available
- later than the 2 PM derivation cohort
- no manual forcing of BRIGHT conditions

## Original BRIGHT_MIDKEY_NORMALIZATION1A seed

```text
achievedIntentEv < +0.10
AND TC20 is median-limited
AND preview center median >= preview global median
AND finished global median >= 75 Y
AND finished global q95 <= 220 Y
```

The original seed produces four prospective activations:

- 17:33:42 — preview median 198, center 201, intent 0; finished median 117, q95 168
- 17:34:23 — preview median 155, center 161, intent 0; finished median 81, q95 134
- 17:38:28 — preview median 107, center 121, intent 0; finished median 81, q95 182
- 18:15:59 — preview median 66, center 66, intent approximately 0; finished median 82, q95 161

The first two are structurally problematic for the intended mechanism: their preview bodies are already bright/high-key. A branch intended to detect low/mid-key preview normalization should not activate merely because TC20 is median-limited and the finished body lies in the target band.

Therefore the original seed does **not** survive prospective falsification unchanged.

## Semantic refinement under test

Add a preview-body requirement:

```text
preview global median <= 120 Y
```

Full provisional conjunction:

```text
achievedIntentEv < +0.10
AND TC20 is median-limited
AND preview global median <= 120 Y
AND preview center median >= preview global median
AND finished global median >= 75 Y
AND finished global q95 <= 220 Y
```

Threshold status: research-only prospective refinement; not frozen; not live.

Rationale is semantic rather than fitted to one frame:

- historical treatment-positive MIDKEY anchor 190346: preview median 99
- historical treatment-positive MIDKEY anchor 190429: preview median 85
- prospective obvious bright-preview activations 173342/173423: 198 / 155
- hard negative 084303 remains testable at preview 112 and is still rejected independently by center/global direction and finished q95

## Refined prospective result

With the <=120 preview-body condition, only two of 47 prospective frames remain ON:

### 17:38:28

- TC20 median-limited: base gain ~0.946 <= guard ~2.099
- preview global median 107
- preview center median 121 (+14)
- achieved intent 0
- finished global median 81
- finished global q95 182

Result: `BRIGHT_MIDKEY_NORMALIZATION1A` candidate ON.

### 18:15:59

- TC20 median-limited: base gain ~2.063 <= guard ~3.703
- preview global median 66
- preview center median 66 (equal)
- achieved intent approximately 0
- finished global median 82
- finished global q95 161

Result: `BRIGHT_MIDKEY_NORMALIZATION1A` candidate ON.

These are **unlabelled prospective activations**, not assumed BRIGHT_FAIL positives. Do not tune them away before visual classification.

## Useful prospective near misses

- 17:30:28 — median-limited; finished 85 / q95 162; preview 137 with center 134. OFF by preview-body and center-direction terms.
- 17:31:00 — median-limited; finished median 89; q95 221. OFF by q95 by only 1 Y.
- 17:32:08 — median-limited; finished 92 / q95 180; preview 144, center 65. OFF.
- 17:51:15 — median-limited; finished 81 / q95 188; preview 93, center 90. OFF by center direction.
- 17:53:07 — median-limited; finished 82 / q95 180; preview 112, center 93. OFF by center direction.
- 18:14:04 — median-limited; finished 82 / q95 196; preview 78, center 69. OFF by center direction.
- 17:58:33 — median-limited; finished 87 / q95 139; preview 130, center 127. OFF by preview-body and center direction.

These near misses show that the <=120 preview threshold is not carrying all separation by itself.

## Cross-tail / stress controls

The DARK prospective frames around 17:44–17:50 remain OFF this BRIGHT branch because their finished body is far below 75 Y and/or TC20 is guard-limited.

18:20:12 clipped-but-dark hard negative remains OFF: finished median ~2 Y despite a large bright tail.

18:27:56 high-key split-field boundary remains OFF: TC20 guard-limited and finished q95 ~237.

## Current decision

Do not commit the <=120 guard into a production selector yet.

The branch has narrowed from 4/47 to 2/47 prospective activations in a mechanism-consistent way, but the two survivors require visual classification of Frozen versus the established RGB-pivot density bank.

Next evidence:

1. visually classify 17:38:28 and 18:15:59 as treatment-positive, Frozen-preferred, or inconclusive;
2. if treatment-positive, test blind RGB035 / RGB050 / RGB075 on both;
3. only then decide whether the <=120 preview-body guard belongs in the canonical BRIGHT_MIDKEY_NORMALIZATION1A seed.

Zero false activation remains more important than full BRIGHT recall.
