# M9PHASENOISEPERF1B — exact symmetric-pair tile reuse

Parent: **1.90 / M9PHASENOISEPERF1A BANDED TERM REUSE**.

The 1.90 Xiaomi 15 Ultra validation reduced the same-phase RAW-noise stage from
about 2.23 s to **1.247 s** while preserving byte-exact output. It remains the
largest single render block; actual AMaZE was about 0.502 s.

## 1B optimization

The filter evaluates 24 same-Bayer-phase candidate offsets. Every offset has a
symmetric opposite, and the patch weight is exactly the same for the unordered
pair:

`W(i,d) == W(i+d,-d)`.

1B computes only the 12 canonical negative-half-plane weights inside bounded
**64-row × 512-column target tiles**. A four-pixel target halo makes the
opposite-direction lookup valid at tile boundaries.

Crucially, reverse contributions are **not** accumulated early. Production still
walks all 24 candidates in the exact original dy/dx order. Positive candidates
retrieve the canonical weight at the neighbour coordinate and then perform the
same `sum += weight * raw[j]` and `ws += weight` operations at the same point
in the scalar sequence.

The existing 1A normalized-pair term reuse is retained inside each canonical
direction. No full-frame weight or distance cache is created.

## Frozen photography

Unchanged:

- quarter RAW-noise blend strength;
- Camera2 variance authority;
- clipping/censor behavior;
- 3×3 same-phase patch;
- 24 candidate geometry;
- candidate accumulation order;
- patch accumulation order;
- exponential weight function and rounding;
- AMaZE algorithm/chunking;
- PREPPERF1A, NOISEPERF1A, TC20, colour, tone and exposure.

## Quality gate

CI compares 1B byte-for-byte against both the original scalar implementation and
1.90's banded 1A implementation across varied dimensions, 1/2/4/8 workers,
explicit 64-row/512-column seam stress, and all four CFA patterns through the
complete reconstruction path.

Version: **1.91-m9phasenoiseperf1b-symtile-phasenoiseperf1a-tg1**.
