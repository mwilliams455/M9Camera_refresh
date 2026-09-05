# M9EDGEPLACEMENTBESTFIT1A — TREATMENTSWEEP1A 2 PM exact-DNG result

Status: **research only / no live renderer mutation / no selector threshold change**

Date: 2026-09-05

## Purpose

Separate **detection** from **treatment strength** for the three exact 2 PM edge-placement anchors after their original DNGs became available:

- `142840` — `DARK_ZERO_INTENT`, visual DARK_FAIL
- `142939` — `DARK_ZERO_INTENT`, visual DARK_FAIL
- `144210` — `DARK_FOREGROUND`, foreground/boundary failure

The canonical BESTFIT1A selector is unchanged.

## Frozen replay

The replay preserves the frozen photographic path:

- R3.8 / H25
- Cobalt Xiaomi 15 Ultra main DCP
- M9 bridge / HSM
- TC20
- SAT3 M06/M07
- firmware `curve02`
- exact BT.601 4:2:2
- daylight TG1 weight = 0 for these frames

Only one variable was changed: an additional gain immediately before the M9 matrix/curve stage.

Tested treatment values:

`0.00, +0.15, +0.25, +0.35, +0.50 EV`

The TC20 gains reconstructed from the DNGs match the captured PRIMARY telemetry:

- `142840`: `1.05445605`
- `142939`: `1.50586770`
- `144210`: `1.38668189`

The final validation sweep was rendered at the full 4096x3072 source geometry in row blocks to avoid changing the per-pixel color/tone math.

## Full-resolution response

| frame | EV | mean Y | median Y | q95 Y | dark <=64 | bright >=224 |
|---|---:|---:|---:|---:|---:|---:|
| 142840 | 0.00 | 21.55 | 2.36 | 133.23 | 90.54% | 3.392% |
| 142840 | +0.25 | 23.93 | 3.52 | 146.96 | 89.17% | 3.471% |
| 142840 | +0.50 | 26.55 | 4.70 | 160.33 | 87.74% | 3.558% |
| 142939 | 0.00 | 19.82 | 3.53 | 93.31 | 89.00% | 1.045% |
| 142939 | +0.25 | 22.98 | 4.82 | 106.75 | 87.02% | 1.200% |
| 142939 | +0.50 | 26.44 | 6.20 | 120.04 | 85.31% | 1.357% |
| 144210 | 0.00 | 84.92 | 33.73 | 231.92 | 54.49% | 7.187% |
| 144210 | +0.25 | 92.18 | 40.81 | 240.85 | 53.49% | 10.640% |
| 144210 | +0.50 | 99.48 | 48.92 | 248.29 | 52.03% | 13.847% |

## Result 1 — ZERO_INTENT treatment is not constrained by rawHardClipFraction alone

Earlier telemetry-only reasoning suggested that `142840` should necessarily receive a smaller lift than `142939` because its RAW hard-clip fraction is ~1.21% versus ~0.015%.

The exact DNG sweep falsifies that implication.

From 0 to +0.50 EV:

- `142840` bright >=224 rises only ~0.17 percentage points.
- `142939` bright >=224 rises only ~0.31 percentage points.

Both retain substantial visual darkness at +0.50 EV, and +0.50 is the strongest tested treatment without a large new finished-highlight penalty.

Therefore:

> **Do not derive treatment magnitude directly from `rawHardClipFraction`.**

RAW clipping remains useful scene/headroom evidence, but finished-output response is what determines whether additional pre-curve gain is photographically expensive.

### Provisional Branch-B treatment conclusion

For these two confirmed `DARK_ZERO_INTENT` anchors, **+0.50 EV is the best-fit end of the tested range**.

This does **not** freeze +0.50 EV as a universal Branch-B constant. The corpus is still too small and prior visual work showed scene-dependent preferences. It is a branch-treatment seed/cap candidate only.

## Result 2 — FOREGROUND_COLLAPSE needs a weaker treatment

`144210` reacts very differently.

From 0 to +0.50 EV:

- q95 rises from ~231.9 to ~248.3 Y.
- bright >=224 rises from ~7.19% to ~13.85%.

The foreground improves, but the dramatic sky is progressively pushed toward the ceiling. The visual best-fit zone is **+0.25 to +0.35 EV**, with **+0.25 EV the safer provisional seed** for preserving the M9-like highlight structure.

Therefore Branch C should not inherit Branch B's treatment strength.

## Result 3 — selector and treatment remain separate

Current architecture remains:

```text
BESTFIT selector
  -> HOLD
  -> DARK_INTENT
  -> DARK_ZERO_INTENT
  -> DARK_FOREGROUND

then, only for a selected edge case:
  -> branch-specific bounded treatment policy
```

Do not encode treatment magnitude into selector thresholds.

## Current treatment seeds for further falsification

These are **not production constants**:

- `DARK_ZERO_INTENT`: test `+0.50 EV` as the current upper-seed / cap candidate.
- `DARK_FOREGROUND`: test `+0.25 EV` as the current conservative seed, with `+0.35 EV` retained as an alternate.
- `DARK_INTENT`: unresolved by this exact-DNG sweep; do not infer from Branch B or C.

## Important constraint

The deep-black medians of `142840` and `142939` remain very low even at +0.50 EV. This is expected from curve02 and is preferable to introducing a global shadow/black-point modification. The project requirement remains to correct edge cases without changing the frozen M9 tone behavior of normal photographs.

If a frame still needs more rescue than the bounded JPEG correction can provide, Lightroom/DNG recovery remains an acceptable fallback.

## Next falsification

1. Keep canonical BESTFIT1A selector unchanged.
2. Do not add a live treatment yet.
3. Prospectively collect new `DARK_ZERO_INTENT` and `DARK_FOREGROUND` positives.
4. Replay those positives with the branch-specific treatment seeds above.
5. Reject a seed if it harms highlight structure or removes the desired M9 density on a meaningful fraction of genuine positives.
6. Only after prospective validation consider a diagnostic-only treatment recommendation in metadata before any renderer mutation.
