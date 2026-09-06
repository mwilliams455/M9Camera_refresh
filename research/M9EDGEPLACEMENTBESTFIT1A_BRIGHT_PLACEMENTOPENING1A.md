# M9 BESTFIT1A — BRIGHT PLACEMENTOPENING1A

Research-only diagnostic hypothesis. No live APK, capture, TC20, renderer, curve02, color science, JPEG quality, or DNG change.

## Purpose

Test whether BRIGHT low-key failures are better described by the finished JPEG being opened relative to the preview body than by an isolated structural-score threshold.

The diagnostics are:

```text
finishedVsPreviewMedianProxyEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
finishedVsPreviewQ95ProxyEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)
```

These are **cross-pipeline placement proxies only**. Preview Y and finished BT.601 Y are not the same photometric stage. Do not interpret the values as capture EV and do not use them as live authority.

## Exact prospective anchors

### 181559 — LOWKEY activation, mild treatment-positive

- preview median 66
- finished median 82
- median placement proxy ~+0.313 EV
- preview q95 141
- finished q95 161
- q95 placement proxy ~+0.191 EV
- exact mild-bank preference: RGB015 / RGB025

### 181404 — LOWKEY boundary/HOLD

- preview median 78
- finished median 82
- median placement proxy ~+0.072 EV
- preview q95 192
- finished q95 196
- q95 placement proxy ~+0.030 EV
- structuralLowKeyScore ~0.545

It remains Frozen. Do not lower the 0.60 structural floor around this frame.

### 173828 — Frozen acceptable / side-by-side mild-density preference

- preview median 107
- finished median 81
- median placement proxy ~-0.402 EV
- structuralLowKeyScore = 0

This demonstrates that side-by-side preference for a slightly denser image does not itself imply a BRIGHT placement failure.

## 2026-09-05 retrospective natural-cohort audit

The full 47-frame untouched late-afternoon cohort contains 12 frames with `structuralLowKeyScore >= 0.60`. Their global-median opening proxies are:

| frame | preview median | finished median | opening proxy |
|---|---:|---:|---:|
| 173159 | 68 | 41 | -0.730 EV |
| 174327 | 66 | 39 | -0.759 EV |
| 174410 | 64 | 7 | -3.193 EV |
| 174524 | 66 | 7 | -3.237 EV |
| 175630 | 57 | 6 | -3.248 EV |
| 181125 | 57 | 6 | -3.248 EV |
| 181247 | 64 | 17 | -1.913 EV |
| 181300 | 63 | 13 | -2.277 EV |
| 181423 | 69 | 17 | -2.021 EV |
| 181527 | 54 | 2 | -4.755 EV |
| **181559** | **66** | **82** | **+0.313 EV** |
| 181623 | 60 | 14 | -2.100 EV |

### Result

Among all 12 structurally-qualified natural frames:

- `181559` is the **only positive global-median opening**;
- all 11 controls are negative;
- several controls have equal/higher structural scores and/or larger TC20 gains but retain substantially denser finished placement.

This makes `PLACEMENTOPENING1A` a serious secondary mechanism diagnostic rather than a two-frame curiosity.

The especially useful control is `174327`: structuralLowKeyScore ~0.876 (essentially identical to `181559`) and TC20 gain ~4.32x, yet preview 66 -> finished 39 (~-0.759 EV proxy). Score and gain therefore do not imply opening.

## Independent morning controls

### 085126 — high-score/high-gain OFF control

- structuralLowKeyScore ~0.9967
- TC20 gain ~2.052
- preview median 51
- finished median 24
- opening proxy ~-1.087 EV

### 084858 — visually GOOD extreme-dark control

- preview median 50
- finished median 14
- opening proxy ~-1.837 EV

Both reinforce that coherent low-key structure can remain intentionally dense and must not be corrected merely because it is dark.

## Retained hard negatives

### 182756 — high-key split-field

- preview median ~85
- finished median ~83
- median placement proxy ~-0.034 EV
- LOWKEY OFF

### 182012 — clipped-but-dark

- preview median ~36
- finished median ~2
- median placement proxy ~-4.17 EV
- LOWKEY OFF

## Interpretation

The useful photographic question is increasingly:

```text
Did the frozen renderer actually open a coherent low-key body relative to its preview placement?
```

rather than:

```text
Is the scene dark?
Is TC20 gain high?
Is structuralLowKeyScore above one scalar floor?
```

Current evidence supports the *direction* of the diagnostic strongly within the natural low-key subset:

```text
retained/dense controls -> negative opening proxy
181404 boundary         -> slight positive proxy
181559 treatment-positive -> materially positive proxy
```

However, no numeric opening threshold is promoted because:

1. preview and finished luma are different pipeline spaces;
2. `181404` is a legitimate slightly-positive boundary/HOLD case;
3. only one prospective treatment-positive LOWKEY activation has exact visual treatment validation;
4. historical severe LOWKEY BRIGHT_FAIL anchors do not currently retain enough directly paired preview/finished telemetry for equivalent validation.

## Development use

Existing LOWKEY authority remains unchanged:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

The research-only boundary overlay also remains:

```text
base intent/gain/body passes
AND 0.50 <= structuralLowKeyScore < 0.60
-> BOUNDARY_HOLD / Frozen
```

`PLACEMENTOPENING1A` is recorded alongside those states and used for falsification/ranking, not live authority.

The reusable retrospective tool is:

```text
research/m9edgeplacementbestfit1a_bright_placementopening_retroaudit1a.py
```

It can join `m9edgeplacement1a_labels_seed.csv`, ranks labeled GOOD/BOUNDARY positive-opening cases first, and emits median/q95/q99/centre placement proxies.

## Next work order

Do **not** request new shooting before exhausting the existing 2026-09-05 paired data.

1. run the retrospective auditor across every available paired sidecar;
2. join existing visual GOOD / BOUNDARY / failure labels where identities are known;
3. inspect any labeled GOOD frame with materially positive opening as the highest-priority falsifier;
4. preserve `181404` as Frozen boundary evidence;
5. keep the second BRIGHT morphology (`190346` / `190429`) separate from LOWKEY;
6. only after retrospective evidence is exhausted decide whether a new capture batch is necessary.

Priority remains zero GOOD false corrections and preservation of normal M9 rendering.
