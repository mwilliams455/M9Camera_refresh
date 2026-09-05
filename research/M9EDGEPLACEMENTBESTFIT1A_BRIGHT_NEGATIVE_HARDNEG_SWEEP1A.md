# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT NEGATIVE HARD-NEGATIVE SWEEP1A

Research-only. No live APK, capture policy, TC20, curve02, color science, or frozen renderer change.

## Setup

Full-resolution 4096×3072 R3.8/H25 proxy path:

- HSM hue strength 0.25
- corrected CCT sign
- frozen TC20 recomputed on 1600-side camera-domain meter
- SAT3 M06/M07
- firmware curve02
- exact BT.601 4:2:2
- JPEG quality 95

Negative pre-curve sweep: `0 / -0.25 / -0.50 / -0.75 EV`.

These two frames are **hard-negative controls**, not BRIGHT_FAIL labels. The purpose is to measure the damage if a BRIGHT selector fires incorrectly.

## 182756 — high-key / split-field hard negative

TC20:

- base median gain: 1.9394×
- guard gain: 1.8707×
- applied gain: 1.8707×
- RAW hard clip: 0.000763%

| EV | median Y | mean Y | q95 Y | <=64 | >=224 | center median |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 83 | 109.97 | 236 | 42.37% | 8.22% | 102 |
| -0.25 | 71 | 100.59 | 227 | 47.43% | 5.52% | 89 |
| -0.50 | 60 | 91.50 | 216 | 51.82% | 3.81% | 77 |
| -0.75 | 50 | 82.77 | 204 | 55.64% | 1.38% | 65 |

Interpretation:

- `-0.75 EV` remains technically renderable and does not catastrophically clip black to one value.
- However it is photographically aggressive: useful-body density drops substantially and the bright tail is reduced far more than needed for an already plausible high-key scene.
- Therefore `-0.75 EV` can remain only an **absolute research envelope**, never a default BRIGHT treatment.

## 182012 — clipped-but-dark hard negative

TC20:

- base median request: 16.0×
- guard gain: 1.1083×
- applied gain: 1.1083× (guard-limited)
- RAW hard clip: 1.5076%

| EV | median Y | mean Y | q95 Y | <=64 | >=224 | RGB endpoint fraction |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 2 | 42.04 | 245 | 81.06% | 10.11% | 41.21% |
| -0.25 | 1 | 39.45 | 237 | 81.67% | 8.00% | 43.12% |
| -0.50 | 1 | 36.78 | 227 | 82.26% | 5.83% | 48.63% |
| -0.75 | 0 | 34.14 | 216 | 82.84% | 4.09% | 53.26% |

Interpretation:

This is the decisive falsifier for any generic highlight-driven BRIGHT rule.

- The image has an enormous bright tail and meaningful RAW clipping.
- Yet its useful body is already almost completely at the floor.
- Negative pre-curve treatment reduces the highlight tail while increasing endpoint occupancy and collapsing the lower body further.
- `-0.75 EV` is clearly unacceptable here.

Therefore:

> High q95, bright-pixel fraction, RAW clipping, or TC20 guard binding must never independently authorize BRIGHT correction.

## Architecture consequence

The negative side now needs two independent decisions:

```text
BRIGHT eligibility morphology
    -> e.g. BRIGHT_LOWKEY_OPENING1A
    -> proposed negative treatment
    -> LOWER-BODY PRESERVATION / ROLLBACK veto
    -> absolute clamp no lower than -0.75 EV
    -> publish or rollback to weaker/baseline render
```

The lower-body safety layer should inspect finished response, not only input RAW/highlight statistics. Candidate safety signals for prospective research include:

- finished global median / q25 floor
- change in dark<=64 fraction
- change in deep-black / endpoint occupancy
- center/lower-body retention

Do not freeze thresholds from these two controls.

## Current conclusion

The earlier assumption that BRIGHT treatment could be controlled by a simple `0 .. -0.75 EV` ladder is incomplete.

`-0.75 EV` remains a useful **absolute experimental bound**, but the BRIGHT path needs a rollback rule that protects useful lower-body information. The correct treatment operator may also remain asymmetric to DARK rescue; previous pivoted-density experiments are still relevant.
