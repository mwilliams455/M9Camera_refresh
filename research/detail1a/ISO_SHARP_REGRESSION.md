# ISO/sharpness regression history — 22 September 2026

Follow-up clarification: the user's specific "pink edging is back" report was
on 21 September following DETAIL1H. The active boundary is therefore GL2G -> H.
[`DETAIL_BOUNDARY_CAUSE.md`](DETAIL_BOUNDARY_CAUSE.md) now separates the two D
changes with exact endpoints. The older 12 September history below remains
background, rather than the starting point for the recent recurrence.

The active question is which recent integration introduced false colour. Treat
the ISO/sharpness sequence as a regression history before proposing another
interpolation or colour-suppression algorithm. DETAIL1D with Sharp disabled is
not a pre-testing baseline.

## Historical boundaries

| Boundary | Evidence | What it establishes |
|---|---|---|
| 12 September: CLOSURETEST1A/B | First closure integration `f06c7a6260030f4720ac291cd1d6de85114ea4a6`; `research/M9_SHARPNESS_RBCLOSURE1A_FINDINGS_20260912.md` | The contemporary report explicitly records a new green/cyan foliage halo exposed by CLOSURETEST1B. Frozen neutral-aware MHC with Sharp bypassed was cleaner on that regression frame. |
| 12 September: SHARPSOURCE1B/C | `patches/apply-m9cam-sharpness-sharpsource1c-rbanchor1a.py`, commit `f6aa2b4fbfa94d47122744a1082f26df787b5f08` | An equal camera-RGB offset transfers the Leica green/Sharp result onto MHC RGB. This is a mobile integration, not proof of equivalent Leica colour behaviour. |
| 21 September: DETAIL1A/B | `49b0070`, README and DETAIL1B | Offline ISO-row replay. Slots 0–2 reproduce the existing fixed ISO160 row exactly. The ISO schedule itself was not promoted by these offline tests. |
| 21 September: DETAIL1C/D | Rejected C `62861ef`; corrected-domain D `78075a36b01d722f8a42566f201752bddef75505` | New R/B reconstruction changes output while retaining the existing native green and Sharp exactly. Correcting C's units did not establish photographic nonregression for D. |
| 21 September: DETAIL1H | `0726b579055b0ffade7f18f8a8667efdf1333df5` and `patches/m9cam-m9detail1h.patch` | Phone integration applies D plus the guard after native demosaic. Disabling the guard retains D; it does not restore pre-DETAIL native R/B. |

The 12 September report distinguishes an even older magenta/OpenCV-EA issue
from the new CLOSURETEST1B green/cyan issue. These should not be collapsed into
one historical cause. The user's exact last visually accepted APK has not been
re-established here.

## New controlled regression replay

`iso_sharp_regression_probe.py` compares six historical/internal controls over
1,536 known-scene cases and all four CFA layouts. The primary control is the
actual frozen GL2G native RGB output, including its pre-existing Sharp. The
earlier internal MHC stage is labelled as a mathematical-stage control, not an
entire historical APK replay.

Native source SHA256:
`23037daba9fe5acbffb68f4bdf1fdce394eb476d7312ef0b57d514678b95a1bc`.

| Compared with GL2G native | False-magenta cases worse | False-green cases worse | Mean magenta excess fraction | Mean green excess fraction |
|---|---:|---:|---:|---:|
| GL2G native | — | — | 0.145762 | 0.038769 |
| DETAIL1C (already rejected) | 1,028 | 963 | 0.179390 | 0.072504 |
| DETAIL1D | 1,138 | 336 | 0.173189 | 0.035846 |
| DETAIL1D, Sharp off | 988 | 630 | 0.172737 | 0.047705 |

Counts are out of 1,536. D's average green excess falls, despite individual
green regressions. These are known-scene error metrics, not colour classification
of a photograph. The suite uses one fixed neutral and fixed native Sharp row;
it is not an exhaustive ISO/illuminant sweep. See the inherited scene generation
and metric definitions in `true_mhc_factorial.py`.

All four matching controls reproduce the earlier factorial metrics within
1e-14. C and D preserve every native green sample exactly. The historical
uniform camera-RGB offset equation reproduces native GL2G RGB byte-for-byte
inside its nine-pixel support boundary in all 1,536 cases.

## Why the early Sharp integration remains implicated

The historical integration adds an equal offset `delta` to camera R, G and B
before later white balance. For channel neutrals `nR` and `nB`, its unclipped
effect on white-balanced colour differences is:

```
change(R / nR - G) = delta * (1 / nR - 1)
change(B / nB - G) = delta * (1 / nB - 1)
```

When both neutrals are below one, positive offsets produce magenta-direction
chroma and negative offsets produce green-direction chroma. Preserving raw
camera `R-G` and `B-G` does not preserve white-balanced chroma. The synthetic
audit verifies the equation for both signs. This identifies a colour-unit
mismatch in the mobile adapter, not a faulty recovered Sharp coefficient table.
Clipping, rounding and later colour conversion add further effects. The script's
scaled-offset arithmetic example is an invariant illustration, not a candidate
renderer or an accepted correction.

## Same-RAW confirmation and remaining boundary

The previously recorded woodland result in `DETAIL1H_PHONE_FRINGE.md` was
reproduced independently with the historical native RGB primary control. All
eight H guard statistics and the previously saved H host JPEG are exact.
New photo-derived evidence remains private. The published original result
already demonstrates that D/H adds pink fringe relative to GL2G at unchanged
green, Sharp, gain and downstream colour. GL2G itself still contains the older
Sharp integration, so it must not be described as the clean pre-sharpness APK.

The next isolation must restore the complete pre-Sharp MHC output as one
control and then add the historical Sharp/green/RB integrations in order. For
the later DETAIL regression, bypassing the entire D/H R/B overwrite restores
the pre-DETAIL native result; bypassing Noise2 alone does not. This investigation
does not change the phone app, TG2, exposure, tone or colour calibration. No
new demosaic candidate is promoted.

## Reproduction

From the repository root, with the frozen GL2G source assembled and the prior
true-MHC factorial full report available:

```bash
python research/detail1a/iso_sharp_regression_probe.py \
  --assembled /path/to/frozen/PhotonCamera \
  --prior-report /path/to/true_mhc_factorial/report.json \
  --out /path/to/iso_sharp_regression
```

`results/iso_sharp_regression_summary.json` retains the aggregate results,
source hashes, exact-control assertions and signed colour-unit audit. Full
case-level results and the private photographic replay are preserved in the
separate evidence package.
