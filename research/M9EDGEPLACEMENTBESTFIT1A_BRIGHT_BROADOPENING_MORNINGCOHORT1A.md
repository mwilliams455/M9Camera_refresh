# M9 BESTFIT1A — BRIGHT BROADOPENING MORNINGCOHORT1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, colour science, JPEG quality, or DNG change.

## Purpose

Close the full 13-frame 2026-09-05 morning control set against `BROADOPENING1A`.

This is an independent cross-cohort falsification set: the frames were collected earlier on September 5 and were not selected because of the later preview->finished opening hypothesis.

The diagnostic remains:

```text
medianOpeningEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95OpeningEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BROAD_POSITIVE = medianOpeningEv > 0 AND q95OpeningEv > 0
```

These are cross-pipeline placement proxies, not exposure EV and not treatment authority.

## Complete morning result

| frame | preview median -> finished | median proxy | preview q95 -> finished | q95 proxy | sign class |
|---|---|---:|---|---:|---|
| 084712 | 136 -> 74 | -0.878 | 208 -> 196 | -0.086 | RETAINED_OR_DENSER |
| 084858 | 50 -> 14 | -1.837 | 204 -> 151 | -0.434 | RETAINED_OR_DENSER |
| 085011 | 66 -> 69 | +0.064 | 199 -> 198 | -0.007 | BODY_POSITIVE_UPPER_NONPOSITIVE |
| 085126 | 51 -> 24 | -1.087 | 189 -> 217 | +0.199 | UPPER_POSITIVE_BODY_NONPOSITIVE |
| 085303 | 74 -> 12 | -2.624 | 199 -> 178 | -0.161 | RETAINED_OR_DENSER |
| 085321 | 116 -> 28 | -2.051 | 228 -> 198 | -0.204 | RETAINED_OR_DENSER |
| 085339 | 89 -> 58 | -0.618 | 192 -> 194 | +0.015 | UPPER_POSITIVE_BODY_NONPOSITIVE |
| 085353 | 109 -> 46 | -1.245 | 213 -> 203 | -0.069 | RETAINED_OR_DENSER |
| 085742 | 110 -> 67 | -0.715 | 201 -> 186 | -0.112 | RETAINED_OR_DENSER |
| 085848 | 113 -> 77 | -0.553 | 213 -> 211 | -0.014 | RETAINED_OR_DENSER |
| 085955 | 124 -> 35 | -1.825 | 200 -> 174 | -0.201 | RETAINED_OR_DENSER |
| 090211 | 98 -> 78 | -0.329 | 210 -> 201 | -0.063 | RETAINED_OR_DENSER |
| 090359 | 128 -> 91 | -0.492 | 201 -> 167 | -0.267 | RETAINED_OR_DENSER |

Summary:

```text
BROAD_POSITIVE:                       0 / 13
BODY_POSITIVE_UPPER_NONPOSITIVE:     1 / 13
UPPER_POSITIVE_BODY_NONPOSITIVE:     2 / 13
RETAINED_OR_DENSER:                 10 / 13
```

## Key falsification: median sign alone is unsafe

`085011` is the clean new counterexample:

```text
preview median   66
finished median  69
median proxy     +0.064
preview q95      199
finished q95     198
q95 proxy        -0.007
```

A rule using `globalMedianOpeningProxyEv > 0` alone would call this an opening case even though the upper-body does not corroborate it.

The movement is small and mixed. `BROADOPENING1A` correctly classifies it as `BODY_POSITIVE_UPPER_NONPOSITIVE`, not `BROAD_POSITIVE`.

This materially strengthens the reason for requiring sign agreement across median and q95 before calling the renderer broadly opened.

## Independent q95-only falsifiers

### 085126

This is the strongest structural LOWKEY morning challenge:

```text
structuralLowKeyScore ~0.9967
TC20 gain             ~2.052x
preview median        51 -> 24   ~= -1.087
preview q95           189 -> 217 ~= +0.199
```

The upper tail opens strongly while the useful body becomes much denser. q95 alone would therefore misclassify this frame.

### 085339

```text
median 89 -> 58   ~= -0.618
q95   192 -> 194  ~= +0.015
```

Again, a tiny q95 rise occurs while the body becomes materially denser.

These independently reinforce the Part-3 `164510` / `164622` and late-afternoon `173100` evidence that q95 positivity is not authority by itself.

## 085955 metadata recovery

The standalone `_M9_PRIMARY.json` was absent from the Dropbox research copy, but the exact staged PRIMARY payload survives inside:

```text
M9_DIAGNOSTICS_BURST_1788595199669_2.json
role = primary_timing
publicFilename = IMG_20260905_085955_1788595195624_00_M9_PRIMARY.json
```

No image reconstruction or approximation was used. The recovered exact payload reports finished global median 35 and q95 174.

The retrospective auditor has therefore been upgraded to recover missing standalone PRIMARY sidecars from exact diagnostic-bundle payloads before declaring a frame unpaired.

## Relationship to existing evidence

The morning set now adds a genuinely independent result:

```text
September-4 Part-3 complete pairs:       0 / 29 BROAD_POSITIVE
September-5 morning controls:            0 / 13 BROAD_POSITIVE
September-5 BRIGHT near-miss set:        1 / 7  BROAD_POSITIVE = 181404 HOLD
prospective NATURAL_MILD 181559:          BROAD_POSITIVE
```

These are overlapping research purposes, not one random sample. Do not combine the fractions into a population false-positive estimate.

The important falsification fact is simpler:

- neither the independent Part-3 set nor the independent morning set produces a broad-positive control;
- single-statistic positive movements *do* occur in both directions;
- the median+q95 conjunction rejects those mixed redistributions;
- `181404` still proves `BROAD_POSITIVE != automatic treatment`;
- `181559` remains the only exact prospective treatment-positive natural LOWKEY example and has materially stronger broad-positive movement.

## Development consequence

`BROADOPENING1A` has now survived enough independent existing-data pressure to retain it as the leading **corroborating mechanism diagnostic** for BRIGHT LOWKEY research.

It should still not become live treatment authority.

Current interpretation:

```text
median<=0 and q95<=0
    -> retained/dense evidence

median>0 xor q95>0
    -> mixed redistribution / HOLD evidence

median>0 and q95>0
    -> broad-opening mechanism evidence
       -> still requires morphology + HOLD/severity judgement
```

No numeric minimum threshold is frozen.

## Next research step

The next existing-data task is to audit all remaining September-5 late-afternoon frames for `BROAD_POSITIVE`, not just LOWKEY-qualified or MIDKEY-neighborhood subsets.

Any visually ordinary/GOOD broad-positive frame is now the highest-value falsifier.

Only after that full-cohort broad-positive inventory is closed should a new shooting batch be considered.
