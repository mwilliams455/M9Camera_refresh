# M9PHASENOISEPERF1B — exact symmetric patch-weight reuse

Parent: **1.90 / PHASENOISEPERF1A BANDED TERM REUSE**.

The 1.90 phone capture reduced the selected same-phase RAW noise proposal from
about 2.23 s to about **1.25 s**, while remaining byte-exact to the original
filter. Phase noise is still the largest individual reconstruction stage.

## Exact identity used

For a target sample i and same-phase displacement d, the patch weight is exactly
symmetric:

`weight(i,d) == weight(i+d,-d)`.

The patch contains the same nine sample pairs in reverse. Squared differences,
two-term variance sums, patch traversal order, count threshold and exp() input
are therefore identical.

1B computes only the 12 canonical half-plane patch weights. During final output
it still walks **all 24 candidate neighbours in the original dy/dx order**.
Candidates in the opposite half-plane read the corresponding symmetric cached
weight at the candidate centre.

## Bounded memory

The cache is restricted to **32x256 target tiles** plus the existing four-pixel
candidate and two-pixel patch halos. Scratch is private per OpenMP worker. There
is no full-frame distance, patch-weight or contribution cache.

## Hard quality gate

The untouched scalar filter and 1.90 banded implementation remain compiled as
oracles. CI requires exact equality for:

- scalar vs 1.90 vs 1.91 uint16 RAW-noise output;
- varied dimensions and 1/2/4/8 workers;
- clipping and zero-variance cases;
- 32-row and 256-column tile-boundary stress;
- complete reconstruction RGB and statistics across all four CFA patterns.

No RAW noise strength, AMaZE, exposure, colour, tone, PREPPERF or NOISECANCEL
parameter changes.

Version: **1.91-m9phasenoiseperf1b-symmetric-amazeperf1a-tg1**.
