# M9PHASENOISEPERF1A — exact banded same-phase noise acceleration

Parent: **1.89 / AMAZEPERF1A PARALLEL PERIPHERY**.

The first 1.89 phone profile resolved the reconstruction block:

- total reconstruction: ~3003 ms
- same-phase RAW noise proposal: **~2230 ms**
- actual AMaZE core: **~523 ms**
- variance transport: ~73 ms
- quarter blend: ~4 ms
- float input: ~10 ms
- output quantization: ~57 ms
- border: ~28 ms

So the dominant reconstruction cost is the selected quarter-strength RAW noise
proposal, not AMaZE interpolation.

## Optimization

The photographic algorithm is unchanged. The scalar filter compares a 3x3
same-Bayer-phase patch against 24 same-phase neighbours. For overlapping target
patches it repeatedly recomputes the same normalized pair term:

`(raw[a]-raw[b])^2 / (variance[a]+variance[b])`.

PHASENOISEPERF1A processes bounded 64-row target bands. For each candidate
displacement it computes that exact pair term once, then gathers the same nine
terms in the original py/px order. The 24 candidate displacements are still
visited in the original dy/dx order and the same `exp`, sum, weight sum and
`llround` operations are retained.

Scratch is per-worker and bounded. There is no 12 MP full-frame distance or
weight cache.

## Hard quality gate

The original `phase_noise` remains compiled unchanged as the oracle. CI
requires byte-for-byte equality between it and `phase_noise_banded_exact`
across varied dimensions, clipping/variance patterns, worker counts, a
structured scene-like target and all four CFA patterns through the complete
reconstruction path.

Version: **1.90-m9phasenoiseperf1a-banded-amazeperf1a-tg1**.
