# M9EDGEPLACEMENT1A — INTENTCOLLAPSE1A hypothesis (corrected)

Research-only hypothesis. This is **not** a production selector, not an EV rule,
and not authorization to modify the live APK.

## Corrected Part-3 identity state

The prior Part-3 `+30` global-ordinal inference has been retracted.

The strongest current visual identity is:

`IMG_20260904_164048_1788536448208_00`

The original reviewer recognizes this as likely visual corpus #73, and a direct
render shows the retained #73 scene description: a sculpture/statue against a
bright field/sky that is substantially too dense.

It is therefore the current same-build exact DARK example.

`IMG_20260904_164019_1788536419887_00`

remains a very strong same-build DARK candidate, but is no longer claimed to be
#40. Its old #40 identity depended on the invalid offset inference.

## Why a new hypothesis is still needed

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

DARK_FAIL therefore cannot simply mean "the image is dark" or "TC20 was guarded".

## RENDERGRID1A directional evidence

RENDERGRID1A applies the recovered 16x22 Integral spatial mask and 4x6 regional
topology to the finished frozen JPEG as diagnostic geometry only.

Current Part-3 observations by exact capture:

| capture | disposition | achieved intent | upper/lower shift | Integral relative shift |
|---|---|---:|---:|---:|
| `164048` | DARK_FAIL / likely #73 | ~+0.138 EV | ~+2.75 EV | ~+0.10 EV |
| `164019` | DARK candidate | ~+0.299 EV | ~+2.34 EV | ~-0.01 EV |
| `164035` | saturated safety control | ~+0.070 EV | ~+1.67 EV | ~+0.05 EV |
| `164402` | GOOD swan hard negative | ~+0.202 EV | ~+0.46 EV | ~+0.52 EV |
| `164622` | BOUNDARY | ~+0.176 EV | ~+1.12 EV | ~-0.04 EV |
| `164647` | boundary review | ~+0.422 EV | ~+1.64 EV | ~+0.03 EV |

The potentially useful distinction is a conjunction rather than one field:

1. real positive sensor-exposure intent exists;
2. Frozen substantially increases upper-versus-lower spatial separation;
3. broad finished-render body remains extremely low;
4. the Integral-weighted field fails to improve materially relative to the
   overall rendered mean.

This remains consistent with an **intent-cancelled useful-body-collapse** subtype.

## Part-3-only descriptive conjunction

The observed shape remains approximately:

- achieved intent >= +0.10 EV
- upper/lower render-vs-preview separation shift >= +1.5 EV
- broad render-cell body remains very low (P75 median roughly <=30)
- Integral relative shift <= roughly +0.15 EV

Within the currently fixed Part-3 labels it activates:

- `164048` — confirmed/strongly anchored DARK example
- `164019` — unconfirmed DARK candidate

and activates:

- confirmed GOOD: 0 / 10
- confirmed BOUNDARY: 0 / 2

The exact values are descriptive only. They were observed in the same cohort and
are not thresholds to preserve or port.

## Important methodological correction

The old interpretation treated `164019` as a confirmed #40 and `164048` as an
unconfirmed neighbor. That role assignment was wrong because the ordinal mapping
was wrong.

The spatial hypothesis itself is not disproved by the correction: both captures
show the same unusual geometry. But it has **not gained independent validation**
from the #73 recognition because both statue captures were already involved in
forming the hypothesis.

This distinction matters.

## Hard negatives remain important

`164402` is particularly valuable because it received meaningful positive capture
intent while the white swan remained photographically plausible against dark
surroundings. It protects against:

`positive intent + dark finished render -> lift`

`164622` and the saturated `164035` frame likewise protect against simple spatial
shift or highlight-tail rules.

## Required falsification before promotion

INTENTCOLLAPSE1A only becomes interesting if its qualitative shape survives:

1. at least 30 global GOOD controls;
2. at least 10 compatible same-build GOOD controls;
3. at least 2 compatible same-build BOUNDARY controls;
4. a **second independently identified same-build DARK_FAIL** not used to form the
   current conjunction;
5. retained #4/#40/#80/#98 when exact identities become available;
6. intentional low-key and bright-subject-on-dark-background hard negatives;
7. saturated-preview stress frames;
8. Frozen regression and blinded visual validation.

## Architecture if it survives

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

The spatial grid remains classifier evidence only, never local tone mapping.
Frozen remains the mandatory default.
