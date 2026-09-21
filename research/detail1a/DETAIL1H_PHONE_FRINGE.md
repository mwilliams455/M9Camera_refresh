# DETAIL1H phone validation: pink edges remain

21 September 2026. Capture `IMG_20260921_164710_1790005630040_00`.
**Photographic acceptance remains open. Do not promote DETAIL1H as a fringe fix.**

Further continuation: [`CENSORED_CHROMA_AND_WB.md`](CENSORED_CHROMA_AND_WB.md)
records 1,536 coloured/severely clipped fixtures, rejected local cleanup, and
new evidence for the native pre-interpolation WB arithmetic boundary.

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

The diagnostics alone could not locate RAW clipping at each pink edge. The
matching DNG has now been supplied and replayed as described below. No accepted
photographic correction, exposure retune or replacement APK is issued here.

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

## Matching-RAW replay, completed

The uploaded DNG is readable: 25,171,214 bytes, SHA-256
`1103f6047dd1e11fcd5defa3ddbb4e24ca5f00221e5672ffd67d5d69a5592903`.
Its actual neutral is `[0.41796875, 1, 0.6435546875]`; the final blue digits in
the phone's JSON are rounded. DNG-derived NORM030 alpha and representation scale
match the phone exactly: `0.2516146769823271` and `1.6105431518598052`.

`fringe_replay.py` reconstructs the existing shading input, executes the frozen
native green/fixed-ISO160 Sharp stage, and compares the previous foundation,
corrected D with guard off, and shipped H. It uses the **recorded live Camera2
RGB noise profile**, not the DNG writer's different historical profile. Eight H
statistics match the phone exactly: tiles, supported samples, changed samples,
maximum correction, censored samples, mean confidence, mean residual variance
and scratch budget. Elapsed time is intentionally excluded.

All variants use the capture's actual render gain `1.4142135623730951`, with
unchanged extracted source colour, SAT2 and curve02. The larger original TC20
gain is not the gain applied by the phone. There is no independent remetering or
exposure adjustment. DNG metadata/preprocessing and host encoding remain
explicit replay boundaries; matching stage statistics do **not** prove complete
Android pixel or JPEG parity.

For this foliage scene, a diagnostic counts pre-JPEG RGB8 pixels with
`min(R,B)-G > 15` and mean RGB > 100. This is not a universal colour-quality
measure: real magenta subjects also qualify. It is never used by a correction.

| Replay | Diagnostic pink pixels | Fraction of frame |
| --- | ---: | ---: |
| Previous native foundation | 125,225 | 0.995% |
| D, guard off | 174,776 | 1.389% |
| H, live profile | 174,776 | 1.389% |
| Producer-only early white limit, guard off | 54,957 | 0.437% |
| Early limit gated by adjacent clipped green, guard off | 56,950 | 0.453% |

The original-resolution crops confirm the increased pink in D/H. Turning off
the guard leaves the same diagnostic count and visible bright-edge problem;
it does not mean all D/H pixels are identical. Of H's counted pixels, 87.080%
are within two sensor pixels and 95.440% within four of an original hard-clipped
RAW sample (Chebyshev distance). This localizes most of this measured failure
to clipped-highlight neighbourhoods. It does not establish that every residual
fringe is interpolation rather than optical/source colour.

## White-limit candidates rejected

The simple probe applies the already-existing per-channel physical-white limits
**before D's producer interpolation**, at `round(65535 * neutral[channel] /
representationScale)`. The consumer still uses the original native sharpened
green, exactly. It reduces this scene's diagnostic pink count by 68.6% relative
to H, but leaves visible residual fringes. It is not a completed correction.

The second probe limits this cap to samples within one pixel of a green CFA
sample at or above its normalized physical-white limit. Both are research-only;
neither runs the noise guard after the new nonlinear clipping. Any future
integration would need an appropriate variance/censor policy, not the old noise
model applied without review.

The expanded probe covers **384 cases**: all four CFAs, a diagonal step and
repeated fine lines, four optical blur widths, two neutral background levels,
and neutral, green, magenta, red, blue and bright-magenta foregrounds. Scene
values are white-balanced linear camera RGB, not display RGB. No sensor noise
is added; normalization uses float64 and lens gains are unity. All variants
retain exactly the same native sharpened green.

The declared reference retains the known, physically white-clipped scene
R-G/B-G differences and adds that same sharpened green. It screens colour-
difference reconstruction; it is not an independent full-camera rendering or
perceptual quality oracle. Pink counts are informative only for neutral/green
fixtures, never an objective for the genuinely coloured fixtures.

Across the 32 clipped-neutral fixtures, mean pink fraction falls from 8.233%
with D to 0.497% with the early limit; mean R/B reference RMS falls from 0.01940
to 0.00841. But the unrestricted cap worsens R/B reference RMS in **106 of 320
coloured cases**, and the adjacent-green gate still worsens **72 of 320**.
For bright magenta against the clipped background, average RMS rises from
0.03217 to 0.07020 with the unrestricted cap, or 0.03966 with the gate. These
are concrete counterexamples to accepting a reduction in pink pixels alone.

Neither candidate passes coloured-edge nonregression. The five-RAW promotion
suite and Android integration are therefore not run for these rejected probes.
No noise strength, sharpness row, exposure or hue suppression mask is retuned.

## Remaining correction work

The next reconstruction correction must handle censored highlight samples
without introducing false R/B differences or corrupting genuine coloured edges.
It must pass the clipped-neutral and coloured fixtures, improve these original-
resolution crops, and then pass the existing multi-RAW regression suite before
an Android candidate is built. The current evidence isolates an added D-stage
failure; it does not close the entire fringe problem or validate a rollback.

Evidence: `results/fringe_164710_capture.json`, `results/clipped_edge_probe.json`,
`results/fringe_164710_replay.json` and `results/highlight_colour_probe.json`.
The capture fixture records input hashes; private image pixels are not added to
this repository.

```bash
python3 research/detail1a/clipped_edge_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/clipped_probe

python3 research/detail1a/fringe_replay.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/fringe_replay
```
