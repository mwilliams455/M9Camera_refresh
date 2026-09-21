# DETAIL1H phone validation: pink edges remain

21 September 2026. Capture `IMG_20260921_164710_1790005630040_00`.
**Photographic acceptance remains open. Do not promote DETAIL1H as a fringe fix.**

Malcolm reports pink edging in several photographs. The supplied foliage/sky
JPEG visibly contains pink boundaries at many leaves and branches. Its matching
PRIMARY records `M9DETAIL1H_NATIVEGUARD`, guard requested/applied, and reason
`nominal_unscaled_profile`. This is evidence that the new stage ran, not an old
build or guard fallback. The top-level legacy `sharpnessRbPolicy` label still
describes the older proxy; use `renderer.detail1H` for stage execution evidence.

## What this capture establishes

- BGGR, ISO 50, exposure 9,616,969 ns; recorded output 3072x4096.
- The uploaded JPEG is 1536x2048, so it confirms the visible problem but cannot
  support original-pixel measurements or full-resolution seam analysis.
- Guard execution: 192 tiles, 1,158,767 changed carrier samples, maximum absolute
  carrier correction 7, elapsed 1120.74 ms. Green/fixed ISO160 Sharp retained.
- RAW hard-clip diagnostic: 2.449%; censored sample count: 325,092. Censoring also
  includes black samples and is not the same measurement as highlight clipping.
- Final bitmap audit: 5.724% of pixels have a channel exactly 255, 3.762% are full
  white. The older `rgb8ClipFraction` refers to another measurement and must not
  replace the final bitmap audit.
- Manual user EV was +1.75 with a held Auto baseline +0.75. This is not an Auto
  brightening validation. Auto exposure remains unresolved and deferred by user.

The diagnostics do not locate RAW clipping at each pink edge. They cannot
separate optical/source fringing, interpolation, green sharpening, physical
white clipping or downstream colour amplification without the matching RAW.
No photographic correction, exposure retune or replacement APK is issued here.

## New falsification evidence

`clipped_edge_probe.py` executes the frozen native green/Sharp foundation and
the exact D/H spatial kernels on 16 noiseless neutral fixtures. It uses this
capture's CFA, neutral, representation scale and live noise profile. Fixtures
cover a diagonal step and fine diagonal lines, four optical blur widths, and
unclipped versus clipped neutral highlights. A unity lens-gain grid is deliberate;
the normalization is synthetic float64, not an Android preprocessing oracle.

The metric uses restored, white-balanced camera channels, clipped at neutral
white: a pixel is pink when **both** R/nr-G and B/nb-G exceed 0.02. It excludes
the outer 16 pixels. This is a diagnostic camera-domain threshold, not a rendered
JPEG colour metric or a claim of visibility at that exact threshold.

All eight clipped fixtures contain a larger pink-pixel fraction with D/H than
with the previous native foundation, even though total neutral-error RMS is
lower. For fine lines at sigma=1 sensor pixel, the fraction rises from 11.94%
to 19.10%; RMS falls from 0.0304 to 0.0226. The eight unclipped counterparts have
zero pink pixels under this threshold with D/H. This exposes why improved
aggregate error and the earlier unclipped neutral-edge checks were insufficient.

The noise guard leaves these clipped cases effectively unchanged. Its radius-6
censor exclusion intentionally protects uncertain samples from noise smoothing;
it does not repair false colour already present in the D reconstruction.
This reproduces a relevant weakness, **not the cause of every fringe in the
phone JPEG**. A blanket return to the old foundation is not validated either.

## Required next evidence and work

The exact DNG was absent from the provided attachments and exact-name Library
and Dropbox searches on this turn. Request
`IMG_20260921_164710_1790005630040_00.dng`; another capture is unnecessary.

Replay that RAW through the previous native foundation, D without the guard,
and H with the recorded live profile, preserving the capture's shading and
exposure plan. Compare original-resolution edge crops before and after physical
white clipping, target colour/SAT2 and curve02. Extend the acceptance checks to
clipped neutral and genuinely coloured fine edges before choosing a correction.
Avoid a hue-based pink suppression mask that could remove real subject colour.

Evidence: `results/fringe_164710_capture.json` and
`results/clipped_edge_probe.json`. The capture fixture records hashes of the
supplied PRIMARY/JPEG; private image pixels are not added to this repository.

```bash
python3 research/detail1a/clipped_edge_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/clipped_probe
```
