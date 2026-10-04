# M9DETAIL1D — correct the R/B difference domain

21 September 2026. **The added DETAIL1C green/magenta fringe is substantially
removed in the five tested offline replays.** The correction aligns R/B with
green before producing colour differences and restores camera-channel scaling
after reconstruction. Native green, ISO160 Sharp, colour transforms, exposure
policy and JPEG encoding stay fixed. Noise2 remains unimplemented.

This is a correction to the research reconstruction. No application source or
APK was changed. It is not a claim of complete Leica firmware equivalence or
absence of all colour artifacts in arbitrary scenes.

## Cause and correction

Let `nr=AsShotNeutral[R]/AsShotNeutral[G]` and similarly `nb`. A neutral scene
has camera-channel values approximately `(nr*L, L, nb*L)`, not equal raw RGB.
DETAIL1C formed `R-G` directly in this unequal-gain camera domain. Even for a
neutral scene that difference is `(nr-1)*L`: it contains brightness structure.
Spatially filtering it and adding it to a differently filtered/sharpened green
therefore creates chroma around edges.

Ignoring quantization, clipping and the nonlinear Co gate, write the difference
interpolation as `T` and sharpened green as `SG`. The failed red reconstruction
on an ideal aligned neutral signal is:

```
R_old = SG + (nr - 1) * T(L)
R_old/nr - SG = (1/nr - 1) * (SG - T(L))
```

The right side is nonzero at detail/edges whenever the two brightness signals
differ. This explains why leaving the green/Sharp output fixed did not prevent
the regression. B has the same problem with `nb`.

The corrected contract is:

```
Dn_R = round(rawR14 / nr) - green14
Dn_B = round(rawB14 / nb) - green14
Dn   = recovered Co=2 shrink, when enabled
Cn   = opposite-phase diagonal average and final two-pass interpolation
R14  = clamp14(round(nr * (sharpGreen14 + Cn_R)))
B14  = clamp14(round(nb * (sharpGreen14 + Cn_B)))
```

The Co threshold now operates in the same green-normalized units as its green
uncertainty. Red and blue are restored to camera space before the existing
source colour matrix; the downstream renderer does not receive a second WB.
There is no hue mask, selective desaturation, exposure offset or new blur.

Neutralization can exceed the original 14-bit range. The mobile probe uses
signed 32-bit differences and signed 64-bit sums, then clamps only after returning the
reconstructed channels to camera space. Clamping the intermediate neutralized
red/blue to 14-bit would lose bright-channel headroom. This wider representation
is an explicit mobile adaptation; exact Leica upstream gains, headroom scale,
rounding and clamps are not claimed recovered by this change.

The firmware dispatch supports auditing this boundary: the added
`evidence_rb/Run_WB_before_green.asm.txt` shows enabled bit 3 calling
`Process_WB` with `frame+0x34`, returning to dispatch before bit 4 invokes
`GreenInterpolationWithCo`. The original disassembly and excerpt hashes are in
the result report. Function-address order alone was not used as execution order.

## Falsification and arithmetic checks

The same synthetic neutral scene is sampled through all four Bayer layouts,
three unequal R/B response pairs and three smooth edge orientations: 36 cases.
Its true chroma is known. Green and the actual native Sharp output stay fixed.
The measured error is RMS of `R/nr-G` and `B/nb-G` in green-domain 14-bit units.
The corrected-to-failed RMS ratio is at most 0.065680: at least 93.43% less false
colour error in every case. Remaining error includes Bayer interpolation and
quantization, so exact zero is not claimed.

Additional checks pass:

- Eight unity-neutral controls reproduce the original probe bit for bit with
  shrink enabled and disabled, isolating domain conversion from spatial math.
- 48 constant-colour cases preserve camera RGB within one 14-bit unit, including
  strongly non-neutral colours. The correction does not force all colours grey.
- Four bright-channel cases retain differences above signed 16-bit range without
  premature clipping.
- Independent vectorized producer equations cover all four CFA layouts.
- 21,600 wider signed consumer samples match an independent vectorized oracle,
  including unequal channel scales and final camera-space clamps.
- All full-frame candidates preserve 62,914,560 native green samples each; the
  outer ten pixels also remain baseline. 62,199,760 supported green samples
  match the actual frozen native green+Sharp implementation.

These checks verify the mobile implementation and neutral-invariance repair.
They do not establish Blackfin hardware equivalence or recover Noise2.

## Full JPEG comparisons

Five 4096×3072 RAWs were rendered into 20 JPEG95 files: the production MHC control,
failed DETAIL1C Co=2 probe, corrected domain without shrink, and corrected domain
with Co=2. The three-column sheets show control / failed / corrected Co=2.
Both old controls match their DETAIL1C JPEG SHA256 hashes exactly in all five
scenes. Final render gains agree within 3.21e-16 EV (floating-point roundoff).

Changes below are measured on the same decoded JPEG edge crops. Chroma HF RMS
is the sigma 1 Gaussian residual of `(R-G, B-G)`; it includes real colour detail,
noise and artifacts. This metric supports the visual comparison but is not a
noise-only score or a substitute for a known-colour reference.

| Sensor ISO | Corrected Co=2 vs failed: chroma HF | Corrected Co=2 vs production: chroma HF | Corrected vs production: edge-gradient p95 |
| --- | --- | --- | --- |
|50,15 Ultra |−79.22% |−60.93% |+2.99% |
|104,17 Ultra |−50.40% |−7.46% |+3.57% |
|521,15 Ultra |−62.51% |−22.21% |−2.78% |
|573,15 Ultra |−48.31% |−14.68% |+1.07% |
|1142,15 Ultra |−60.83% |−30.83% |+2.83% |

Visual inspection of all five sheets shows the added green/magenta foliage/sky
rings largely removed, a cleaner bright boundary in the 17 Ultra skin/hair crop,
and reduced coloured speckle in the defocused ISO521 window. The corrected
no-shrink control also reduces edge chroma HF in every capture. This isolates
domain correction as beneficial independently of the Co shrink.

The corrected Co=2 variant shifts whole-frame mean channels by at most 0.734
RGB8 levels from the production control. This small mean shift does not prove
local colour accuracy; the edge sheets and constant-colour tests are retained.
At ISO1142, quiet-crop chroma HF is 26.32% below production and luma HF is 6.56%
below production. Other quiet crops still show texture/noise changes: for
example, ISO104 quiet luma HF is 21.68% above production despite lower chroma HF.
The ISO521 scene is defocused and cannot validate in-focus texture retention.

## Next integration boundary

Keep this corrected domain contract for continuing R/B work. Do not carry the
failed camera-domain subtraction into a phone candidate. The recovered Noise2
carrier filtering/adaptive combination remains the next implementation task,
with coefficients and thresholds audited in the same normalized signal units.
Full Leica upstream WB and fixed-point scaling remain distinct research gaps.
The mobile correction is supported by neutral invariance and the same-RAW tests;
it is not presented as an exact emulation of that upstream firmware stage.

The production app still uses its MHC difference baseline. Phone integration,
Android parity, high-ISO 17 Ultra and telephoto validation are outstanding. This
change does not select a Sharp ISO mapping or trade image quality for speed.

## Reproduce

Use the same hash-verified GL2G sources, firmware-derived Sharp header and
dependencies as DETAIL1B/C. The older DNGs retain the same offline neutral-intent
exposure and host OpenCV/JPEG limitations documented there.

```bash
python3 research/detail1a/rb_domain.py /absolute/path/detail1d/native
python3 research/detail1a/rb_domain_synthetic.py \
  /absolute/path/detail1d /absolute/path/m9_sharp_fulliso_bank.h
python3 research/detail1a/rb_domain_run.py \
  --assembled PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --reference-report research/detail1a/results/rb_report.json \
  --synthetic-report /absolute/path/detail1d/neutral_edges.json \
  --out /absolute/path/detail1d \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng \
  /absolute/path/15u-1142.dng
```

`results/rb_domain_report.json` contains the input/source identities, all 36
synthetic results, arithmetic checks, full-image/crop measurements, gain
decisions and 20 JPEG hashes. The full JPEGs and five comparison sheets are
delivered separately.
