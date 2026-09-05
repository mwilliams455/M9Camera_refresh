# M9EDGEPLACEMENTBESTFIT1A — BRANCHB SENSITIVITY1A / SWAN PAIR

**Date:** 2026-09-05  
**Status:** research-only. Canonical BESTFIT1A unchanged.

## Result

A one-at-a-time threshold sweep across the 29-frame Part-3 replay shows that the provisional Branch-B activation is unusually stable to most threshold changes but sensitive to the discrete matched-region collapse boundary.

Holding all other v2.83 conditions fixed:

- scene-spread minimum 1.20 through 1.50 -> only `164436`
- render P75 maximum 12 through 30 -> only `164436`
- render mean maximum 25 through 35 -> only `164436`
- retention collapse boundary -1.40 or -1.45 EV -> `164420` + `164436`
- retention collapse boundary -1.50 through -1.60 EV -> only `164436`
- minimum collapsed regions 2 -> `164420` + `164436`
- minimum collapsed regions 3 -> only `164436`
- minimum collapsed regions 4 -> none

The preview-bright-fraction dimension is also informative:

- lowering to ~0.15 adds known BOUNDARY `163702`
- current ~0.20 leaves `164436`
- raising to >=0.25 removes `164436`, but this would be threshold retuning to the discovered sample and is not recommended.

## Paired-scene morphology

`164420` and `164436` are consecutive DNGs of the same bright swan / dark background / metal-fence setup in the frozen-render proxy.

| frame | scene spread | bright frac | P75 | center ret | lower ret | upper ret | edge ret | count | canonical |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 164420 | 2.201 | .292 | 6.5 | -.936 | **-1.497** | -2.462 | -2.092 | 2 | HOLD |
| 164436 | 1.724 | .208 | 6.0 | -1.449 | -1.965 | -4.128 | -2.947 | 3 | DARK_ZERO_INTENT |

`164420` misses the -1.50 lower-retention cutoff by only about 0.003 EV. That is not a photographically meaningful distinction.

Both frames have strong LOCALSUBJECTSURVIVAL1A evidence:

- `164420`: local q95 255, local-minus-global q95 +137 Y
- `164436`: local q95 255, local-minus-global q95 +149 Y

## Interpretation

Do not solve this by increasing preview bright-fraction minimum, requiring exactly 4/4 collapsed regions, or moving the -1.50 EV regional cutoff. Those would be small-corpus threshold fitting.

The more defensible architecture is to retain the broad-collapse Branch-B seed, independently detect whether a compact useful subject remains strongly preserved, use that only as a protective veto, and falsify the veto prospectively before modifying canonical BESTFIT1A.

No live lift is authorized.
