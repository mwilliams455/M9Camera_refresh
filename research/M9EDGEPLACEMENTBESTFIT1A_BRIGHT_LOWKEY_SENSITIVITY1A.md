# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY SENSITIVITY1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG changes.

## Purpose

Test whether the provisional `structuralLowKeyScore >= 0.60` term in `BRIGHT_LOWKEY_OPENING1A` is robust or merely sitting on a fragile numerical boundary.

Current unchanged LOWKEY seed:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

## Known lower-side evidence

- `084858` — visually GOOD extreme-dark hard negative; score ~0.536; finished median 14; remains OFF independently on body.
- most prospective high-body controls have score = 0 and are far from the structural boundary.

## Historical upper-side evidence

- `184937` — confirmed BRIGHT_FAIL / LOWKEY treatment-positive; score ~0.625; gain ~1.60; finished median ~92; RGB050 preferred.

This means the retained historical positive sits only ~0.025 above the provisional 0.60 score floor, so raising the score floor would immediately endanger recall.

## Critical prospective sensitivity frame: 181404

Untouched 2026-09-05 natural cohort frame:

```text
structuralLowKeyScore ~= 0.545
tc20Gain = 2.5540036931
finishedGlobalMedianY = 82
finishedGlobalQ95Y = 196
```

The frame fails the current LOWKEY seed **only on structuralLowKeyScore**.

Therefore:

- at score floor 0.60 -> OFF
- lowering toward ~0.54 would make it ON
- gain/body terms would not protect it

This is the correct visual sensitivity boundary to inspect before any structural-score adjustment.

## Required interpretation

Do not lower the score floor from numerical pressure alone.

Visual-first outcomes:

### If Frozen 181404 is already right / M9-like

Then the current 0.60 floor is providing useful specificity. `181404` becomes a strong near-threshold GOOD control and any future score relaxation must preserve it OFF through a different structural discriminator.

### If Frozen 181404 is genuinely too open

Then the current seed has a real recall miss. Do **not** simply lower the score threshold because that would also move toward other low-score controls. Instead compare 181404 morphology with 181559 and historical LOWKEY positives to identify the missing structural feature, then retest prospectively.

### If uncertain

Keep 0.60 unchanged and classify 181404 as a boundary. Under-intervention remains preferable.

## Current status

```text
thresholdStatus = provisional_falsification_seed_not_frozen_not_live
181404VisualClass = PENDING_USER_REVIEW
selectorChangeAuthorized = false
```

The current 0.60 score floor remains unchanged pending visual judgement.
