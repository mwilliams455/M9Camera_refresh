# Clipped-sample constraints and independent R/B interpolation

21 September 2026. **The local interpolation control reduces the failing
photograph's pink diagnostic by 61.8% while keeping native green exact. It
still fails colour fixtures; it is not an accepted correction or a new APK.**
This follows `WB_GAIN_AND_MAPPING.md`. The physical-white cap remains rejected.
Auto exposure is still unresolved and user-deferred.

## What changed in the investigation

Two different ideas were tested: treating clipped CFA samples as lower bounds,
and changing R/B interpolation while retaining the existing green/Sharp output.
Neither uses the pink diagnostic as a processing mask. Neither changes SAT2,
source colour, the tone curve or the recorded render gain.

### Lower-bound reconstruction: rejected

`censored_constraint_solver.cpp` implements an experimental spatial prior:
anisotropic `TV(G) + lambda * (TV(R-G) + TV(B-G))`. Non-clipped measured CFA
values are equality constraints; clipped measured values are lower bounds;
all inferred channels are nonnegative. Units are WB-neutralized linear values.
The primal and dual steps are 0.16, extrapolation is 1, and iteration counts
are fixed. This is not recovered Leica code or uniquely determined highlight
recovery, and no convergence/optimality certificate is claimed.

`censored_constraint_probe.py` retains the nine selected falsification cases:
RGGB, 160x192, repeated four-pixel diagonal lines of period15 and slope0.43,
the failing capture's neutral and representation scale, no noise, unity
shading, sensor black64/white1023, inner16 scoring. Two variants were tested:

- **Green fill:** insert only inferred hard-clipped native green samples back
  into the Bayer buffer, then rerun native green, fixed ISO160 Sharp and D.
  All other Bayer samples remain exact. Weights 0.5, 1, 2 and 4; 300 iterations.
- **Joint RGB:** add the existing Sharp correction from inferred green to all
  three inferred channels, using that result within an eight-pixel clipping
  dilation and D outside. Weights 0.5, 1 and 2; 800 iterations.

These probes change native green values; they are not fixed-green controls.
Every solver output passes the observed-sample constraints, but those
constraints do not determine the missing colours. Representative full RGB RMS
errors against the known blurred scene, clipped channelwise to 0..1:

| Background / subject / blur sigma | D | Green fill, weight1 | Joint RGB, weight1 |
| --- | ---: | ---: | ---: |
| Very white / neutral / 0.5 | 0.1329255 | 0.0980951 | 0.0970255 |
| Very white / magenta / 1 | 0.0400067 | 0.0451387 | 0.1330885 |
| Blue sky / green / 1 | 0.0375650 | 0.0370651 | 0.1077174 |
| Bright magenta / green / 1 | 0.0684948 | 0.0645047 | 0.1363682 |

The complete nine-case results are in `results/censored_constraint_probe.json`.
The portable screen reproduces all earlier exploratory metrics exactly. These
counterexamples reject the tested configurations without a costly full-frame
solver, larger tuning search or Android port. They do not prove that every
possible lower-bound reconstruction must fail.

### Independent interpolation: useful control, not yet accepted

`demosaic_control.py` runs installed rawpy 0.25.1 / LibRaw 0.21.4 AHD and DCB
as independent controls. They are not recovered M9 routines. The minimal
temporary DNG contains only the explicit CFA/black/white and identity-matrix
metadata; it inherits no camera shading, black correction or colour transform.
Raw-camera RGB16 output has unity WB, linear gamma, automatic scaling and
brightness off, and no median-filter passes.

The normalized Bayer values are neutralized with one common reversible
headroom factor `max(1, 1/nR, 1/nB)` before encoding into uint16. After
interpolation that factor is restored. Only `R-G` and `B-G` are transferred
onto the **exact native sharpened green**, then camera-channel scaling is
restored. There is no early physical-white cap. The 10-pixel perimeter retains
H on the photograph and D on synthetic scenes. Encoding still has ordinary
uint16 rounding; it is not a lossless mathematical transform.

The local control uses all CFA channels' sensor clipping, with full DCB within
Chebyshev distance4 of a sample at sensor white and a linear taper to zero at
distance8. Outside this support the photograph retains H byte-for-byte. This
support rule is an explicit heuristic, not a recovered M9 rule. It does not
transfer the existing H noise-variance model to DCB: H contributes only where
the local blend retains it. Noise calibration for a replacement remains open.

## Same-RAW results and retained checks

The exact DNG SHA-256 is
`1103f6047dd1e11fcd5defa3ddbb4e24ca5f00221e5672ffd67d5d69a5592903`.
The replay uses the recorded live Camera2 noise profile and render gain
1.4142135623730951, with no remetering. All eight previously checked H guard
statistics match the phone record exactly. Native/colour sources are
hash-verified and their hashes are retained in the report.

| Replay | Diagnostic pink pixels | Change from H |
| --- | ---: | ---: |
| Current H | 174,776 | — |
| AHD colour differences | 125,539 | -28.2% |
| DCB colour differences | 70,835 | -59.5% |
| DCB near clipping | 66,712 | -61.8% |

Counts are pre-JPEG `min(R,B)-G > 15` and RGB sum >300. This is a diagnostic
for the reported foliage shot, not an accuracy metric for genuine magenta
objects. Three original-resolution crops show markedly less pink, with some
residual fringing. They do not establish acceptance on other photographs.

All controls preserve native green and the ten-pixel perimeter exactly. The
local control also preserves all H channels at clipping distance8 or more.
Twenty-four flat linear camera-RGB cases cover both algorithms, all four
CFAs and three triples, including saturated green; their maximum channel
error is at most one uint16 unit. These are checks of the demosaic wrapper,
not a claim of Leica/Android output equivalence.

## Broad colour screen: still fails

The same 1,536 fixtures cover four CFAs, two geometries, four blur widths,
twelve backgrounds and four subjects. D remains the synthetic baseline;
noise is absent. Both existing references are retained, with comparison
tolerance 1e-12:

- Full RGB error against the known blurred scene clipped channelwise to 0..1.
- R/B error against that scene's colour differences added to fixed native G.

Neither is a Leica hardware or perceptual oracle. Native green is smoothed
and sharpened differently from the ideal scene, so the references answer
different questions; both must remain visible in assessing a replacement.

| Control / metric | Cases worse than D | Largest RMS increase |
| --- | ---: | ---: |
| DCB / known-scene RGB | 50 | 0.00430437 |
| DCB / fixed-green R/B | 285 | 0.05954252 |
| Local DCB / known-scene RGB | 16 | 0.00227591 |
| Local DCB / fixed-green R/B | 245 | 0.05954252 |

The local RGB failures consist of four configurations across all four CFAs:
unblurred bright-magenta edges against very-white or bright-magenta backgrounds,
and sigma1 neutral/green fine lines against white. Twelve of the sixteen
failures have coloured subjects. Local support avoids the global control's
worst unclipped magenta-line failure, but it does not solve the clipped cases.

For the largest fixed-green regression, unblurred RGGB neutral lines against
white, full RGB RMS improves from 0.13839536 to 0.13173111 while fixed-green
R/B RMS worsens from 0.05839135 to 0.11793388. Reporting only the former would
hide a substantial mismatch with the chosen green channel. The full 1,536
case records, summaries and photograph checks are retained in
`results/demosaic_control_synthetic.json` and `results/demosaic_control_replay.json`.

## Consequence

Changing R/B interpolation alone can remove much of this photographed fringe
without lowering highlight white or changing green detail. That narrows the
remaining work to the R/B reconstruction and its consistency with native G,
especially around clipped fine structures. It does not establish the complete
cause of every fringe or justify replacing the app's pipeline with LibRaw.

The next candidate must address these specific colour/green counterexamples
before five-RAW promotion and a phone build. No application source, APK,
exposure behaviour or production default changes in this research commit;
PR39 remains draft and unmerged.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/censored_constraint_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/constraint-screen

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/demosaic_control.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/interpolation-controls
```

Dependencies are the existing host replay stack plus rawpy. The latter script
also emits `Interpolation-controls.png` and four labelled-by-filename research
JPEGs. RAWs, temporary DNGs, native binaries and photographic outputs are not
committed to this research branch.
