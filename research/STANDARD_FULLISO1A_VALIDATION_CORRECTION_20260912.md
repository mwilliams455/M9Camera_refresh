# STANDARD_FULLISO1A validation correction — 2026-09-12

## Correction

An initial five-RAW offline RBANCHOR1A cross-scene replay was invalid because it omitted the production NORM030 physical LensShadingMap stage before demosaic/Sharp. Xiaomi 15 Ultra wide-module OpcodeList2 GainMaps reach roughly 4–5x near corners, so raw-only replay materially changes the MHC/Sharp signal domain.

The rejection of SHARPSOURCE1C/RBANCHOR1A based on that raw-only replay is withdrawn.

## Corrected replay ordering

DNG black subtraction -> exact per-CFA OpcodeList2 GainMap interpolation -> normalized linear Bayer -> q14 / neutral-MHC / Leica-green Sharp source -> RBANCHOR1A.

Across the five mounted RAWs, RBANCHOR1A remains consistently much cleaner than SHARPSOURCE1B in edge R/B clamp metrics and removes the catastrophic ordinary-scene B-zero result seen in the invalid replay.

Representative mean edge clamp/cyan percentages (1B -> 1C):

- 2026-09-12 foliage/sky regression: R0 15.903 -> 6.612; B0 12.784 -> 4.163; cyan 0.507 -> 0.490.
- 2026-09-07 13:12 scene: R0 10.089 -> 2.406; B0 4.980 -> 0.975; cyan 0.178 -> 0.094.
- 2026-09-06 18:51 scene: R0 0.075 -> 0.015; B0 0.064 -> 0.004; cyan 0 -> 0.
- 2026-09-07 11:21 scene: R0 7.835 -> 1.801; B0 4.000 -> 0.528; cyan 2.688 -> 1.950.
- 2026-09-07 07:48 scene: R0 0.023 -> 0.002; B0 0.018 -> 0.001; cyan 0.001 -> 0.002.

No claim is made that RBANCHOR1A is bit-exact Leica R/B reconstruction. It remains an explicitly labelled frozen-MHC R-G/B-G proxy around the recovered sharpened Leica green/base. Exact packed BF561 R/B closure remains a later fidelity refinement if needed.

## Promotion implication

RBANCHOR1A is acceptable as the seam for the first complete Standard ISO schedule, subject to device validation. The next candidate must use the canonical 13x2050 Sharp base bank and proven Standard modes [4,4,4,4,4,4,3,3,3,3,3,2,2].
