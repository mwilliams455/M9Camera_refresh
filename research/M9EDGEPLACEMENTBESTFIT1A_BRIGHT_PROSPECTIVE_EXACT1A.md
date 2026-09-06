# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT PROSPECTIVE EXACT1A

Research-only. No live APK, capture policy, TC20, curve02, colour science, JPEG quality, or frozen renderer change.

## Purpose

Replace the earlier approximate visual mock-up with an exact-pixel replay using the two user-uploaded frozen JPEGs:

- `IMG_20260905_173828_1788626308900_00`
- `IMG_20260905_181559_1788628559798_00`

The exact test uses one JPEG decode per source and applies the reconstructed 0.85-pivot RGB-ratio-preserving BRIGHT operator directly to those decoded pixels.

## Treatment bank

```text
Frozen
RGB035
RGB050
RGB075
```

Operator:

```text
pivot = 0.85
w(Y) = clamp(1 - Y/pivot, 0, 1)
EV(Y) = -strength * w(Y)
scale(Y) = 2^EV(Y)
```

Luma uses exact project BT.601 Q14 coefficients:

```text
Y = (4899R + 9617G + 1868B) / 16384
```

R/G/B receive the same per-pixel scale, preserving RGB ratios apart from final 8-bit rounding.

## Blind protocol

- A/B/C/D are independently randomized for each source frame.
- Review variants are saved as lossless PNG after the common source JPEG decode.
- This avoids JPEG-recompression differences influencing visual judgement.
- `DECODE_KEY.json` is intentionally excluded from the blind review ZIP.

## Why this supersedes the approximate mock-up for promotion decisions

The earlier comparison was directionally useful and yielded two provisional observations:

- 173828: Frozen looked correct; stronger density rapidly became too dark.
- 181559: mild added density appeared promising, but stronger darkening progressively lost the desired M9 character.

Those observations are retained as hypotheses only. Any selector/severity promotion should use the exact-pixel result from this experiment.

## Development question

The exact blind test is intended to determine whether the BRIGHT architecture should explicitly separate:

```text
mechanism eligibility
    -> HOLD or treatment-positive
    -> bounded severity choice
    -> finished-image safety / rollback
```

rather than mapping eligibility directly to a fixed treatment strength.

### Required outcomes

For 173828, zero-false-positive policy predicts Frozen/HOLD should win or at minimum remain preferable to meaningful intervention.

For 181559, the current hypothesis is that only a mild treatment should remain competitive; if stronger treatments are preferred in the exact replay, the severity model must remain scene-dependent rather than capped artificially at RGB035.

## Status

Exact blind set generated from the uploaded source JPEGs. User visual classification pending before decode and before any selector/severity code change.
