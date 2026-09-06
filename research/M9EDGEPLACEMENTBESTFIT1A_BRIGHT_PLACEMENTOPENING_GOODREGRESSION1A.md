# M9 BESTFIT1A — BRIGHT PLACEMENTOPENING GOODREGRESSION1A

Research-only. No live APK, capture, TC20, renderer, JPEG, DNG, curve02, or color change.

## Purpose

Challenge the `PLACEMENTOPENING1A` direction against an independent, already visually labeled control set rather than relying only on the September-5 LOWKEY cohort.

Source: locally retained September-4 Part-3 same-build metadata pairs (`again again part 3.zip`) joined to existing `m9edgeplacement1a_labels_seed.csv` visual labels.

The proxy remains:

```text
globalMedianOpeningProxyEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
```

This is a cross-pipeline placement proxy, not exposure EV.

## Labeled GOOD controls

| frame | preview median | finished median | opening proxy | structuralLowKeyScore | TC20 gain |
|---|---:|---:|---:|---:|---:|
| 164510 | 93 | 92 | -0.016 | 0.000 | 2.534 |
| 164525 | 83 | 60 | -0.468 | 0.000 | 3.961 |
| 164814 | 73 | 51 | -0.517 | 0.405 | 3.615 |
| 164707 | 93 | 48 | -0.954 | 0.000 | 1.601 |
| 164736 | 91 | 34 | -1.420 | ~0.000006 | 1.557 |
| 163553 | 72 | 19 | -1.922 | 0.587 | 1.491 |
| 164247 | 93 | 22 | -2.080 | 0.000 | 1.467 |
| 163847 | 63 | 14 | -2.170 | 0.000 | 1.421 |
| 164331 | 45 | 7 | -2.684 | 0.788 | 1.238 |
| 164402 | 60 | 5 | -3.585 | 0.000 | 1.196 |

Result:

```text
10 / 10 labeled GOOD controls have opening proxy <= 0
maximum GOOD proxy = -0.016 EV (164510, effectively neutral)
```

This is useful because the control set includes large TC20 gains and substantial structural-low-key scores:

- `164525`: gain ~3.96x, still negative opening;
- `164814`: score ~0.405, gain ~3.62x, still negative opening;
- `163553`: score ~0.587 (inside the current 0.50-0.60 boundary band) and remains strongly negative;
- `164331`: score ~0.788 yet remains strongly negative.

Thus positive opening is not a generic consequence of either high TC20 gain or high structural-low-key score in these visually accepted frames.

## Labeled BOUNDARY controls

| frame | preview median | finished median | opening proxy |
|---|---:|---:|---:|
| 164622 | 68 | 13 | -2.387 |
| 163702 | 49 | 2 | -4.615 |

Both remain strongly negative. Their ambiguity is therefore DARK-side/placement context, not BRIGHT opening.

## Labeled DARK_FAIL anchor

`164048`:

```text
preview median 99
finished median 5
opening proxy ~-4.307 EV
```

As expected, this lies on the opposite tail and should never enter BRIGHT_LOWKEY treatment merely because its scene contains bright structure.

## Combined interpretation

Current directly checked evidence now includes:

1. all 12 structurally-qualified frames in the September-5 late-afternoon natural cohort;
2. the key September-5 morning low-key controls;
3. 10 visually labeled same-build GOOD Part-3 controls;
4. two labeled Part-3 BOUNDARY controls;
5. the Part-3 DARK_FAIL anchor.

Within those checks, the only clearly treatment-positive natural LOWKEY frame (`181559`) is also the only one with materially positive global-median opening (~+0.313 EV). The September-5 `181404` boundary is only slightly positive (~+0.072 EV), while labeled GOOD controls checked here are neutral/negative.

This strengthens `PLACEMENTOPENING1A` as a **secondary diagnostic/falsification axis**.

It still does not justify a production numeric threshold because preview and finished luma differ in pipeline space and historical severe LOWKEY BRIGHT_FAIL anchors lack directly paired telemetry in the currently mounted corpus.

## Development consequence

Do not change the current LOWKEY selector yet.

Use opening direction to rank evidence:

```text
LOWKEY morphology + negative opening -> strong HOLD / retained-density evidence
LOWKEY morphology + near-zero opening -> HOLD / boundary evidence
LOWKEY morphology + materially positive opening -> BRIGHT mechanism evidence requiring visual confirmation
```

No numeric cut point is frozen by GOODREGRESSION1A.
