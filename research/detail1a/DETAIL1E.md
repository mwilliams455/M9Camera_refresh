# M9DETAIL1E — recover and evaluate Noise2

21 September 2026. **The luma-disabled Noise2 modes used by Leica ISO160–1600
are now implemented as offline probes in the corrected DETAIL1D domain.**
They reduce colour noise in known-colour tests and in the five RAW replays, but
also remove real colour detail. The stronger ISO-indexed probe increases edge
chroma HF in the ISO573 capture. Neither setting is approved for phone output.
Keep DETAIL1D as the working R/B research baseline; production remains unchanged.

## Recovered source contract

The canonical firmware SHA256 is
`4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20`.
`noise2_evidence.py` verifies the canonical BF561 loader and LUTS resource,
extracts active call targets using GNU binutils 2.44, and emits normalized
instructions, per-function hashes, the table inputs, and a manifest in
`evidence_noise2/`. No firmware binary or generated application asset is added.
Overlapping stale map variants are excluded; the zero-sized `ASMBox9CDI` symbol
is bounded by its actual return instruction.

The loader at `feb1c638` copies `LUTS+0x200`, length `0x3f0`, to
`context+0x268`. `Set` at `feb1d1bc` then selects the noise controls and strength.
These addresses establish the table mapping, rather than inferring it from
plausible-looking values:

| Input | LUTS offset | Context field | Value or selector |
| --- | --- | --- | --- |
| Base noise strength | 0x200 | 0x268 / noise+0x30 | 31 |
| Attenuation divisor Q | 0x208 | 0x270 / noise+0x38 | 64 |
| Luma enable, five rows | 0x20c | 0x274 table → 0x238 | All zero except slot12 |
| Chroma mode, five rows | 0x310 | 0x378 table → 0x23c | 1,1,1,2,2,2,2,2,2,3,3,4,5 |
| ISO noise strength | 0x47c | 0x4e4 table → signed16 0x264 | 256,291,332,384,437,498,576,656,747,863,984,1121,1278 |
| Brightness weights | 0x4f0 | 0x558 / noise+0x320 | 256 positive bytes, descending from 16 to 2 |

All five menu rows of the luma and chroma selector tables are identical. The
probe supports slots0–10. Slots11/12 are rejected explicitly: modes4/5 and the
additional luma-noise branch have not been implemented here.

`Process_Noise` at `ff602bd0` selects these recovered separable filters. Their
samples have the same CFA phase, at **two-pixel spacing**, so R and B do not mix:

| Mode | Function | One-dimensional weights | Rounding after each pass |
| --- | --- | --- | --- |
| 1 | Gauss5CDI, ff60272c | [1,2,1] / 4 | Signed floor |
| 2 | ASMBox9CDI, ff600d48 | [1,2,2,2,1] / 8 | Fractional MAC extraction; see limitation below |
| 3 | Gauss13CDI, ff60246c | [1,2,3,4,3,2,1] / 16 | Signed floor |

The mode2 filter is not a uniform 9×9 average. The probe uses nearest-even MAC
rounding and also measures the alternative biased half-up behavior. The caller's
live ASTAT rounding state has not been established, so Blackfin bit equivalence
is not claimed. Modes1/3 use explicit arithmetic shifts and have no such choice.

The luma-disabled adaptive loop begins at `ff602ea0`. For original difference
`c`, filtered difference `m`, green `g`, power-of-two threshold `T=2^s`, and
`Q=64`, its mathematical form in the wider mobile domain is:

```
v = floor(abs(c-m) * brightness_weight[g >> 6] / 16)
if v < T:
    result = floor((v*c + (T-v)*m) / T)
else:
    z = floor(v/T)
    result = floor((Q-z)*c/Q) if z < Q else 0
```

Large residuals enter **colour attenuation**, not a simple keep-original edge
branch. The transition at `v=T` is discontinuous. This matters both to colour
detail and to rounding sensitivity: changing mode2's tie convention alters a
few branch decisions, with a maximum carrier difference of 60 and camera-channel
difference of 19 units in 14-bit space in the ISO573 replay. The affected RGB16
sample fraction is 3.49%; this is not dismissed as universal one-unit roundoff.

`CalculateNoiseParameter` at `feb1cd70` derives the threshold from ISO strength
and three WB coefficients. With `f=(iso_strength/256)*31` and positive
`sigma_i=truncate(WB_i*f/16384)`, it sets `E=max(sigma_R,sigma_B)^2+sigma_G^2`.
For positive E, `s=floor(log4(E))+2`; for zero E, s=1. The implementation follows
the float32 operation order. Although the map labels the conversion helper
`__float32_to_int32_round`, its actual instructions at `feb19c58` shift the
positive mantissa without adding a rounding offset: the used conversion
truncates. The instruction body, rather than the symbol name, determines this.

## Explicit mobile adaptations

The carrier is DETAIL1D's WB-normalized colour difference. The probe supplies
WB coefficients `round(16384/nr), 16384, round(16384/nb)` without uint16 wrap,
uses signed32 carriers and signed64 products, and restores camera-channel
scaling only after the R/B consumer. These are coherent units for this mobile
experiment, not a recovery of every Leica upstream WB scale, clip or overflow.
The original signed16 carrier/statistic narrowing is deliberately not reproduced
on bright mobile values. Neutral ratios are restricted to the audited range
1/16–16; the full-frame carrier must fit ±262144.

Native green and the actual native fixed ISO160 Sharp output remain exact.
Mode1/2/3 need carrier borders5/7/9, while the unchanged green+Sharp needs9.
The consumer retains the outer ten pixels from baseline. This independent
channel support policy is a mobile probe arrangement; it does not emulate the
firmware's shared, cumulatively incremented border counter.

The two probes are fixed Noise2 ISO160 and nearest Leica ISO to the recorded
sensor ISO. The latter selects 160,160,500,640,1250 for the five RAWs. It is an
ISO comparison, not a sensor noise calibration. Sharp remains ISO160 in both.
No colour transforms, exposure intent, JPEG encoder or quality setting change.

## Verification and quality finding

- 80,836 supported samples match an independent separable-filter/blend oracle,
  including all four CFAs, odd dimensions, wider signed values and both mode2
  rounding conventions. All three adaptive branches execute.
- 60 exact threshold-boundary cases cover positive/negative differences and
  the transitions at T and Q×T. Twelve constant-colour cases retain values
  outside int16 without desaturation; unsupported slots reject explicitly.
- All 36 known-neutral edge cases improve over corrected DETAIL1D. The worst
  new/old chroma-error RMS ratios are 0.839, 0.639 and 0.590 for slots0,5,9.
- Every candidate preserves 62,914,560 native green samples across the five
  RAWs, plus the baseline border. Supported green matches actual native Sharp.
- Twenty JPEG95 outputs include production and corrected DETAIL1D controls.
  All ten control hashes match DETAIL1D exactly. Render gains agree within
  3.21e-16 EV, and low-ISO fixed/indexed outputs are identical.

Known-colour synthetic scenes use green-domain R/B noise sigma100 and fixed
noiseless green. They expose the detail cost that a noise-only score would miss:

| True scene | Corrected, Noise2 off: R/B RMS error | Fixed ISO160 | ISO500 | ISO1250 |
| --- | --- | --- | --- | --- |
| Neutral flat | 43.97 | 29.77 | 20.23 | 16.76 |
| Coloured flat | 44.89 | 30.90 | 21.50 | 17.98 |
| Colour edge | 157.31 | 165.54 | 185.14 | 209.54 |
| Fine colour sine, period16 pixels | 93.75 | 165.01 | 291.47 | 400.18 |

Changes below use the same decoded JPEG crops, relative to corrected DETAIL1D
Co=2. Chroma HF includes true colour detail, noise and artifacts; it is not a
direct noise measurement on these photographs.

| Sensor ISO | Quiet chroma HF, fixed160 | Quiet chroma HF, indexed | Edge chroma HF, fixed160 | Edge chroma HF, indexed |
| --- | --- | --- | --- | --- |
| 50, 15 Ultra | −10.30% | −10.30% | −24.52% | −24.52% |
| 104, 17 Ultra | −11.75% | −11.75% | −13.80% | −13.80% |
| 521, 15 Ultra | −15.17% | −32.68% | −12.71% | −16.45% |
| 573, 15 Ultra | −17.53% | −31.06% | −0.74% | +3.28% |
| 1142, 15 Ultra | −22.14% | −40.10% | −8.33% | −7.41% |

Visual review of all five sheets shows reduced coloured speckle in the window
and shadow crops. Skin/hair and foliage retain the unchanged green detail, but
that does not prove preservation of colour detail. The stronger ISO573 probe
has more visible magenta edge activity and slightly softer foliage, consistent
with its edge metric and the synthetic colour-detail cost. ISO521 is defocused
and cannot establish in-focus detail retention. Whole-frame mean RGB changes
by at most 1.434 RGB8 units versus DETAIL1D; local accuracy requires more than a
mean statistic.

**Decision:** retain the corrected R/B domain and keep both Noise2 settings as
research probes. Reject automatic promotion of the ISO-indexed setting. The
fixed160 probe is gentler and improves the tested neutral fringes, but it still
loses true colour detail and is not approved as a finished output policy.
Next work should resolve the live mode2 rounding state and calibrate the mobile
noise/WB strength against repeat captures and colour-detail references, with
the ISO573 magenta boundary included as a regression case. Do not treat lower
chroma HF alone as the acceptance criterion or trade image quality for speed.
High-ISO 17 Ultra, telephoto and on-device validation remain outstanding.

## Reproduce

Use the same frozen GL2G assembly, native header and dependencies as DETAIL1D.
The existing host/Camera2 and neutral-exposure-intent limitations still apply.

```bash
python3 research/detail1a/noise2_evidence.py \
  /absolute/path/m9-1_216.decrypted.upd /absolute/path/bfin-objdump \
  research/detail1a/evidence_noise2
python3 research/detail1a/noise2_checks.py \
  /absolute/path/detail1e /absolute/path/m9_sharp_fulliso_bank.h
python3 research/detail1a/noise2_run.py \
  --assembled PhotonCamera --header /absolute/path/m9_sharp_fulliso_bank.h \
  --reference-report research/detail1a/results/rb_domain_report.json \
  --checks /absolute/path/detail1e/checks.json --out /absolute/path/detail1e/replay \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng /absolute/path/15u-1142.dng
```

The complete measurements are in `results/noise2_report.json`. Production
source, preview, defaults and APK are unchanged. This is not complete Noise2,
Blackfin hardware equivalence, Leica image parity or Android parity.
