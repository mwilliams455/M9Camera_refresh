# M9PREPPERF1A — exact parallel pre-SAT preparation

Parent: **1.87 / M9NOISEPERF1A PARALLEL8**.

The 1.87 phone capture proved the new NOISECANCEL parallel path itself was
successful (about 291 ms), but the existing pre-SAT preparation rose to about
1125 ms. PREPPERF1A targets only that preparation stage.

## What changes

The existing 128-row in-place preparation remains structurally identical:

1. preserve the two-row uncorrected transformed halo;
2. camera-to-M9 transform the current band plus two look-ahead rows;
3. apply the frozen 0.25 pre-SAT chroma operation;
4. commit only the current 128-row band to the owning camera buffer.

Two computations inside each band are parallelized across **8 workers**:

- independent per-pixel `cameraToM9` preparation;
- `partial_chroma` destination rows while the source Q14 band remains immutable.

The original scalar `trialPrepare` and scalar `partial_chroma` entry points
are retained unchanged as parity oracles.

## Quality/memory gate

This is performance-only:

- pre-SAT chroma strength remains 0.25;
- camera-to-M9 math is unchanged;
- 128-row banding is unchanged;
- two-row halo semantics are unchanged;
- no full-frame Q14 allocation/copy is added;
- NOISEPERF1A / NOISECANCEL1B are untouched;
- AMaZE, SOURCECAL, TC20, SAT2, curve02, BT.601/TG1 and exposure are untouched.

The regression requires byte-exact in-place output against the frozen scalar
out-of-place path over multiple band sizes and one full 4096x3072 frame.

Version: **1.88-m9prepperf1a-parallel8-noiseperf1a-tg1**.
