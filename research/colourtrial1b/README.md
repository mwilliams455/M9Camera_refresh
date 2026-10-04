# COLOURTRIAL1B — separate RAW noise and clipping experiments

Offline research, with no Android, default-renderer, Auto-exposure, SAT, curve,
or JPEG integration. The reference is complete AMaZE reconstruction followed
by the fixed 25% directional correction in `../colourtrial1a/chroma.cpp`.
The old green replacement and final Sharp are absent from candidate paths.

The factorial consists of the reference, same-phase noise handling alone,
clipped-sample repair alone, and noise handling followed by clipped repair.
All four retain the same downstream processing and correction strength.
No automatic ISO-based demosaicer selection is introduced.

## Working configuration

| Responsibility | Selected direction |
|---|---|
| Auto exposure / highlight protection | Apply the existing preview clipping and brightening budget to total positive Auto bias, including the inherited baseline. See the [Auto exposure policy](../../patches/colourtrial1a/README.md). |
| Complete colour reconstruction | AMaZE, with the old green replacement and final Sharp absent. |
| Residual chroma correction | Fixed 25% directional correction from COLOURTRIAL1A. |
| RAW noise correction | Apply one quarter of the same-phase noise-filter proposal. |

This is a working balance for implementation and device validation. Faint
residual fringe and some attenuation of tiny colour details remain possible.
The full noise-filter strength and `clipped_ratio` are retained as diagnostic
experiments; neither is selected for this configuration. Highlight protection
is documented under Auto exposure, with its preview-based measurement limits
kept explicit. No new runtime or APK integration is introduced by this choice.

## Noise hypothesis

`phase_noise` works before demosaicing. It compares 3×3 patches within each
individual Bayer phase, searching a 5×5 same-phase neighbourhood. Distances
are divided by the sum of the two sensor variances. The unit expected noise
distance is removed and the weight is `exp(-2 * max(distance - 1, 0))`.
At least seven uncensored patch comparisons are required. The centre has
unit weight; each accepted neighbour contributes its measured value.

The caller supplies independent RAW variance in squared input-code units:
`(S * signal + B + quantization_variance) * (gain / scale * 65535)^2`.
Signal and profile are normalized to the sensor black-to-white range before
shading. Use the actual per-colour noise profile and full-frame shading gain.
Do not substitute an interpolation-specific output variance model. Zero
variance disables filtering at that sample. Black- and white-censored samples
are excluded; the six-pixel RAW border is copied exactly.

This changes measured samples deliberately. Noise-like genuine detail can be
attenuated. Whole-image error alone cannot establish detail preservation:
evaluate weak coloured points/lines, noisy detail, and noiseless features
with the same noise model supplied. No photographic acceptance is implied.

An explicitly separate bounded variant uses `Reconstruction.blend` to apply
only one quarter of the RAW correction. This limits each measurement change
to 25% of the full proposal, within half a code of rounding. It is distinct
from the fixed downstream 25% chroma correction. This RAW bound does not
guarantee a corresponding bound after nonlinear demosaicing and colour.

## Diagnostic highlight-reconstruction hypothesis

`clipped_ratio` modifies only measurements flagged as physically sensor-white
clipped. Shading-amplified or white-balanced values exceeding one are not such
flags. Initial complete AMaZE RGB guides ratios between channels.

For a clipped channel, donors are sampled on the same Bayer phase within a
12-pixel radius. Their 3×3 neighbourhood must contain no sensor-white flags;
their measurement must exceed four estimated noise standard deviations.
The other two channels must have similar relative colour (difference at
most 0.1), with a combined-brightness ratio between 1/8 and 8. Donor weights
depend on spatial distance and this colour agreement. At least four donors
and ratio standard deviation no greater than 15% of the mean are required.

The inferred measurement can only increase, to at most twice the observed
bound and the input storage maximum. All other measured samples remain
exact. AMaZE is then rerun on the modified mosaic; the existing downstream
camera-white ceiling remains in place. This is not an HDR output mode.

The method assumes local colour continuity. It cannot establish the missing
colour from a clipped observation, may abstain at difficult edges, and can
still infer the wrong value. A successful known-neutral recovery invariant
does not establish performance on coloured highlights. Test both.

## Host interface and checks

`control.py` validates array layout, compiles the standalone C++ library into
a caller-chosen directory, and checks sample constraints on every call.
Input arrays must not alias output storage. CFA values 0–3 mean RGGB, GRBG,
GBRG, BGGR. Neutral is `[nR, 1, nB]`. Full-frame CFA origin is assumed.

Run the synthetic checks outside the repository:

```sh
OPENBLAS_NUM_THREADS=1 python3 research/colourtrial1b/check.py /tmp/m9-colourtrial1b-check
```

They cover zero-noise bypass, four independent flat phases, protected
censored samples and border, deterministic one/four-worker output, known
flat-noise error reduction, no-clipping identity on all CFAs, unchanged
unclipped measurements, lower bounds, and a recoverable neutral highlight.

The research harness must additionally reproduce the existing reference
before scoring SAT2/3/4, inspect full-size and normal-size photographs,
and measure fine-colour retention independently of aggregate noise scores.
Private captures, paths, coordinates, reports and photographic derivatives
are intentionally outside this source tree.
