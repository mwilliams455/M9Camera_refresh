# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY+BROAD PROSPECTIVE-2 PROTOCOL

**Status:** research-only / protocol freeze before next untouched natural cohort  
**Branch:** `m9edgeplacementbestfit1a-offline3`  
**Purpose:** prospectively falsify the current BRIGHT LOWKEY mechanism without retuning thresholds after seeing the next photographs.

## 1. Non-negotiable baseline freeze

The next cohort must use the existing frozen photographic path unchanged:

- R3.8-H25/TG1
- Cobalt Xiaomi 15 Ultra main-camera calibration
- M9 bridge/HSM
- SAT3 M06/M07
- firmware curve02
- exact BT.601 4:2:2
- 12 MP JPEG
- JPEG quality 95
- current capture/exposure framework
- current TC20
- current black/shadow/color policy
- DNG + JPEG output

No new APK is required for this prospective pass. Continue using the existing diagnostic build `M9Cam-EDGEPLACEMENTGATE1A`.

The diagnostic path remains read-only with respect to capture and rendered pixels.

## 2. Frozen BRIGHT LOWKEY structural seed

For this prospective cohort, do **not** change these thresholds after capture:

```text
BRIGHT_LOWKEY_OPENING1A =
    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND tc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75
```

These remain falsification thresholds, not production constants.

## 3. Frozen BROADOPENING corroborator

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BRIGHT_BROADOPENING1A =
    medianShiftEv > 0
    AND q95ShiftEv > 0
```

Important freeze:

- no minimum positive magnitude is introduced;
- `+0.001 EV` and `+0.20 EV` are both BROAD-positive for eligibility research;
- severity is **not** inferred from BROAD magnitude;
- do not fit a threshold between the prior `181404` HOLD boundary and `181559` mild-positive frame.

## 4. Frozen conjunction

```text
BRIGHT_LOWKEY_BROAD1A =
    BRIGHT_LOWKEY_OPENING1A
    AND BRIGHT_BROADOPENING1A
```

Meaning:

> The frame exhibits the coherent low-key morphology associated with the historical BRIGHT mechanism **and** the finished renderer has actually opened both body and upper-body relative to preview.

This is **treatment eligibility evidence only**.

It does not mean:

- treatment is mandatory;
- Frozen is photographically wrong;
- the required correction strength is known;
- the structural score should map monotonically to treatment strength.

## 5. Severity / HOLD remains a separate stage

The next prospective pass must preserve this architecture:

```text
mechanism eligibility
        ↓
visual photographic severity
        ↓
HOLD is valid whenever Frozen is already right
        ↓
only if treatment is justified:
    bounded RGB-pivot density candidate
        ↓
finished-response safety / rollback
```

Do not convert `BRIGHT_LOWKEY_BROAD1A` directly into a live darkening command.

## 6. MIDKEY branch remains failed/deferred

The prior `BRIGHT_MIDKEY_NORMALIZATION1A` prospective refinement is **not** part of Prospect-2.

Specifically, do not revive or retune:

```text
preview global median <= 120 Y
preview center median >= preview global median
finished q95 <= 220 Y
```

The 17:38:28 frame demonstrated that this path could select a photograph that was already visually acceptable. Prospect-2 should test the LOWKEY+BROAD conjunction, not patch MIDKEY around that frame.

## 7. Prospective cohort collection rules

Collect a new natural-shooting cohort after this protocol commit.

Preferred properties:

- normal use rather than deliberately forcing the selector;
- mixture of indoor/outdoor when practical;
- ordinary mid-key scenes;
- genuinely dark/low-key scenes that should remain dense;
- dark field with compact luminous subject;
- high-key/split-field scenes;
- low-light motion-assisted scenes;
- ordinary people/skin scenes if encountered naturally;
- some scenes where TC20 is median-limited and some where it is guard-limited.

Do **not** optimize the batch to generate BRIGHT activations. A zero-activation natural batch is valid evidence.

## 8. Required data per photograph

Retain the normal diagnostic set:

- JPEG
- DNG
- `_M9.json`
- `_M9_PRIMARY.json`

At evaluation time extract at minimum:

```text
achievedIntentEv
structuralLowKeyScore
tc20Gain
baseMedianGain
tc20GuardGain
TC20 binding state if available
previewGlobalMedianY
previewGlobalQ95Y
finishedGlobalMedianY
finishedGlobalQ95Y
medianShiftEv
q95ShiftEv
BRIGHT_LOWKEY_OPENING1A
BRIGHT_BROADOPENING1A
BRIGHT_LOWKEY_BROAD1A
```

Do not silently assume zero intent when the intent metric is absent.

## 9. Evaluation order is frozen

After collection:

1. score **every** frame with the frozen rules;
2. record the total cohort count and every activation;
3. record useful near misses, especially failures of only one conjunction term;
4. visually inspect current Frozen JPEGs for all activations before applying treatment;
5. label each activation as:
   - `FROZEN_RIGHT`
   - `MILD_TREATMENT_VALUE`
   - `CLEAR_BRIGHT_FAIL`
   - `UNCERTAIN`
6. only treatment-positive activations may enter a blinded RGB-pivot treatment test;
7. record ties and inconclusive results exactly;
8. do not change thresholds until the cohort has been completely scored and visually classified.

## 10. Treatment bank for treatment-positive activations

The preferred operator family remains RGB-ratio-preserving pivoted density:

```text
pivot = 0.85
w(Y) = clamp(1 - Y / pivot, 0, 1)
EV(Y) = -strength * w(Y)
scale(Y) = 2^EV(Y)
```

For mild prospective cases, test the smallest plausible strengths first.

Current research preference:

```text
Frozen
RGB015
RGB025
```

`RGB035`, `RGB050`, and `RGB075` remain useful stress/legacy envelope points but should not be assumed necessary for a mild activation.

The absolute BRIGHT research ceiling remains no stronger than the previously explored `RGB075` envelope unless a separate experiment explicitly changes it.

## 11. Prospect-2 falsification criteria

The conjunction becomes **stronger evidence** if:

- activations remain rare;
- ordinary GOOD frames remain OFF;
- dark but correctly dense M9-like frames remain OFF;
- high-key/split-field controls remain OFF;
- activated frames consistently exhibit real broad opening rather than isolated percentile noise;
- at least one new activation is independently judged treatment-positive.

The conjunction is **weakened or rejected** if:

- it repeatedly selects ordinary photographs where Frozen is already right;
- high structural-low-key scores alone dominate selection despite dense finished placement;
- BROAD sign-only activation produces many trivial false candidates;
- activation rate grows materially across ordinary shooting;
- treatment-positive evidence does not reproduce outside the 18:15:59 frame.

Do not rescue a failing prospective result by immediately retuning thresholds against the same cohort.

## 12. Historical evidence boundary

Exact historical preview-global and finished-global q95 pairs for the original `184927`, `184937`, `194307`, and `190401` anchors are not currently available in the recovered source set.

Retained historical evidence supports LOWKEY morphology and TC20-state claims, but it is insufficient to reconstruct exact historical `BRIGHT_BROADOPENING1A` status without inventing values.

Therefore historical BROAD status remains **UNKNOWN** until the original sidecars/JPEG diagnostics are recovered.

This evidence gap must not block a genuinely prospective second cohort, and it must not be filled by inference.

## 13. Promotion bar remains conservative

Even if Prospect-2 succeeds, no live promotion follows automatically.

Before a live exception path is considered, require at minimum:

- repeat prospective rarity;
- zero or near-zero GOOD false activation;
- more than one independent treatment-positive LOWKEY example;
- stable HOLD behavior on dark-but-correct controls;
- treatment strength selected separately from mechanism detection;
- rollback to Frozen whenever finished-response or visual confidence is weak.

The governing rule remains:

> Preserve the successful frozen M9 JPEG for the healthy middle; intervene only on strongly evidenced tails.
