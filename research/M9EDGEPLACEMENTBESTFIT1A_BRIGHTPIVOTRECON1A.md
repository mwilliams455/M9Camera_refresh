# M9 EDGEPLACEMENT BESTFIT1A — BRIGHTPIVOTRECON1A

Research-only. No live APK, TC20, capture policy, curve02, color science, or frozen renderer changes.

## Legacy operator reconstruction

The original M9BESTFIT1A implementation artifact is not currently recoverable. The retained v2.81 handoff preserves enough numerical behavior to reconstruct the tone law with high confidence, but this document does **not** claim the missing original source was recovered.

Retained legacy facts:
- RGB035: lower-tone density up to ~0.35 EV, tapering to zero in upper tones, RGB ratios preserved.
- Y035/Y050: same pivot concept in BT.601 luma, Cb/Cr retained.
- 18:49:27: median 0.371 -> 0.324 (RGB035), 0.325 (Y035), 0.307 (Y050), while centre q95 ~0.851 stays anchored.
- 18:49:37: median 0.366 -> 0.318 / 0.319 / 0.301 while centre q95 ~0.869 stays anchored.

Those numbers are reproduced closely by the monotonic law:

```text
pivot = 0.85
w(Y) = clamp(1 - Y/pivot, 0, 1)
EV(Y) = -strength * w(Y)
scale(Y) = 2^EV(Y)
```

For Y=0.371 this predicts RGB035 ~=0.324. For Y=0.366 it predicts ~=0.319. Values at/above 0.85 are unchanged.

This is therefore labelled **reconstructed legacy behavior**, not exact recovered source.

## Full-12 MP hard-negative operator comparison

Columns: median Y | q95 Y | centre q95 Y | <=64 Y | >=224 Y | RGB endpoint occupancy

### 18:27:56 — high-key split-field boundary

| Variant | median | q95 | center q95 | <=64 | >=224 | endpoint |
|---|---:|---:|---:|---:|---:|---:|
| FROZEN | 83 | 236 | 249 | 42.37% | 8.22% | 2.69% |
| PRE035 | 66 | 223 | 239 | 49.32% | 4.85% | 2.71% |
| PRE050 | 60 | 216 | 233 | 51.82% | 3.81% | 2.85% |
| RGB035 | 72 | 236 | 249 | 47.12% | 8.22% | 2.69% |
| Y035 | 71 | 236 | 249 | 47.25% | 8.02% | 3.79% |
| Y050 | 67 | 236 | 249 | 49.16% | 8.02% | 4.33% |

Interpretation:
- Plain PRE035/PRE050 darkens the upper anchor: q95 and centre q95 fall materially.
- RGB035 restores lower/mid density while q95 and centre q95 remain exactly at the Frozen values in this replay.
- Y035/Y050 also preserve the upper anchor but increase RGB endpoint occupancy, consistent with luma-only movement pushing preserved chroma toward gamut boundaries.

### 18:20:12 — clipped-but-already-dark hard negative

| Variant | median | q95 | center q95 | <=64 | >=224 | endpoint |
|---|---:|---:|---:|---:|---:|---:|
| FROZEN | 2 | 245 | 255 | 81.06% | 10.11% | 45.25% |
| PRE035 | 1 | 233 | 252 | 81.91% | 7.21% | 48.77% |
| PRE050 | 1 | 227 | 248 | 82.26% | 5.83% | 51.21% |
| RGB035 | 1 | 245 | 255 | 81.70% | 10.11% | 45.22% |
| Y035 | 2 | 244 | 255 | 81.71% | 9.99% | 52.24% |
| Y050 | 1 | 244 | 255 | 81.97% | 9.99% | 53.44% |

Interpretation:
- No negative treatment is photographically justified for this frame; BRIGHT_LOWKEY_OPENING1A correctly rejects it.
- If misactivated, pivoting is less destructive to the upper anchor than plain PRE.
- RGB035 creates less new lower-body loss than PRE035 and keeps endpoint occupancy effectively at baseline.
- Y035/Y050 preserve q95 but materially increase endpoint occupancy, making them weaker safety candidates for a production exception path.

## Current operator conclusion

For BRIGHT-tail research, **RGB-ratio-preserving pivoted density is now the preferred operator family to test first**, not plain negative pre-curve EV and not Y-only/CbCr-preserving density.

This is not yet a production choice because these two frames are hard negatives, not confirmed BRIGHT_FAIL positives, and the retained historical blind review explicitly found no universal winner. Direct replay of confirmed BRIGHT_FAIL DNGs is still required before promotion.

## Architecture

```text
Frozen render
   -> conservative BRIGHT subtype eligibility
   -> RGB pivoted density candidate
   -> lower-body preservation / endpoint safety veto
   -> bounded strength, absolute research floor no lower than -0.75 EV
   -> publish candidate or fall back to Frozen
```

The BRIGHT and DARK treatment operators remain intentionally asymmetric.
