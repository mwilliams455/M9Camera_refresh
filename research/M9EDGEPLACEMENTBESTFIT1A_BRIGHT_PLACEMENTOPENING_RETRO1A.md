# M9 BESTFIT1A — BRIGHT PLACEMENTOPENING RETRO1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG change.

## Correction to development plan

A new capture batch is **not** the first next step. The 2026-09-05 data already contains substantial natural/control evidence for the exact low-key-opening question:

- 47-frame untouched late-afternoon natural cohort;
- 13-frame morning cross-cohort hard-negative set;
- additional visually reviewed GOOD / BOUNDARY / hard-negative anchors.

This note mines that existing evidence before requesting further shooting.

`PLACEMENTOPENING1A` remains a cross-pipeline diagnostic only:

```text
globalMedianOpeningProxyEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
```

Preview Y and finished BT.601 Y are different pipeline spaces. The value is **not capture EV** and has no live authority.

## Complete score-qualified late-afternoon subset

The 47-frame natural cohort contains 12 frames with `structuralLowKeyScore >= 0.60`. Their preview and finished global medians are now paired:

| frame | score | TC20 gain | preview median | finished median | median opening proxy |
|---|---:|---:|---:|---:|---:|
| 173159 | ~0.6017 | ~2.4038 | 68 | 41 | -0.730 EV |
| 174327 | ~0.8761 | ~4.3178 | 66 | 39 | -0.759 EV |
| 174410 | ~0.9145 | ~1.4235 | 64 | 7 | -3.193 EV |
| 174524 | ~0.8758 | ~1.4461 | 66 | 7 | -3.237 EV |
| 175630 | ~0.9586 | ~1.0872 | 57 | 6 | -3.248 EV |
| 181125 | ~0.9163 | ~1.0134 | 57 | 6 | -3.248 EV |
| 181247 | ~0.9145 | ~1.5844 | 64 | 17 | -1.913 EV |
| 181300 | ~0.9314 | ~1.3825 | 63 | 13 | -2.277 EV |
| 181423 | ~0.8087 | ~1.4461 | 69 | 17 | -2.021 EV |
| 181527 | ~0.8234 | ~1.1192 | 54 | 2 | -4.755 EV |
| **181559** | **~0.8761** | **~2.0633** | **66** | **82** | **+0.313 EV** |
| 181623 | ~0.9720 | ~1.5415 | 60 | 14 | -2.100 EV |

### Result

Within the entire structurally-qualified natural subset:

- `181559` is the **only frame with positive global-median opening**;
- the other 11 are all negative;
- the nearest negative controls are still approximately -0.73 / -0.76 EV;
- several controls have higher structural scores and/or larger TC20 gains than `181559` but remain dense.

This sharply supports the semantic distinction:

```text
coherent low-key structure alone != BRIGHT opening
TC20 gain alone                  != BRIGHT opening
finished body >= 75 alone        != complete mechanism description
actual positive preview->finished body movement is a useful additional diagnostic
```

It also explains why `174327` is such a strong control: its score (~0.876) essentially matches `181559`, and its TC20 gain (~4.32x) is more than twice as large, yet its useful body moves **down**, 66 -> 39, rather than opening.

## Independent morning challenge

`085126` is the strongest morning score/gain challenge:

```text
structuralLowKeyScore ~= 0.9967
TC20 gain             ~= 2.052
preview median         = 51
finished median        = 24
opening proxy          ~= -1.087 EV
```

It therefore remains a decisive negative against deriving BRIGHT eligibility from low-key score or TC20 gain alone.

The visually GOOD extreme-dark `084858` similarly moves:

```text
preview median   50
finished median  14
opening proxy    ~= -1.837 EV
```

Dense M9 rendering is retained rather than normalized upward.

## Boundary / preference controls

### 181404 — BOUNDARY_HOLD

```text
preview median   78
finished median  82
opening proxy    ~= +0.072 EV
score            ~= 0.5448
TC20 gain        ~= 2.554
```

This is slight positive movement, not the ~+0.31 movement of `181559`. It remains Frozen. Do not lower the 0.60 score floor around it.

### 173828 — Frozen acceptable, side-by-side RGB015 preference only

```text
preview median   107
finished median  81
opening proxy    ~= -0.402 EV
score            = 0
```

This is important because it demonstrates that an aesthetic preference for a little extra density does not imply the renderer opened the scene or that BRIGHT correction should activate.

## Existing hard negatives

Retained hard-negative movement remains consistent with the same direction:

```text
182756 high-key split field: 85 -> 83  ~= -0.034 EV
182012 clipped-but-dark:      36 -> 2   ~= -4.170 EV
```

Neither is a BRIGHT low-key opening case.

## What is now supported

The current evidence is stronger than the earlier two-frame comparison. For the natural low-key subset actually most relevant to `LOWKEY_OPENING1A`, there is a clean retrospective separation:

```text
11 structurally-qualified controls: global median opening proxy < 0
181559 treatment-positive candidate: global median opening proxy > 0
```

This is **not** enough to freeze `proxy > 0` as a production threshold. Reasons:

1. preview and finished luma are different pipeline spaces;
2. `181404` shows a slightly positive boundary value;
3. historical confirmed LOWKEY BRIGHT_FAIL anchors do not currently retain enough directly paired preview/finished telemetry for equivalent validation;
4. selection must remain visual-first and zero-GOOD-false-correction biased.

But it is enough to promote `PLACEMENTOPENING1A` from a two-frame curiosity to a serious **secondary mechanism diagnostic**.

## Development architecture after RETRO1A

Keep the existing LOWKEY seed unchanged, but record opening alongside it:

```text
Frozen render
  -> structural LOWKEY morphology
  -> TC20 / finished-body context
  -> PLACEMENTOPENING1A diagnostic
       negative -> retained/dense placement evidence
       slight positive -> boundary / HOLD evidence
       clearly positive -> opened-body evidence
  -> visual treatment validation
  -> NATURAL_MILD: RGB015 first, RGB025 escalation-only
  -> finished-response safety
  -> Frozen rollback
```

No numeric positive-opening threshold is frozen here.

## Next retrospective work

Before requesting a new natural batch:

1. run `m9edgeplacementbestfit1a_bright_placementopening_retroaudit1a.py` over every available paired 2026-09-05 sidecar;
2. join existing visual labels where possible;
3. rank labeled GOOD and BOUNDARY frames by positive opening proxy first;
4. inspect any GOOD frame with materially positive opening as a direct falsifier;
5. separately retain the historical severe BRIGHT bank; do not force `190346/190429` into LOWKEY;
6. only after existing-data exhaustion decide whether another capture batch is needed.

Priority remains under-intervention and preservation of the already-successful frozen M9 rendering.
