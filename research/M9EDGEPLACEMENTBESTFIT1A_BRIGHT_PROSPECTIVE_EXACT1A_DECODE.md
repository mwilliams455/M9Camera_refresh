# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT PROSPECTIVE EXACT1A DECODE

Research-only. No live APK, capture policy, TC20, curve02, colour science, JPEG quality, or frozen renderer change.

## Exact source basis

This result supersedes the earlier image-generation approximation. The two original frozen JPEGs were uploaded directly and the established 0.85-pivot RGB-ratio-preserving operator was applied pixel-exactly to the decoded source pixels.

Blind bank per frame:

```text
Frozen
RGB035
RGB050
RGB075
```

Outputs were reviewed as lossless PNGs to avoid JPEG-recompression bias.

## Blind decode

### `IMG_20260905_173828_1788626308900_00`

Blind map:

```text
A = RGB035
B = Frozen
C = RGB075
D = RGB050
```

User judgement:

- A preferred
- Frozen/B remains acceptable in isolation
- stronger darkening is not desired

Exact luma response:

```text
Frozen median 81.69 Y
RGB035 median 70.11 Y
RGB050 median 65.71 Y
RGB075 median 58.98 Y
```

Interpretation:

`RGB035_PREFERENCE / FROZEN_ALREADY_ACCEPTABLE`

This must NOT be relabelled as a correction-required BRIGHT failure. The frame was previously judged correct enough that no change would have been recommended without the forced comparison. It therefore proves that comparative treatment preference and edge-failure eligibility are different labels.

The provisional MIDKEY selector remains falsified by this frame. Do not widen MIDKEY merely because RGB035 wins in a forced blind bank.

### `IMG_20260905_181559_1788628559798_00`

Blind map:

```text
A = Frozen
B = RGB050
C = RGB075
D = RGB035
```

User judgement:

- between A and D
- lean toward D
- darker versions increasingly lose the desired M9 character

Exact luma response:

```text
Frozen median 82.08 Y
RGB035 median 70.62 Y
RGB050 median 66.20 Y
RGB075 median 59.43 Y
```

Interpretation:

`LOWKEY_OPENING1A / RGB035_SLIGHT_PREFERENCE / FROZEN_NEAR_TIE`

This frame retains the existing LOWKEY mechanism evidence (`structuralLowKeyScore ~0.876`, TC20 median-limited, gain ~2.06x), but treatment value is mild rather than strong.

## Development consequence

The exact prospective evidence supports three distinct concepts:

```text
1. failure/mechanism eligibility
2. comparative treatment preference
3. correction severity
```

They must not be collapsed into one boolean.

For normal prospective frames, this batch supports a bounded mild research zone rather than stronger darkening:

```text
0.00 EV  Frozen
0.15 EV  new mild probe
0.25 EV  new mild probe
0.35 EV  current mild upper candidate
```

RGB050/RGB075 remain valid for historically confirmed BRIGHT_FAIL subtypes, where prior blind work preferred stronger treatment on several anchors. This prospective result does NOT reduce the historical absolute 0.75 pivot research ceiling globally; it only argues that normal/ambiguous prospective cases need a separate mild severity class.

## Current architecture

```text
BRIGHT mechanism eligibility
    -> if no credible failure mechanism: HOLD even if an alternative may win side-by-side
    -> if credible mechanism:
         severity class
           MILD / STRONGER subtype-specific / HOLD
         -> bounded RGB-pivot candidate bank
         -> finished-response safety / rollback
```

Zero unnecessary interventions remains more important than maximizing pairwise preference.

## Next experiment

Run exact-pixel blinded mild bank on both prospective frames:

```text
Frozen / RGB015 / RGB025 / RGB035
```

Purpose:

- determine whether 173828's comparative RGB035 preference is actually maximized at a weaker treatment;
- determine whether 181559 can preserve more M9 character at 0.15–0.25 while retaining the useful density improvement;
- define a prospective MILD severity candidate without altering live code.
