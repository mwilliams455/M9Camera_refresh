# M9DETAIL1F — protect colour detail around Noise2

21 September 2026. **The new bounded Noise2 probe avoids the DETAIL1E ISO573
edge regression in the five reviewed replays, with modest colour-noise reduction
and substantially better colour-detail retention in controlled tests.** Native
green and fixed ISO160 Sharp remain exact. This is a mobile adaptation around
the recovered mode1 filter, not newly recovered Leica firmware logic. It remains
offline; production source, defaults, preview and APK are unchanged.

## What caused the DETAIL1E regression

`noise2_ablation.py` separates filter width, threshold and high-residual colour
attenuation on the ISO573 edge/quiet tiles. Its padded context crops reproduce
the corresponding decoded full-frame JPEG control crops exactly, including
orientation before encoding and JPEG MCU alignment. The six control crops
cover corrected DETAIL1D, fixed160 Noise2 and indexed Noise2, in both tiles.

Change in decoded chroma HF RMS relative to corrected DETAIL1D:

| Ablation | Edge | Quiet |
| --- | --- | --- |
| Fixed160, small filter, T256 | −0.736% | −17.527% |
| Indexed640, wide filter, T512 | +3.283% | −31.064% |
| Wide filter, fixed T256 | −4.880% | −30.228% |
| Small filter, indexed T512 | +9.478% | −17.774% |
| Indexed, high-residual attenuation bypassed | +3.327% | −31.064% |
| Indexed smoothing target alone | +79.596% | −32.396% |

The threshold increase is the main driver in this capture. Removing the
high-residual attenuation does not repair it. A larger threshold allows more
low/medium-contrast colour structure to move toward the smoothed target. These
are controlled intervention results for this RAW, not a universal decomposition
of all chromatic aberration or all possible Noise2 artifacts.

## Noise estimate in the actual processing units

All five DNGs contain three RGB NoiseProfile coefficient pairs. The camera noise
model is `sigma(x)=sqrt(S*x+O)` for normalized RAW signal x; see the
[Android noise-profile documentation](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#SENSOR_NOISE_PROFILE).
`inputs.read(..., with_noise=True)` optionally carries variance through the same
black/white normalization, full-frame NORM030 shading, representation scaling
and 14-bit conversion. Existing input pixels are unchanged, as confirmed by the
ten reference JPEG hashes. R/B variance is then divided by `nr²` and `nb²` for
the corrected difference domain. Green variance keeps its original scale.

The writer provenance is recorded in `results/noise2_profile_audit.json`.
The inspected `DngCreator` writes `NoiseModeler.computeModel` in RGB order;
`NoiseModeler` can scale its base coefficients by
`adaptiveMpy/(FrameCount*0.9)`. All five actual DNG descriptions say FrameCount=1.
There is no evidence of merged input here. The inspected current writer is not
proof of every older writer version, and neither the metadata nor the frame
count establishes a measured sensor noise/covariance calibration. No stacking
or HDR is introduced by this work.

Noise must be propagated through the carrier's shared raw samples. Treating
neighbouring carrier values as independent would give the wrong variance. Let
K be the linear, unshrunk DETAIL1D carrier kernel: four diagonal colour samples
at weight1/4, less their four-cardinal green averages. Let H be the recovered
mode1 separable kernel `[1,0,2,0,1]/4` on the full pixel grid. For the residual
between original carrier c and smoothing target m, the combined raw kernel is
`L = K - H*K`, and its variance estimate is `V = L² * raw_variance`.
The square is taken **after** combining duplicate raw coefficients. This
accounts for covariance introduced by the linear carrier/filter operations.

Four independent white-noise checks, 196,608 samples in total, reproduce this
prediction to observed/predicted ratios 0.9872–1.0093. They include unequal
channel gains, unequal R/G/B noise and all four CFAs. They use the unshrunk
carrier. Nonlinear Co shrink, real sensor spatial correlation, clipping and
uncertainty in the metadata remain limitations of the estimate used on photos.

## Bounded confidence correction

`noise2_guard.py` retains the recovered mode1 smoothing target, avoiding the
unresolved mode2 MAC-rounding choice in the new candidate. It does not use an
ISO lookup to choose strength, and does not use the old colour-attenuation branch.
For residual `r=c-m` and predicted variance V:

```
E = mean(r²) / mean(V)       # 5×5 samples on the same CFA phase
structure_confidence = clamp(2-E, 0, 1)
residual_confidence = clamp(1-|r|/(2*sqrt(V)), 0, 1)
weight = structure_confidence * residual_confidence
out = c + round_to_even(-weight*r)
```

Zero variance bypasses correction. Raw samples at/below black or at/above white
disable correction within six pixels, covering Co, mode1 and consumer support.
The outer ten carrier pixels also bypass. Every correction stays between c and
m and has magnitude at most `sqrt(V)/2 + 0.5` integer units, including rounding.
There is no hue mask or selective desaturation. Strong residual structure
reduces smoothing even when green is constant, protecting true colour-only
detail that a green-edge test would miss.

The confidence functions and constants are explicit engineering choices for a
mobile probe. They are not attributed to Leica. Nominal profile variance factor1
was fixed before the photographic replay; half/double variance factors were
tested on controlled scenes to expose sensitivity rather than tune each photo.

## Controlled quality checks

Thirty-six noisy neutral-edge cases cover all four CFAs, three unequal R/B
responses and three edge directions. Every nominal guarded result reduces
false-colour RMS versus corrected DETAIL1D, by at least 7.59%. This tests known
neutral truth; it does not imply every real coloured edge should become neutral.

Twenty-four known-colour scenes cover four CFAs and six patterns, with known
R/B noise sigma100 in green-domain units and noiseless green. Nominal correction
never increases true R/B RMS error in this set. Mean new/old RMS ratios:

| True scene | Nominal guard | Twice estimated variance |
| --- | --- | --- |
| Neutral flat | 0.9196 | 0.8463 |
| Coloured flat | 0.9253 | 0.8506 |
| Colour edge | 0.9945 | 0.9900 |
| Colour sine, period8 | 1.0000 | 1.0000 |
| Colour sine, period16 | 1.0000 | 1.0000 |
| Colour sine, period32 | 0.9979 | 1.0205 |

The double-variance sensitivity case raises true error by as much as 2.68%.
This is evidence that noise-model calibration matters; doubling the estimate is
not approved. No claim is made that single-frame filtering can distinguish all
weak real colour detail from noise. Zero-variance and fully censored inputs
bypass exactly. Mixed clipped patches preserve reconstructed camera RGB exactly
within five pixels in all four CFAs, verifying the consumer support boundary.

## Finished JPEGs

Fifteen full 4096×3072 JPEG95 outputs compare corrected DETAIL1D, rejected
indexed DETAIL1E, and the new guard. All ten reference-control hashes match
DETAIL1E exactly. The new candidate preserves 62,914,560 native green samples
across the five RAWs; supported green matches actual fixed ISO160 native Sharp.
All render gains match the corrected control exactly in this run.

Changes below are relative to corrected DETAIL1D in the same decoded crops:

| Sensor ISO | Guard: quiet chroma HF | Guard: edge chroma HF | Guard: edge luma gradient p95 |
| --- | --- | --- | --- |
| 50, 15 Ultra | −0.67% | −0.06% | +0.001% |
| 104, 17 Ultra | −2.57% | −0.97% | −0.112% |
| 521, 15 Ultra | −5.28% | −5.72% | −0.038% |
| 573, 15 Ultra | −4.18% | −0.31% | +0.006% |
| 1142, 15 Ultra | −3.04% | −1.28% | −0.015% |

Chroma HF includes real colour detail, noise and artifacts; these are not
noise-only percentages. All five sheets were visually reviewed. The guarded
ISO573 edge stays close to corrected DETAIL1D and avoids the additional magenta
activity in the rejected indexed column. Skin/hair and foliage changes are
subtle. The defocused ISO521 scene shows the largest quiet-crop reduction but
cannot establish in-focus texture retention. This is deliberately less
aggressive than DETAIL1E's 10–40% quiet chroma-HF reduction.

**Decision:** retain this as the next offline candidate and keep corrected
DETAIL1D as the fallback/control. The specific Noise2 regression is avoided in
this reviewed set; absence of every fringe in every scene is not established.
Before a phone default, verify noise-profile provenance and spatial covariance
against repeat flat/colour-detail captures, then check the same implementation
on-device. High-ISO 17 Ultra and telephoto evidence remains missing. Complete
Leica Noise2/WB parity remains a separate research goal. No image quality is
traded for performance, and no production setting is changed.

## Reproduce

Use the frozen GL2G assembly and header from DETAIL1E, with the same dependencies.
`noise2_guard_ablation.json`, `noise2_profile_audit.json` and
`noise2_guard_report.json` in `results/` retain the observations and measurements.

```bash
python3 research/detail1a/noise2_ablation.py \
  /absolute/path/15u-573.dng /absolute/path/m9_sharp_fulliso_bank.h \
  /absolute/path/detail1e/replay /absolute/path/detail1f/ablation
python3 research/detail1a/noise2_guard_checks.py \
  /absolute/path/detail1f /absolute/path/m9_sharp_fulliso_bank.h
python3 research/detail1a/noise2_guard_run.py \
  --assembled PhotonCamera --header /absolute/path/m9_sharp_fulliso_bank.h \
  --reference-report research/detail1a/results/noise2_report.json \
  --checks /absolute/path/detail1f/guard_checks.json \
  --out /absolute/path/detail1f/replay \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng /absolute/path/15u-1142.dng
```
