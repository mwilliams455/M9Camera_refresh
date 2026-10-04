# Measured-green bounds and edge-guided R/B interpolation

21 September 2026. **Guiding R/B interpolation with native green reduces the
same photograph's pink diagnostic by 93.1%, with native green and Sharp exact.
It still damages genuine coloured edges and is not an accepted correction.**
The clipped-green-only constraint examined first has essentially no visible
effect on this photograph. No application source, exposure policy or APK is
changed. PR39 stays draft and unmerged.

This continues `STAGE_TRACE_AND_COHERENT_GREEN.md`. The exact 16:47 failure DNG,
recorded unscaled Camera2 noise profile, SAT2 and render gain
1.4142135623730951 remain fixed. Both photographic scripts recompute H and
match all eight recorded phone guard statistics. This remains a host replay,
not complete Android, JPEG or Blackfin byte parity.

## A bound supported by measured green

`censored_green_bound.py` tests a narrower constraint than the earlier local
fits and white-limit heuristics. If a measured green sample supplies a lower
bound L on WB-normalized green, then each channelwise white-clipped colour
difference obeys:

```
C - G <= max(0, 1 - L),  for C = R or B
```

The bound is imposed **only at actual sensor-censored green CFA sites**, never
at R/B sites or neighbouring uncensored green sites. The implementation uses
the original RAW censor state, the effective normalization/shading gain, ADC
half-bin uncertainty, one uint16 normalization code, and a six-sigma allowance
from the capture's unscaled green noise pair. Green stays exact; only R/B
values above the derived ceiling are lowered. Unselected pixels and the
ten-pixel perimeter stay exact. This is an upper colour-difference bound, not
an assertion that every clipped green pixel has zero chroma.

At raw white, pre-shading normalized green is one, so the normalized buffer
provides a conservative effective gain estimate after subtracting one code.
The six-sigma margin is conditional on the noise model. It is not empirical
sensor calibration, a hot-pixel model, or an unconditional probability bound.
The directly supplied green pair is `[3.1248508540855e-05,
3.669826853873275e-07]`. The historical DNG NoiseProfile is not substituted.

The same 1,536 known scenes cover all four CFAs. A second 1,536-case run adds
seeded Gaussian sensor noise with variance `S * unclipped_signal + O` before
sensor clipping and ADC quantization. The model uses the recorded RGB profile
and seed92311. Synthetic shading is unity; real shading is exercised only by
the photograph. Both established references are retained.

| Bound test | Noiseless /1,536 | With model noise /1,536 |
| --- | ---: | ---: |
| Fixed-green R/B RMS regressions | 0 | 0 |
| Individual fixed-reference R/B squared-error increases | 0 | 0 |
| Known true colour differences exceeding the derived bound | 0 | 0 |
| Changed R/B samples across all fixtures | 9,488,712 | 9,453,802 |
| Full-scene RGB RMS regressions | 444 | 152 |
| Largest full-scene RGB RMS increase | 0.000281042 | 0.000007760 |

These are results for the declared scenes and noise realization, not a proof
of general photographic nonregression. The two references can disagree even
for a useful colour correction: with true clipped white `(1,1,1)` and native
green fixed at `s < 1`, neutral `(s,s,s)` matches the fixed-green colour target,
while magenta `(1,s,1)` has less absolute scene RGB error. This explains why
full-scene and fixed-green results must be interpreted separately; neither
gate is removed or relabelled to promote this candidate.

## Why that bound does not address this photograph

`censored_green_bound_replay.py` applies the same bound to H and the previous
local DCB control. The diagnostic remains pre-JPEG `min(R,B)-G > 15` with RGB
sum >300. It is a diagnostic for this capture, never a processing mask or a
valid general test for distinguishing fringe from real magenta.

| Replay | Flagged pink pixels | Camera pixels changed by bound | Final RGB8 pixels changed by bound | Largest final channel change |
| --- | ---: | ---: | ---: | ---: |
| H | 174,776 | — | — | — |
| H + bound | 174,776 | 182,566 | 5 | 2 |
| Previous local DCB | 66,712 | — | — | — |
| DCB + bound | 66,712 | 182,096 | 331 | 15 |

Of H's 174,776 flagged pixels, only **868** are directly clipped sensor sites;
only **67** are directly clipped green sites. **151,327** flagged pixels are
one or two pixels away from clipping, using Chebyshev distance. The report
records this distribution separately for R, G and B CFA sites; its last
distance bin is distance9 or more.

Thus the condition that makes the pointwise bound defensible does not cover
the main visible error. Most camera-domain adjustments are eliminated by
later processing; the exact RGB8 differences above avoid claiming that the
outputs are identical. Extending the same bound to adjacent pixels would
require an additional, presently unproved scene/interpolation assumption.

## Edge-guided interpolation control

`edge_guided_chroma.cpp` and `.py` directly interpolate the measured-phase
Co2 colour differences, replacing the opposite-phase diagonal average and
bilinear carrier consumer within the existing clipping neighbourhood.
The native pre-Sharp green plane guides the interpolation; the final native
green and fixed ISO160 Sharp remain exact. This is a research control, not a
recovered Leica algorithm.

Two controls use the same declared parameters, without a tuning sweep:

- Radius6, spatial Gaussian sigma3, and green-range Gaussian sigma0.08 in
  physical WB-normalized linear units.
- `guided_all` uses all measured R/B anchors, with the existing Co2 shrink.
- `guided_uncensored` excludes clipped R/B anchors and any R/B anchor whose
  four cardinal green inputs include a sensor-censored green sample.
- If the total anchor weight is at most 1e-12, that output channel retains
  its H/D value. No strong-colour or pink-pixel classifier is used.
- The existing distance4..8 local blend and ten-pixel perimeter apply. H/D
  stays exact outside that support. No new early white limit is introduced.

An independent Python scalar transcription reproduces all output arrays for
four random-CFA checks, including **3,104 evaluated R/B channels**, signed
differences, invalid anchors, support, rounding and preserved pixels.

| Full photograph | Flagged pink pixels | Reduction from H |
| --- | ---: | ---: |
| H | 174,776 | — |
| Previous local DCB, historical control | 66,712 | 61.8% |
| Guided, all anchors | 12,084 | 93.09% |
| Guided, uncensored anchors | 11,264 | 93.56% |

The original-resolution woodland crops look substantially cleaner. Residual
pink and other edge colour remain. This count does not measure overall image
quality or establish that the removed colour was always false.

## Genuine-colour failures prevent promotion

Both guided controls fail the existing **384-case RGGB rejection screen**.
It retains the same known-scene RGB and fixed-native-green R/B references,
inner16 crop and strict 1e-12 comparison tolerance. These are noiseless scenes
with unity shading. No larger four-CFA promotion suite or noise sweep is
justified for these already-rejected parameters.

| Control | Scene RGB failures /384 | Largest RGB RMS increase | Fixed-green R/B failures /384 | Largest R/B RMS increase |
| --- | ---: | ---: | ---: | ---: |
| Guided, all anchors | 47 | 0.03011068 | 67 | 0.03781365 |
| Guided, uncensored anchors | 154 | 0.24239432 | 156 | 0.31059840 |

For sigma1 magenta lines against very white, `guided_all` raises full-scene
RGB RMS from **0.04000669 to 0.07011737**. Its fixed-green worst case also
involves genuine magenta. Excluding clipped anchors is more destructive: for
sigma2 bright-magenta lines against cyan, RGB RMS rises from **0.07024342 to
0.31263774**. The failures include neutral subjects too, so merely exempting
strongly coloured subjects is not an established remedy.

The practical result is a promising photographic direction with a clear
failure condition: green-guided pooling can suppress the fringe but also
mix away colour structure that the guide alone cannot distinguish. Excluding
clipped anchors removes useful information and is especially damaging in
these controls. Future work must protect actual colour structure and establish
reliable interpolation support before integration; increasing suppression
strength or accepting this one woodland photograph is insufficient.

## Evidence and reproduction

Reports contain source/RAW hashes, exact H statistics, all fixture rows and
the declared scopes:

- `results/censored_green_bound_noiseless.json`
- `results/censored_green_bound_noisy.json`
- `results/censored_green_bound_replay.json`
- `results/edge_guided_chroma.json`

The replay emits `Measured-green-bound-comparison.png`; the guided probe emits
`Edge-guided-interpolation-comparison.png` and three research JPEGs. Photos,
RAW data and compiled libraries are not committed. No new APK is produced.
Auto exposure on the 15/17 Ultra remains unresolved and user-deferred.

```bash
python3 research/detail1a/censored_green_bound.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/bound-noiseless

# Same command with --noise for the seeded sensor-noise run.
python3 research/detail1a/censored_green_bound_replay.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/bound-photo

python3 research/detail1a/edge_guided_chroma.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --cfas 0 --out /absolute/path/guided-rejection-and-photo
```
