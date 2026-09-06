# M9 BESTFIT1A — BRIGHT MIDKEY / BROADOPENING RECON1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, colour science, JPEG quality, or DNG change.

## Purpose

Reconcile the failed prospective `BRIGHT_MIDKEY_NORMALIZATION1A` branch with the later `PLACEMENTOPENING1A` / `BROADOPENING1A` evidence.

The original MIDKEY prospective seed activated four frames in the untouched 47-frame September-5 natural cohort:

```text
173342
173423
173828
181559
```

That activation set was already known to contain false candidates. The new question is whether the four frames actually share the same preview->finished placement behavior.

## Cross-stage result

| frame | preview median -> finished | median proxy | preview q95 -> finished | q95 proxy | BROAD_POSITIVE |
|---|---|---:|---|---:|---|
| 173342 | 198 -> 117 | -0.759 | 213 -> 168 | -0.342 | NO |
| 173423 | 155 -> 81 | -0.936 | 172 -> 134 | -0.360 | NO |
| 173828 | 107 -> 81 | -0.402 | 186 -> 182 | -0.031 | NO |
| **181559** | **66 -> 82** | **+0.313** | **141 -> 161** | **+0.191** | **YES** |

Result:

```text
original MIDKEY activations: 4
BROAD_POSITIVE among them:   1
sole BROAD_POSITIVE:         181559
```

## Interpretation

The original MIDKEY selector grouped together photographs with fundamentally different render behavior.

### 173342 / 173423

Both begin with already-bright preview bodies and become materially denser in the finished JPEG. They are not examples of a scene being normalized too open by the frozen renderer.

### 173828

The frozen JPEG was visually acceptable in isolation and later preferred RGB015 in exact side-by-side review, but its global body and q95 both move slightly downward relative to preview.

This is the clearest demonstration that:

```text
aesthetic preference for more density != placement-opening failure
```

The frame belongs in treatment-response/M9ness research, not as evidence that a BRIGHT placement selector should activate.

### 181559

This is the only original MIDKEY activation where both the global body and upper-body actually move upward. It also independently satisfies `BRIGHT_LOWKEY_OPENING1A` and is the only prospective frame in this set with exact NATURAL_MILD treatment-positive evidence.

Thus its earlier MIDKEY activation was incidental overlap with the more coherent LOWKEY-opening mechanism.

## Consequence for MIDKEY development

The September-5 prospective data no longer provides positive support for promoting the MIDKEY branch as a placement selector.

Historical `190346` and `190429` remain genuine visually treatment-positive BRIGHT_FAIL examples, but they should remain an **unresolved second historical morphology** until a mechanism is found that survives independent prospective falsification.

Do not use `173828` to justify that second branch.

Do not retune the failed MIDKEY scalar thresholds around the September-5 frames.

Current status:

```text
LOWKEY_OPENING       -> active research morphology; promising
BROADOPENING         -> promising corroborating diagnostic
MIDKEY_NORMALIZATION -> prospective branch not supported; defer/retire as selector hypothesis
190346 / 190429      -> unresolved historical BRIGHT morphology anchors
```

## Architectural simplification

For current development, the BRIGHT research path can be simplified to:

```text
Frozen
  -> LOWKEY_OPENING eligibility
  -> BROADOPENING corroboration
  -> HOLD vs NATURAL_MILD
  -> weak RGB-pivot treatment first
  -> response safety / rollback

Historical 190346 / 190429
  -> separate unresolved research track
  -> no live selector
```

This reduces the risk of forcing a second branch merely to improve recall.

## Next step

Continue mining existing natural/control data for `BROAD_POSITIVE` GOOD frames.

If BROAD_POSITIVE remains rare and concentrated in genuinely opened scenes, it can become a stronger veto/corroboration layer for LOWKEY research. It still must not become treatment authority from the current evidence alone.
