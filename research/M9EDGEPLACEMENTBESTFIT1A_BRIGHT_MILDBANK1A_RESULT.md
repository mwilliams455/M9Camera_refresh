# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT MILDBANK1A EXACT RESULT

Research-only. No live APK, capture policy, TC20, curve02, color science, JPEG quality, or frozen renderer change.

## Purpose

Resolve the useful low-strength BRIGHT RGB-pivot range after exact-pixel replay of the two prospective September-5 activations.

The prior broad exact blind bank contained:

```text
Frozen / RGB035 / RGB050 / RGB075
```

That test showed that stronger darkening progressively loses the desired M9 character on these natural prospective frames. A second exact bank therefore narrowed the range to:

```text
Frozen / RGB015 / RGB025 / RGB035
```

The source JPEGs were the actual frozen renderer outputs uploaded by the user. The RGB pivot law is the reconstructed 0.85-pivot, ratio-preserving operator using exact BT.601 Q14 luma.

## Exact blind decode

### 173828

Blind mapping:

```text
A = Frozen
B = RGB035
C = RGB025
D = RGB015
```

User choice:

```text
D
```

Decoded preference:

```text
RGB015
```

Exact finished-luma metrics:

| treatment | median Y | q95 Y | q99 Y | dark <=64 |
|---|---:|---:|---:|---:|
| Frozen | 81.69 | 180.16 | 197.00 | 36.23% |
| RGB015 | 76.46 | 177.16 | 195.00 | 40.08% |
| RGB025 | 73.21 | 175.15 | 193.99 | 42.55% |
| RGB035 | 70.11 | 173.11 | 192.94 | 44.96% |

Important context: Frozen had already been judged photographically acceptable in isolation. Therefore RGB015 being preferred in a direct comparison is evidence of a mild aesthetic improvement, not proof that this frame should be automatically classified as BRIGHT_FAIL.

`173828` remains a required HOLD / false-activation control for any MIDKEY selector unless a future independent morphology justifies intervention.

### 181559

Blind mapping:

```text
A = RGB025
B = RGB035
C = Frozen
D = RGB015
```

User choice:

```text
A or D
```

Decoded preference:

```text
RGB025 or RGB015
```

Exact finished-luma metrics:

| treatment | median Y | q95 Y | q99 Y | dark <=64 |
|---|---:|---:|---:|---:|
| Frozen | 82.08 | 157.19 | 193.68 | 30.99% |
| RGB015 | 76.96 | 152.84 | 191.68 | 35.80% |
| RGB025 | 73.73 | 149.97 | 189.94 | 39.09% |
| RGB035 | 70.62 | 147.12 | 188.66 | 42.42% |

This frame independently satisfies the existing research-only LOWKEY_OPENING1A morphology and is therefore the stronger mechanism-positive prospective case.

The exact mild-bank result says that useful correction is confined to approximately 0.15–0.25 EV pivot strength. RGB035 is already beyond the preferred zone in this resolved comparison.

## New evidence

The preferred mild treatments on both natural prospective frames land in a narrow body range:

```text
173828 RGB015: median ~76.5 Y
181559 RGB015: median ~77.0 Y
181559 RGB025: median ~73.7 Y
```

This motivates a **provisional natural-mild landing-zone probe** around roughly 74–77 Y.

This is NOT a production target. It must not be used to normalize arbitrary images to a common median.

Historical confirmed BRIGHT_FAIL frames often preferred stronger 0.50–0.75 pivot treatments, and prior work already established that preferred strength is not monotonic in global median, structuralLowKeyScore, or TC20 gain. Severe failures therefore remain a separate severity problem.

## Development consequence

Split BRIGHT treatment research into at least two severity regimes:

```text
BRIGHT mechanism / eligibility
    |
    +-- HOLD / acceptable Frozen
    |
    +-- NATURAL_MILD
    |      candidate bank = RGB015 / RGB025
    |      RGB035 retained only as upper stress bound
    |
    +-- SEVERE_CONFIRMED_FAIL
           historical candidate bank = RGB035 / RGB050 / RGB075
           no automatic strength mapping yet
```

The mild and severe banks must not be merged into a single formula until a feature with prospective falsification support separates them.

## Current selector implications

1. Do not revive the failed MIDKEY scalar selector simply because 173828 prefers RGB015 side-by-side. Frozen remains acceptable and zero unnecessary correction remains the priority.
2. LOWKEY_OPENING1A remains the better explanation for 181559.
3. For natural LOWKEY prospective activations, 0.15–0.25 is now the first treatment range to test.
4. Do not use RGB050/RGB075 on natural borderline cases merely because historical severe BRIGHT_FAIL anchors tolerated or preferred them.
5. Preserve DNG and frozen renderer unchanged.

## Next falsification

For future untouched prospective BRIGHT candidates:

- classify Frozen visually first, before treatment exposure;
- if LOWKEY_OPENING1A is ON and Frozen is at least mildly too open, generate exact RGB015 / RGB025 / RGB035;
- record the exact finished body metrics;
- test whether the preferred mild treatment repeatedly lands near the provisional 74–77 Y zone;
- any GOOD frame requiring no correction remains HOLD even if a slight side-by-side preference exists.

Only after multiple independent cases should the landing-zone observation be considered for a machine-readable severity stage.
