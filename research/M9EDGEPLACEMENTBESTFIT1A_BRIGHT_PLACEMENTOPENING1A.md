# M9 BESTFIT1A — BRIGHT PLACEMENTOPENING1A

Research-only diagnostic hypothesis. No live APK, capture, TC20, renderer, curve02, color science, JPEG quality, or DNG change.

## Purpose

Test whether BRIGHT low-key failures are better described by the finished JPEG being opened relative to the preview body than by an isolated structural-score threshold.

The diagnostic is:

```text
finishedVsPreviewMedianProxyEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
finishedVsPreviewQ95ProxyEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)
```

These are **cross-pipeline placement proxies only**. Preview Y and finished BT.601 Y are not the same photometric stage. Do not interpret the values as capture EV and do not use them as live authority.

## Current observations

### 181559 — sole prospective LOWKEY activation, mild treatment-positive

- preview median 66
- finished median 82
- median placement proxy ~+0.313 EV
- preview q95 141
- finished q95 161
- q95 placement proxy ~+0.191 EV

This frame visibly tolerated / preferred mild additional density (RGB015–RGB025) in exact blind review.

### 181404 — LOWKEY boundary/HOLD

- preview median 78
- finished median 82
- median placement proxy ~+0.072 EV
- preview q95 192
- finished q95 196
- q95 placement proxy ~+0.030 EV

This frame satisfies intent/gain/body requirements but has structuralLowKeyScore ~0.545. It remains Frozen pending visual classification.

### 182756 — high-key split-field hard negative

- preview median ~85
- finished median ~83
- median placement proxy ~-0.034 EV
- LOWKEY OFF

### 182012 — clipped-but-dark hard negative

- preview median ~36
- finished median ~2
- median placement proxy ~-4.17 EV
- LOWKEY OFF

## Interpretation

The current prospective evidence suggests a useful question:

```text
Did the frozen render actually open the useful body relative to the captured preview placement?
```

That question is closer to the photographic failure mechanism than:

```text
Is structuralLowKeyScore above one scalar floor?
```

However, the evidence is not sufficient to promote a proxy threshold because:

1. preview and finished luma are different pipeline spaces;
2. only one prospective LOWKEY activation is confirmed treatment-positive;
3. historical LOWKEY-positive anchors do not currently retain enough comparable preview/finished scalar detail for a clean retrospective validation;
4. 181404 is still visually unresolved.

## Development use

For future natural cohorts, record the placement proxies for every frame but keep existing LOWKEY authority unchanged.

Desired falsification:

- treatment-positive LOWKEY activations should repeatedly show positive body-opening proxy;
- GOOD/HOLD controls should cluster near zero or negative;
- any ordinary GOOD frame with a strong positive proxy is a direct falsifier of proxy authority.

Do not choose a threshold from 181559 vs 181404. Collect first.

Priority remains zero GOOD false corrections and preservation of normal M9 rendering.
