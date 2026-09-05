# M9EDGEPLACEMENT1A — INTENTCOLLAPSE1A hypothesis

Research-only hypothesis. This is **not** a production selector, not an EV rule,
and not authorization to modify the live APK.

## Observation

September-4 Part-3 recovered one exact DARK_FAIL:

`IMG_20260904_164019_1788536419887_00` — global #40, backlit statue.

A neighboring frame:

`IMG_20260904_164048_1788536448208_00` — global #42

is a high-priority DARK review candidate but remains unlabelled.

Both are from the same 1.61 / sceneexposure-v8 / R3.8-H25-TG1 field cohort.

## Why a new hypothesis is needed

The recovered Part-3 control field falsifies several simple DARK explanations.
Confirmed or plausible non-failure photographs can also have:

- very low preview medians;
- very low finished global/center medians;
- TC20 highlight-guard binding;
- severe guard margin;
- low RAW upper-tail values;
- positive capture assist;
- `renderLiftNeedEvidence == 1`;
- `wholeFrameStarvationEvidence == 1`.

Therefore DARK_FAIL cannot mean simply "the image is dark" or "TC20 was guarded".

## RENDERGRID1A directional evidence

RENDERGRID1A reuses the exact recovered M10-R 16x22 Integral spatial mask and
4x6 regional topology, but applies them only as diagnostic geometry to the
finished frozen JPEG.

Part-3 exploratory values:

| frame | disposition | achieved intent | upper/lower shift | Integral relative shift |
|---|---|---:|---:|---:|
| #40 | confirmed DARK_FAIL | ~+0.30 EV | ~+2.34 EV | ~-0.01 EV |
| #41 | saturated safety control | ~+0.07 EV | ~+1.67 EV | ~+0.05 EV |
| #42 | DARK review candidate | positive | ~+2.75 EV | ~+0.10 EV |
| #47 | plausible swan hard negative | ~+0.20 EV | ~+0.46 EV | ~+0.52 EV |
| #54 | boundary review | ~+0.18 EV | ~+1.12 EV | ~-0.04 EV |
| #55 | boundary review | ~+0.42 EV | ~+1.64 EV | ~+0.03 EV |

The potentially useful distinction is not any single column. The pattern in #40
and #42 is a conjunction:

1. real positive sensor-exposure intent exists;
2. Frozen substantially increases upper-versus-lower spatial separation;
3. the broad finished-render body remains extremely low;
4. the Integral-weighted field fails to improve materially relative to the
   overall rendered mean.

That is consistent with a possible **intent-cancelled useful-body-collapse**
mechanism: the capture system spends real exposure on a difficult scene, but the
frozen normalization/render relationship preserves the upper field while the
body remains buried.

## Part-3-only exploratory conjunction

The following values currently isolate #40 and #42 inside the inspected Part-3
segment:

- achieved intent >= approximately +0.10 EV
- upper/lower render-vs-preview separation shift >= approximately +1.5 EV
- broad render cell body remains very low (for example P75 cell median <= ~30)
- Integral relative shift <= approximately +0.15 EV

These numbers are **descriptive boundaries from one tiny cohort**. They are not
thresholds to preserve, tune, or port into production.

The important information is the shape of the conjunction, not the exact values.

## Why #41 matters

#41 is deliberately retained as a saturated-preview safety control. It has a
large upper/lower shift but much less positive capture intent and belongs to the
known q95==255 stress cohort.

Any future classifier must protect it unless direct photographic review says
otherwise. This is one reason a simple upper/lower-shift threshold is rejected.

## Why #47 matters

#47 is a strong hard negative because it received meaningful positive capture
intent yet remains photographically plausible. Its Integral-weighted rendered
field improves relative to its overall mean far more than #40/#42, while its
upper/lower shift is modest.

This makes #47 particularly valuable against a naïve rule such as:

`positive intent + dark finished render -> lift`.

## Relation to the September-3 DARK_FAIL anchors

The two exact September-3 DARK_FAILs may represent a different failure mechanism:

- baseline useful-body starvation / insufficient development;
- not necessarily positive-intent cancellation.

Do **not** split production `DARK_FAIL` into multiple public classes yet.

If needed, research metadata may later carry a non-authoritative
`darkFailureMechanism` field such as:

- `INTENT_COLLAPSE_CANDIDATE`
- `BASELINE_STARVATION_CANDIDATE`

solely for analysis. Placement remains the production-level concept.

## Required falsification before further promotion

INTENTCOLLAPSE1A only becomes interesting if the same qualitative conjunction
survives:

1. at least 10 confirmed same-build GOOD controls;
2. at least 2 confirmed same-build BOUNDARY controls;
3. additional exact DARK_FAILs from #4/#73/#80/#98 when archives are recovered;
4. intentional low-key and bright-subject-on-dark-background hard negatives;
5. saturated-preview stress frames;
6. Frozen regression;
7. blinded visual validation.

If the conjunction activates broadly on those controls, reject the hypothesis.

## Architectural consequence if it survives

The likely architecture would still be conservative and post-Frozen:

```text
capture / RAW
    ↓
frozen TC20 + M9 renderer
    ↓
finished-render spatial evidence
    ↓
very-high-confidence exception gate
    ├─ ambiguous / coherent darkness -> Frozen unchanged
    └─ confirmed useful-body collapse -> bounded DARK development treatment
```

The spatial grid would be **classifier evidence only**, never local tone mapping.

No face detection, semantic subject detector, HDR engine, global black lift, or
spatially varying pixel correction is implied.

Frozen remains the mandatory default.
