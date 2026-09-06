# M9 BESTFIT1A — BRIGHT BROADOPENING1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, colour science, JPEG quality, or DNG change.

## Purpose

Continue `PLACEMENTOPENING1A` by asking whether a BRIGHT low-key opening should be visible across more than one global tonal statistic.

The new diagnostic pair is:

```text
medianOpeningEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95OpeningEv    = log2(finishedGlobalQ95Y    / previewGlobalQ95Y)
```

and a deliberately conservative summary diagnostic:

```text
broadOpeningMinProxyEv = min(medianOpeningEv, q95OpeningEv)
```

This is **not** exposure EV and is **not** production authority. Preview Y and finished BT.601 Y are different pipeline spaces.

The purpose of the minimum is only to ask whether both the useful body and upper-body moved in the same opening direction. It prevents one locally redistributed statistic from masquerading as broad opening.

## September-4 Part-3 same-build regression

All 29 complete metadata pairs in `again again part 3.zip` were audited.

Sign counts:

```text
global median positive:       0 / 29
q95 positive:                 2 / 29
q99 positive:                 8 / 29
center median positive:       3 / 29
median AND q95 positive:      0 / 29
```

This immediately establishes two safety points.

### q99 is too unstable for authority

8/29 same-build controls have positive q99 movement despite no positive global-median opening. The extreme upper tail is therefore strongly affected by highlight redistribution/anchoring and should remain diagnostic only.

### centre opening is unsafe for severity or eligibility

3/29 controls have positive centre-median movement while the global body remains denser.

The labeled GOOD controls include:

- `164510`: global median 93 -> 92 (~-0.016), q95 220 -> 222 (~+0.013), centre movement ~+0.436;
- `164525`: global ~-0.468, centre ~+0.027;
- `164814`: global ~-0.517, centre ~+0.127.

Therefore `centerMedianOpeningProxyEv > 0` would create GOOD false evidence and must not become a selector or severity axis.

`164510` is especially useful: it is essentially globally neutral while the centre opens materially. This is tonal redistribution, not a globally opened BRIGHT failure.

## q95-only positive controls

Only two Part-3 frames have positive q95 movement:

```text
164510 GOOD:     global median ~-0.016, q95 ~+0.013
164622 BOUNDARY: global median ~-2.387, q95 ~+0.048
```

Neither is broad-positive because the global median remains non-positive.

Thus q95 positivity alone is also not enough.

## Prospective ordering

### 173828 — Frozen acceptable / mild aesthetic preference only

```text
preview median 107 -> finished 81  ~= -0.402
preview q95    186 -> finished 182 ~= -0.031
broad minimum                     ~= -0.402
structuralLowKeyScore              = 0
```

Both global statistics retain/darken placement. The later preference for RGB015 is therefore aesthetic/treatment-response evidence, not evidence of a BRIGHT opening mechanism.

### 181404 — BOUNDARY_HOLD

```text
preview median 78 -> finished 82   ~= +0.072
preview q95    192 -> finished 196 ~= +0.030
broad minimum                      ~= +0.030
preview centre median 69 -> finished 109 ~= +0.659
```

The centre opens dramatically even though the global broad-opening evidence is only slight. This is direct prospective evidence that centre movement must not be used as severity authority.

`181404` remains Frozen.

### 181559 — treatment-positive NATURAL_MILD

```text
preview median 66 -> finished 82   ~= +0.313
preview q95    141 -> finished 161 ~= +0.191
broad minimum                      ~= +0.191
preview centre 66 -> finished 100  ~= +0.599
```

Unlike `181404`, both global body and q95 show materially positive movement.

The exact mild-bank review preferred the RGB015/RGB025 region, while Frozen remained close. This remains a NATURAL_MILD example, not a severe BRIGHT correction authority.

## Current ordering

Across the directly checked evidence:

```text
Part-3 labeled GOOD max broad minimum: ~-0.016
173828 acceptable Frozen:              ~-0.402
181404 BOUNDARY_HOLD:                   ~+0.030
181559 NATURAL_MILD positive:           ~+0.191
```

This ordering is photographically coherent, but it must **not** be converted into a numeric threshold from these anchors.

The useful interpretation is categorical:

```text
median <= 0 and q95 <= 0
    -> retained/dense global placement evidence

median <= 0, q95 > 0
    -> upper-tail redistribution; HOLD evidence

median > 0, q95 <= 0
    -> body-only opening; unresolved, HOLD

median > 0 and q95 > 0
    -> BROAD_POSITIVE mechanism evidence
       magnitude still requires visual severity judgement
```

`BROAD_POSITIVE` is a research evidence class, **not treatment eligibility**.

## Why the minimum diagnostic is useful

`broadOpeningMinProxyEv` expresses the weakest of the two global opening signals. It therefore ranks:

- broad opening more strongly when both body and upper-body move upward;
- slight boundary opening near zero;
- mixed redistribution below zero even if one statistic rises.

It is safer than centre movement and safer than q99 movement in the current same-build regression.

## Updated architecture

```text
Frozen render
  -> existing LOWKEY morphology / intent / TC20 / finished-body gate
  -> PLACEMENTOPENING diagnostics
       -> global median
       -> global q95
       -> BROADOPENING sign class
  -> if not BROAD_POSITIVE: HOLD / Frozen
  -> if BROAD_POSITIVE: visual severity validation still required
       -> mild treatment bank only when visually justified
  -> response safety
  -> Frozen rollback
```

This is deliberately more conservative than promoting `proxy > 0` from the median alone.

## Next retrospective falsification

Before new shooting:

1. run the updated retrospective auditor over every available September-5 pair;
2. rank all `BROAD_POSITIVE` frames, not just existing LOWKEY activations;
3. visually inspect any GOOD-looking broad-positive frame first;
4. if broad-positive ordinary GOOD frames are common, reject this mechanism as authority;
5. if broad-positive remains rare and concentrated in visually opened cases, retain it as a corroborating BRIGHT diagnostic;
6. do not use centre or q99 opening as authority.

Priority remains zero GOOD false correction and preservation of the frozen M9 rendering.
