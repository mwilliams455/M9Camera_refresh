# Fringe stage trace and coherent-green controls

21 September 2026. **Most flagged pink pixels already have an R/B excess
before colour conversion. Replacing green along with R/B does not improve the
photograph, and combining a common white limit with DCB still damages genuine
coloured edges. No accepted correction or new APK.**

This follows `GREEN_SUPPORT_AND_LOCAL_FITS.md`. The earlier fixed-green local
DCB result remains a research control with unresolved regressions. Native
green/fixed ISO160 Sharp remain the app's foundation. Auto exposure remains
unresolved and user-deferred; no exposure setting or metering is retuned here.

## Exact downstream stage audit

`fringe_stage_audit.py` compiles the same hash-verified colour source and calls
its actual `cameraToM9` and `m9CurvePixel` functions. It records curve02 RGB8
before the final BT.601/TG1 pair operation, then compares it with the unchanged
full render. **The context stays on SAT2, mode9, throughout.** It does not use
mode8 as a bypass: that shared diagnostic mode also changes the saturation-bank
selection in the frozen source and would confound this comparison.

An independent NumPy transcription of the pair arithmetic reproduces all
**188,743,680 RGB samples** from the five rendered variants exactly. Selected
per-pixel traces also reproduce the corresponding pre-pair RGB8 values exactly.
These checks concern this host replay, not hardware/Android/JPEG byte parity.

The same exact 16:47 DNG, recorded live Camera2 noise profile and render gain
1.4142135623730951 are used. All eight H phone guard statistics remain exact.
The diagnostic is still pre-JPEG `min(R,B)-G > 15` with RGB sum >300, never a
processing mask or an accuracy measure for real magenta objects.

| Stage count | Current H | Previous local DCB |
| --- | ---: | ---: |
| Flagged after curve02, before pair operation | 180,981 | 86,680 |
| Flagged in final RGB8 | 174,776 | 66,712 |
| Flagged at both stages | 141,728 | 52,412 |
| Newly flagged after pair operation | 33,048 | 14,300 |
| No longer flagged after pair operation | 39,253 | 34,268 |

The pair operation redistributes colour between neighbours; it does not
eliminate the fringe. Its net diagnostic count decreases in these replays, so
it is not the main origin of the existing pink signal. This does not prove
that every pair-induced colour change is harmless or optically correct.

For pixels flagged in each variant's **final** image, the camera RGB entering
colour conversion is divided by the capture neutral for a WB-normalized
diagnostic. `min(R/nR,B/nB)-G` is positive at **92.713%** of H's flagged pixels
and **91.574%** of the local DCB control's flagged pixels; it exceeds 0.02 at
83.365% and 74.417%, respectively. This is evidence of a predominantly upstream
signal, not proof that the colour matrices/tone curve have no effect.

The report also retains camera-white-capped, PP, M9, gain-limit and curve
samples. Their channel bases differ: their numerical differences are not
interchangeable error scores or percentage-amplification measurements. The
gain-limit point is a float pre-rounding diagnostic. All stage statistics are
conditioned on the same variant's final pink mask, not the whole photograph.

## Coherent-green experiment

`coherent_green_probe.py` tests whether keeping the original green plane is
preventing an otherwise useful R/B interpolation from working. DCB remains an
independent control, not recovered Leica processing. The WB-neutralized
headroom encoding, clipping-distance4..8 local blend and ten-pixel perimeter
are retained; H/D remain outside the support.

- **Fixed green:** the previous DCB R-G/B-G transfer onto native sharpened G.
- **Coherent RGB:** use the DCB channels together, with no added sharpening
  inside the full-weight region. This changes green and serves as a diagnostic.
- **Coherent RGB, native Sharp recomputed:** run the same native ISO160 Sharp
  routine on q14 DCB green, then add the resulting common offset to all three
  WB-normalized channels. The input to Sharp is different.
- **Coherent RGB, original native detail:** retain the original correction
  `nativeSharpG - nativePreSharpG`, add it to all three DCB channels, and keep
  the DCB green foundation. This preserves that correction, not the original
  final green plane or its entire photographic appearance.

| Photographic replay | Flagged pink pixels | Green pixels changed from H |
| --- | ---: | ---: |
| Current H | 174,776 | 0 |
| Previous fixed-green local DCB | 66,712 | 0 |
| Coherent RGB | 82,377 | 2,822,361 |
| Coherent RGB, Sharp recomputed | 106,720 | 2,793,010 |
| Coherent RGB, original native detail | 87,421 | 2,745,773 |

All retain the perimeter and every H channel at clipping distance8 or more
exactly. Inspection of the same three original-resolution crops shows that
changing green does not clear the residual fringe. None of the coherent
variants beats the prior fixed-green control on this diagnostic.

## Known-colour screen

The new controls use the same **384 RGGB rejection cases**, not a new full
four-CFA promotion suite. The two old references remain unchanged: known
blurred scene RGB clipped channelwise to 0..1, and known scene colour
differences added to the original native G. The old fixed-green reference is
retained as a historical comparison; it is not relabelled as ground truth for
the deliberately changed green variants.

An additional **scene-chroma RMS** compares reconstructed `(R-G,B-G)` with the
known scene's `(R-G,B-G)` after channelwise clipping. It checks colour residuals
without prescribing the old green plane. It also has no native-sharpening or
perceptual reference. Neither averaging it nor improving full RGB RMS alone
establishes acceptance. Comparisons retain the previous 1e-12 tolerance.

| Control | Scene RGB failures /384 | Largest RGB RMS increase | Fixed-green R/B failures /384 | Scene-chroma failures /384 |
| --- | ---: | ---: | ---: | ---: |
| Previous fixed-green DCB | 4 | 0.00227591 | 63 | 58 |
| Coherent RGB | 4 | 0.00229362 | 86 | 52 |
| Coherent RGB, Sharp recomputed | 154 | 0.03655355 | 189 | 118 |
| Coherent RGB, original native detail | 97 | 0.02494979 | 130 | 79 |
| Prelimited fixed-green DCB | 77 | 0.04651317 | 93 | 90 |

The D and fixed-green DCB values reproduce their earlier report exactly.
For unblurred neutral lines against white, scene-chroma RMS is **0.05839135**
with D, **0.11962496** with coherent RGB, **0.11498243** with recomputed Sharp,
and **0.10395466** with the original native detail. Thus changing the green
reference does not rescue those variants. Recomputed Sharp also raises full
RGB RMS on sigma1 neutral lines from **0.02949801 to 0.06605155**. Using the
same sharpening function on a different interpolation input is not sufficient
to preserve its previous photographic behaviour.

## Pre-interpolation limit combined with DCB: also rejected

`prelimited_dcb_probe.py` tests the remaining interaction explicitly: apply the
previous common physical-white limit to the normalized Bayer input **before
DCB**, then transfer only DCB colour differences onto the original native G.
This differs from the prior native-D early-limit and DCB post-limit probes.
The fixture harness is reused with a single declared variant override.

It still fails. Sigma1 bright-magenta lines against very white rise from
full RGB RMS **0.02369933 to 0.07021250**. The fixed-green and scene-chroma
checks also retain substantial regressions. This control is rejected at the
fixture screen; no full-photograph render, larger tuning sweep or Android
implementation is justified for it.

## Consequence and reproduction

The evidence supports retaining the current native green/Sharp foundation
while investigating clipped-channel R/B reconstruction. The remaining pink
cannot be assigned mainly to JPEG encoding or the final pair operation, and
these coherent-green controls do not show that green must be replaced. A
subsequent correction needs to address the already-present upstream colour
residual while preserving actual coloured edges. The complete optical versus
interpolation contribution to every remaining fringe is still unresolved.

Reports: `results/fringe_stage_audit.json`, `results/coherent_green_probe.json`
and `results/prelimited_dcb_probe.json`. Source/RAW hashes, every fixture,
conditional stage statistics and preservation checks are retained. The
photographic script emits `Coherent-green-comparison.png` and five research
JPEGs. Photos, RAWs and generated native binaries are not added to the repo.
PR39 remains draft and unmerged; application source and defaults are unchanged.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/fringe_stage_audit.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/stage-audit

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/coherent_green_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --cfas 0 --out /absolute/path/coherent-screen

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/detail1a/prelimited_dcb_probe.py \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --cfas 0 --out /absolute/path/prelimited-screen
```
