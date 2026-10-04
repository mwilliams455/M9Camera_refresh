# Native-green support and uncensored local fits

21 September 2026. **Matching the R/B spatial support to native green does not
fix the clipped-edge failure. It brings back much of the photograph's pink
edging. Post-interpolation white limits and the tested local affine fits also
fail. No candidate is promoted and no application or APK changes.**

This continues `CLIPPED_CONSTRAINTS_AND_INTERPOLATION.md`. The prior local DCB
control remains a useful research comparison, with its documented regressions;
it has not become an accepted replacement. Auto exposure remains unresolved
and user-deferred. SAT2 and the direct native colour pipeline remain current.

## Test of the spatial-support hypothesis

`green_support_probe.py` starts with exactly the same headroom-preserving
LibRaw DCB interpolation as the previous control. It then applies native
green's spatial footprint to **each** reconstructed channel before transferring
R-G and B-G onto the exact current sharpened green:

- At R/B sites: average the four cardinal neighbours.
- At G sites: `(4 * centre + four diagonal neighbours) / 8`.

The control uses float arithmetic here; it is not a native integer port.
The ten-pixel perimeter is retained. The same distance4..8 clipping support
limits every control in this investigation, retaining D outside in synthetic
scenes and H outside in the photograph. The final green plane is byte-exact
with the respective baseline, so sharpening is unchanged.

A separate dependency check confirms that DCB retains all measured green
samples used by this footprint. After the existing q14 conversion and integer
floor, applying that footprint to DCB green reproduces the compiled C++
producer's pre-Sharp G on **16,128 samples across all four CFAs**. There are
8,064 exact measured-green sample comparisons. This establishes the support
relationship tested here; it does not establish full Leica or Android parity.

## Same photograph: the matching change is worse

The exact 16:47 RAW is replayed at its recorded render gain
1.4142135623730951, using the recorded live Camera2 noise profile. Native and
colour sources remain hash-verified. All eight H phone guard statistics match
exactly. All three variants retain native green, the ten-pixel perimeter and
all H channels at clipping distance8 or more.

| Replay | Diagnostic pink pixels | Reduction from H |
| --- | ---: | ---: |
| Current H | 174,776 | — |
| Previous local DCB control | 66,712 | 61.8% |
| Matched green support | 137,298 | 21.4% |

These are the existing pre-JPEG diagnostic counts, not a processing hue mask
or an accuracy metric for magenta objects. The H and local-DCB counts reproduce
the preceding report exactly. Inspection of the same three original-resolution
crops confirms substantially more pink in the matched-support control. Its
better synthetic fixed-green score does not outweigh that visible regression.

## Rejection screen, not a new 1,536-case promotion

This round uses the **384 RGGB cases** from the existing grid: two geometries,
four blur widths, twelve backgrounds and four subjects. The previous 1,536
case report remains intact. There is no claim that this round's new controls
passed or even ran the complete four-CFA colour grid. The four-CFA support
dependency check above and the BGGR photograph are separate checks.

Both prior references remain visible, with the same 1e-12 comparison tolerance:
known blurred scene RGB clipped channelwise to 0..1, and that scene's colour
differences added to native green. No noise and unity shading in the synthetic
screen. Every D and local-DCB metric reproduces its preceding result exactly.

| Control | Scene RGB cases worse than D | Largest RGB RMS increase | Fixed-green R/B cases worse than D | Largest R/B RMS increase |
| --- | ---: | ---: | ---: | ---: |
| Previous local DCB | 4 | 0.00227591 | 63 | 0.05954252 |
| Matched green support | 4 | 0.00316800 | 45 | 0.02734059 |
| White limit after DCB | 28 | 0.01187896 | 50 | 0.05677359 |
| White limit, then match | 63 | 0.03163436 | 43 | 0.02344510 |
| Match, then white limit | 47 | 0.03163436 | 59 | 0.02734059 |
| Local affine fit, radius4 | 39 | 0.03987594 | 21 | 0.05111132 |
| Local affine fit, radius8 | 127 | 0.37602712 | 113 | 0.45984957 |

The matched control's worst scene RGB failure is sigma0.5 magenta fine lines
against bright magenta: **0.08669738 to 0.08986538**. Its largest fixed-green
failure is unblurred neutral lines against white: **0.05839135 to 0.08573194**.
The previous local DCB value in that latter test was 0.11793388. Thus matching
does reduce that particular error while failing both the overall colour screen
and the real photograph. Neither reference alone is a photographic oracle.

## Why the additional controls are rejected

The white-limit controls clip reconstructed WB-neutralized RGB at physical
white, after DCB has already reconstructed the channels. This tests a different
ordering from the previously rejected RAW/pre-WB cap. Moving the limit later
still damages genuine coloured edges. Combining it with matched support in
either order does not resolve that problem.

The affine controls fit `C = a * G + b`, separately for R and B, using uncensored
measured colour samples and DCB's green guide. Samples next to hard-clipped
native green are excluded. Both fits must have at least eight samples, green
variance at least 0.02 squared, residual variance at most 0.02 squared, and
slope in [-4, 8]. Ridge regularization is 1e-6. Predicted colours are bounded
below by zero, clipped to physical white for difference construction, and
added to the unchanged native sharpened green. These are explicit experimental
thresholds, not a calibrated confidence guarantee or recovered M9 processing.

A small fit residual does not certify the extrapolated missing colour. The
radius8 control's worst case, sigma0.5 green lines against very white, raises
scene RGB RMS from **0.13962989 to 0.51565701**. Radius4 also fails strongly on
unblurred magenta lines against blue, **0.11771182 to 0.15758775**. These cases
are sufficient to reject the tested fits; there is no reason to render them
over the full photograph, expand their tuning search or port them to Android.

## Consequence and reproducibility

The remaining problem is not solved by matching filter footprints, moving a
common white limit, or trusting a low-residual local colour fit. Keep the
previous independent DCB comparison and its failures. A subsequent candidate
must preserve the cleaner directional edge reconstruction while supplying a
more reliable treatment of censored channel data; it cannot use an improved
average score to excuse returned pink fringes or colour-detail damage.

`results/green_support_probe.json` retains every case, source hashes, the
four-CFA support checks and the exact photographic replay report. The script
emits `Green-support-comparison.png` plus H/DCB/matched research JPEGs. RAWs,
photos, generated native libraries and historical assemblies are not committed.
PR39 remains draft and unmerged.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/green_support_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --cfas 0 \
  --out /absolute/path/green-support-evidence
```
