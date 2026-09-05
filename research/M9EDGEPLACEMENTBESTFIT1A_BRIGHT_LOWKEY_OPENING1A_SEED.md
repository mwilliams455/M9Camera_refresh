# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_LOWKEY_OPENING1A SEED

Research-only. No live APK, capture policy, TC20, curve02, color science, or frozen renderer change.

## Purpose

Define a first conservative BRIGHT-tail morphology without assuming that BRIGHT correction is the negative mirror of DARK correction.

Historical BRIGHT_FAIL evidence shows at least one clean mechanism: a genuinely coherent low-key scene is normalized by TC20 toward its ordinary body key and the finished JPEG becomes too open / loses ambience. This is distinct from clipping, backlight, or a legitimately high-key scene.

## Provisional selector seed

```text
BRIGHT_LOWKEY_OPENING1A =
    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND tc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75
```

Threshold status: provisional high-specificity research seed; not frozen; not live.

This branch intentionally accepts partial recall. Do not weaken it merely to recover every known BRIGHT_FAIL frame. Other BRIGHT morphologies may require separate branches.

## Historical expected behavior

Expected ON from retained historical evidence:

- 184927 — structuralLowKeyScore ~0.732; TC20 median-limited ~2.63x; finished median ~93
- 184937 — structuralLowKeyScore ~0.625; TC20 median-limited ~1.60x; finished median ~92
- 194307 — structuralLowKeyScore 1.000; TC20 median-limited ~4.94x; finished median ~87; RAW hard clip 0

Expected OFF / unresolved by design:

- 190346 — structuralLowKeyScore ~0.008
- 190401 — structuralLowKeyScore ~0.506 and guard-limited; likely separate morphology
- 190429 — structuralLowKeyScore ~0.323

The branch therefore explains a coherent subset, not the entire BRIGHT_FAIL bank.

## Hard-negative falsification

### 182756 — prospective high-key split-field boundary

- preview global median 85
- preview q75 200
- top-third mean ~192.4
- top-third >=192 fraction ~0.905
- finished global q95 ~237
- structuralLowKeyScore = 0

Result: OFF. A genuinely bright/high-key split field must not be darkened merely because it has a large bright tail.

### 182012 — prospective clipped-but-dark hard negative

- preview median 36
- preview q95/q99 255
- preview dark<=64 ~0.731
- preview bright>=192 ~0.165
- finished median ~2
- finished q95 ~247
- structuralLowKeyScore = 0

Result: OFF. Clipping/high q95 alone is not BRIGHT failure evidence.

### 084525 — known GOOD, finished median overlaps BRIGHT_FAIL range

- preview median 91
- finished median 79
- finished q95 226
- strong spatial split
- structuralLowKeyScore = 0

Result: OFF. Finished median alone is unsafe.

### 084858 — known GOOD, genuinely very dark M9-like frame

- structuralLowKeyScore ~0.536
- finished median 14
- finished q95 151

Result: OFF on both low-key threshold and finished-body requirement. Genuine dense rendering must remain untouched.

Additional GOOD/safety controls with retained structuralLowKeyScore = 0 include 084513, 084146, 143532, and 164035.

## Why not use a preview-median-only gate

Preview median can strengthen diagnostics but should not replace structuralLowKeyScore. The structural score already encodes coherence / broad-bright / spatial-separation / backlight context. The hard negatives above show why high/low preview luminance alone is insufficient.

## Treatment implications

Do not yet assign -0.75 EV to this branch.

Historical BRIGHT work found that the useful operation may be asymmetric to DARK rescue: lower-body / lower-mid density restoration while keeping upper tones anchored. The earlier BESTFIT bright bank (RGB035 / Y035 / Y050) showed scene-dependent preferences and no universal winner.

Current absolute research envelope remains:

```text
DARK side:  0 .. +0.75 EV hard ceiling (empirically tested)
BRIGHT side: 0 .. -0.75 EV proposed hard ceiling only
```

The negative ceiling requires direct treatment replay on confirmed BRIGHT_FAIL DNGs before promotion.

## Architecture consequence

```text
BRIGHT eligibility
    -> BRIGHT_LOWKEY_OPENING1A (first conservative branch)
    -> later additional BRIGHT branches only if independently justified
    -> determine desired photographic treatment/severity
    -> clamp to absolute -0.75 EV envelope
    -> finished-image safety / rollback
    -> publish
```

BRIGHT and DARK remain separate/asymmetric selectors and may use different treatment operators.
