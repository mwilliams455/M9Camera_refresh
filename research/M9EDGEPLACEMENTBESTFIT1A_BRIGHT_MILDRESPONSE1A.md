# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT MILDRESPONSE1A

Research-only. No live APK, capture policy, TC20, frozen renderer, curve02, color science, JPEG quality, or DNG changes.

## Purpose

Translate the exact-pixel prospective blind review into a falsifiable **finished-response envelope** for NATURAL_MILD BRIGHT treatment without pretending that scene metadata can predict one universal correction strength.

This work does **not** alter `BRIGHT_LOWKEY_OPENING1A` eligibility.

## Why a response envelope

Historical confirmed BRIGHT_FAIL treatment magnitude is not monotonic in:

- `structuralLowKeyScore`
- TC20 gain
- frozen global median

The near-matched historical pair `184927` / `184937` preferred RGB075 versus RGB050 despite similar placement statistics. Therefore strength should not be mapped directly from those scalars.

The prospective user feedback also establishes a distinct risk:

> increasing darkness can progressively lose the M9 character even when the RGB-pivot operator technically preserves upper-tone anchors.

The safety problem for NATURAL_MILD is therefore over-densifying the useful body, not simply highlight clipping.

## Exact prospective response

### 173828

Frozen was already acceptable in isolation. Exact mild-bank blind review preferred RGB015.

| Variant | median Y | delta median | dark<=64 | delta dark<=64 | q95 Y | delta q95 |
|---|---:|---:|---:|---:|---:|---:|
| Frozen | 81.69 | 0.00 | 0.3623 | 0.0000 | 180.16 | 0.00 |
| RGB015 | 76.46 | -5.22 | 0.4008 | +0.0385 | 177.16 | -3.00 |
| RGB025 | 73.21 | -8.48 | 0.4255 | +0.0632 | 175.15 | -5.00 |
| RGB035 | 70.11 | -11.58 | 0.4496 | +0.0874 | 173.11 | -7.04 |

The image is not LOWKEY-eligible (`structuralLowKeyScore = 0`), so this is a treatment-response control, not an automatic-correction positive.

### 181559

This is the sole full `BRIGHT_LOWKEY_OPENING1A` activation in the 47-frame untouched prospective cohort. Exact mild-bank review was RGB015 / RGB025, with no need for RGB035 once the mild region was resolved.

| Variant | median Y | delta median | dark<=64 | delta dark<=64 | q95 Y | delta q95 |
|---|---:|---:|---:|---:|---:|---:|
| Frozen | 82.08 | 0.00 | 0.3099 | 0.0000 | 157.19 | 0.00 |
| RGB015 | 76.96 | -5.12 | 0.3580 | +0.0481 | 152.84 | -4.35 |
| RGB025 | 73.73 | -8.35 | 0.3909 | +0.0810 | 149.97 | -7.22 |
| RGB035 | 70.62 | -11.45 | 0.4242 | +0.1143 | 147.12 | -10.07 |

## Observed prospective mild envelope

For falsification only:

```text
median drop <= 9.0 Y
dark<=64 increase <= +0.09
q95 drop <= 8.0 Y
bright>=224 increase <= +0.002
```

Status:

```text
observed_two_frame_prospective_probe_not_production_threshold
```

Under this envelope:

- 173828: RGB015 PASS, RGB025 PASS, RGB035 FAIL on median drop
- 181559: RGB015 PASS, RGB025 PASS, RGB035 FAIL on median + dark-body + q95 response

This is useful because the boundary appears at the same treatment transition where the exact visual preference stopped supporting stronger density.

It is still only a two-frame observation and must be challenged prospectively.

## Treatment policy implication

The conservative NATURAL_MILD research order should now be:

```text
LOWKEY_OPENING eligible
  -> Frozen remains reference
  -> RGB015 first treatment probe
  -> RGB025 escalation-only probe
  -> RGB035 upper stress bound only
```

Do **not** make RGB025 the default merely because it remains inside the observed response envelope.

The project priority is under-intervention and preservation of M9 character. Since RGB015 was the exact winner on 173828 and tied/competed with RGB025 on 181559, the weakest useful treatment is the better default research hypothesis.

## Relationship to historical severe BRIGHT_FAIL

Historical treatment-positive LOWKEY anchors remain:

- `184927` -> RGB075 preferred
- `184937` -> RGB050 preferred
- `194307` -> RGB075 tentative preferred

These demonstrate that the NATURAL_MILD envelope must **not** replace the severe research bank.

Current architecture therefore remains categorical:

```text
BRIGHT eligibility
  -> HOLD
  -> LOWKEY_OPENING / NATURAL_MILD
       -> RGB015 first
       -> RGB025 escalation-only
       -> RGB035 stress bound
  -> SEVERE_CONFIRMED_FAIL research class
       -> RGB035 / RGB050 / RGB075 historical bank
       -> no automatic severity classifier yet
```

Until an independently falsified severe-vs-mild discriminator exists, unknown future LOWKEY activations should be treated conservatively as NATURAL_MILD in offline research. A live camera must not infer severe correction from score, gain, or median alone.

## Next falsification

For the next independent natural LOWKEY activation:

1. judge Frozen first;
2. if Frozen is genuinely a little too open, compare Frozen / RGB015 / RGB025;
3. include RGB035 only as an upper stress bound if useful;
4. compute `MILDRESPONSE1A` metrics;
5. test whether the preferred treatment remains inside or falsifies the observed envelope;
6. do not retune the envelope to force the new result to fit.

A second later treatment-positive LOWKEY activation is still required before any production promotion.
