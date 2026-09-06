# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_BROADOPENING FULL47 1A

Research-only prospective falsification audit. No live APK, capture, TC20, curve, color, JPEG-quality, or DNG change.

## Cohort

Untouched September-5 natural-shooting cohort:

- 47 photographs
- normal photographic use, not captured to satisfy `BRIGHT_BROADOPENING1A`
- JPEG + DNG + capture/PRIMARY diagnostics
- later than the historical BRIGHT derivation set

This is the same 47-frame prospective cohort previously used to falsify the original `BRIGHT_MIDKEY_NORMALIZATION1A` seed.

## Diagnostic under test

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BROAD_POSITIVE = medianShiftEv > 0 AND q95ShiftEv > 0
```

No magnitude threshold is applied. Sign agreement only.

## Result

```text
47 total frames
 2 BROAD_POSITIVE
45 BROAD_OFF
```

The two positives are:

| frame | median shift | q95 shift | broad min | existing visual/treatment classification |
|---|---:|---:|---:|---|
| 181404 | +0.072 EV | +0.030 EV | +0.030 EV | BOUNDARY_HOLD / Frozen acceptable |
| 181559 | +0.313 EV | +0.191 EV | +0.191 EV | NATURAL_MILD / mild RGB-pivot treatment-positive |

This is important because the diagnostic did not simply rediscover every dark-preview or high-TC20 scene. It isolated the two known prospective frames where the finished response genuinely opens both the body and upper-body.

## Failed MIDKEY activations

The four frames that activated the original prospective MIDKEY seed divide as follows:

| frame | median shift | q95 shift | BROADOPENING |
|---|---:|---:|---|
| 173342 | -0.759 EV | -0.342 EV | OFF |
| 173423 | -0.936 EV | -0.360 EV | OFF |
| 173828 | -0.402 EV | -0.031 EV | OFF |
| 181559 | +0.313 EV | +0.191 EV | ON |

Therefore the original MIDKEY selector grouped four photographs that did not share the same renderer-response behavior. Three become denser; only 181559 broadly opens.

`173828` remains an important distinction: a very mild density variant can be aesthetically preferable without the frame being a placement-failure example. Aesthetic improvement must not be promoted into failure detection.

## Ordinary near-miss checks

Representative OFF frames show why the two-sign conjunction matters:

- 173028: median 137 -> 85, q95 186 -> 162 — both denser
- 173100: median 137 -> 89 but q95 207 -> 221 — upper-tail redistribution, not broad opening
- 173208: median 144 -> 92, q95 206 -> 180 — both denser
- 175115: median 93 -> 81, q95 200 -> 188 — both denser
- 175307: median 112 -> 82, q95 203 -> 180 — both denser
- 175833: median 130 -> 87, q95 166 -> 139 — both denser
- 181138: median 59 -> 10 while q95 224 -> 248 — strong body densification with upper-tail redistribution
- 182032: median 66 -> 13, q95 255 -> 226 — both denser
- 182039: median 66 -> 14 while q95 225 -> 233 — body densification with upper-tail redistribution

Positive q95 alone is therefore not sufficient. Positive center movement is also deliberately non-authoritative because GOOD/HOLD frames can open locally while global body density is retained or increased.

## Independent control evidence already accumulated

The sign-conjunction has not shown broad leakage in the two independent control groups audited before this full47 closure:

```text
September-4 Part-3 control set : 0 / 29 BROAD_POSITIVE
September-5 morning controls   : 0 / 13 BROAD_POSITIVE
September-5 natural full47     : 2 / 47 BROAD_POSITIVE
```

This does not make it production-ready. It does make BROADOPENING a materially stronger renderer-response descriptor than preview median, finished median, q95 alone, center movement, or the failed MIDKEY seed.

## What 181404 proves

`181404` is the required HOLD counterexample:

```text
genuine broad opening
    !=
mandatory correction
```

Its response is positive but small and Frozen remains photographically acceptable. Therefore any future architecture needs a separate photographic-severity/HOLD stage after mechanism corroboration.

Do not create a cutoff between +0.030 and +0.191 EV from this pair. That would be two-point overfit.

## Current interpretation

```text
LOWKEY / BRIGHT structural morphology
        ↓
BROADOPENING response corroboration
        │
        ├─ OFF -> strong retained-density / HOLD evidence
        │
        └─ ON  -> genuine renderer opening
                    ↓
             separate severity / HOLD
                    ↓
          Frozen OR bounded mild RGB pivot
```

The next falsification is historical: replay the confirmed BRIGHT_FAIL treatment anchors and the known Frozen/HOLD negative through the same median+q95 response diagnostic. The objective is not to force every BRIGHT treatment-positive morphology to be BROAD_POSITIVE; it is to determine whether the LOWKEY opening mechanism itself reproduces independently and whether HOLD negatives remain OFF or only weakly positive.

## Status

`BRIGHT_BROADOPENING1A`: **promising research corroborator; not live; no threshold frozen.**

MIDKEY remains failed/deferred. No APK or global renderer/capture change follows from this audit.
