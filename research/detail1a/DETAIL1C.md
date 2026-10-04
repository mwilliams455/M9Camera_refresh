# M9DETAIL1C — partial red/blue reconstruction

21 September 2026. **Do not promote this candidate.** The recovered pre-Noise
carrier and final R/B interpolation produce stronger green/magenta edge fringes
when inserted into the current GL2G path with Noise2 bypassed. The regression is
already present with the colour-difference shrink disabled. This closes a useful
negative experiment and identifies the next integration work; it does not show
that Leica's complete pipeline has the same defect.

## What was recovered

The existing application uses sharpened Leica green plus full-resolution
neutral-aware MHC R−G and B−G differences. The firmware consumer has a different
input contract. The recovered path is:

1. Form green at native R/B sites from the four cardinal greens, divided by four.
   At G sites, use `(4*G + four diagonal greens)/8`. These are the same equations
   already used for the application's Leica Sharp source.
2. At G sites, retain `abs(filteredGreen - rawGreen)`. At each native R/B site,
   sum those four cardinal residual magnitudes to obtain unsigned uncertainty
   `a`. The producer computes signed `d = rawColour - interpolatedGreen`.
3. The Run call explicitly supplies `nCo=2`. If `abs(d) < a`, replace the
   magnitude with `max(abs(d) - (a >> 2), 0)`, retaining its sign. Otherwise keep
   `d`. The comparison is strict; this is not a universal chroma subtraction.
4. Diagonally average the native differences onto the **opposite R/B CFA phase**.
   The destination is the former raw allocation, `frame+0x34`. Red differences
   now occupy blue sample positions, and blue differences occupy red positions.
5. `Process_Noise` acts on that carrier. Its full Noise2 filter and adaptive
   combination are still unported and are explicitly bypassed in this probe.
6. `ASMRedBlueInterpolation1` reads the carrier plus sharpened green. Its two
   traversals interpolate the two complementary phases and clamp the sum to
   0…16383. A missing sample on both axes uses horizontal pair averages first,
   followed by a vertical pair average. Negative shifts use arithmetic floor;
   one flat four-sample average can differ by one unit.

This corrects the earlier shorthand that treated `frame+0x40/+0x44` as independent
full R−G/B−G planes. `frame+0x40` first holds interleaved native differences;
`frame+0x34` holds the cross-phase carrier consumed later. Buffer identities
must be tracked by stage because the firmware reuses allocations.

The consumer also increments the support counter: Sharp's recovered support 9
becomes 10. The experiment preserves the baseline's outer ten pixels and changes
only R/B inside. This establishes a candidate support requirement; no application
border policy was changed.

## Evidence anchors

The normalized instruction excerpts in `evidence_rb/` preserve addresses and
parallel instruction bundles. Its manifest records the original disassembly
hashes and the transformation applied. The source is the existing
[RBCLOSURE1A workflow artifact](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/34695003096),
artifact 10298570662, ZIP SHA256
`2f5591eeaebb58e24e97adc37a1ae0aed78b0514b711f5a88dc1d539b91e3302`.
No firmware binary or unrelated functions are included.

| Contract | Instruction anchors |
| --- | --- |
| Literal Co=2 and raw/green/work/difference arguments | Run `ff61097a`–`ff61099c` |
| Green, residual and cross-phase filter call setup | GreenInterpolationWithCo `ff613558` |
| Unsigned input loads; signed difference; uncertainty shift; strict magnitude gate | `ffa00052`–`ffa00094` |
| Signed four-diagonal filtering, fractional coefficient 0x2000 and truncation | `ffa0024e`–`ffa00354` |
| Consumer support increment | `ffa0344a`–`ffa03450` |
| First phase and horizontal-then-vertical halfword averages | `ffa03480`–`ffa03550` |
| Mirrored second phase | `ffa03558`–`ffa0362e` |

Arithmetic is interpreted from GNU disassembly. C++ is checked against a
separate address-based consumer oracle and vectorized producer equations, not
against Blackfin hardware. These checks establish internal consistency and
catch phase/rounding mistakes; they cannot exclude a shared interpretation error.

## Same-RAW result

Five 4096×3072 captures produce fifteen full JPEG95 images: baseline, recovered
carrier without shrink, and recovered carrier with Co=2. Green and fixed
ISO160/Standard mode 4 ×2 Sharp are held constant. All variants use the same
source colour, SAT2/curve02, tone path and JPEG encoder as DETAIL1B.

The table shows change in **decoded JPEG edge-crop chroma high-frequency RMS**
relative to the baseline. Chroma is `(R−G, B−G)` in decoded RGB8, with a sigma 1
Gaussian residual. It contains real colour detail, noise and artifacts; it is
not a calibrated false-colour or noise-only score.

| Sensor ISO | Carrier, no shrink | Carrier + Co=2 | Native differences changed by shrink |
| --- | --- | --- | --- |
| 50, 15 Ultra | +105.71% | +87.99% | 35.25% |
| 104, 17 Ultra | +89.15% | +86.58% | 6.80% |
| 521, 15 Ultra | +107.50% | +107.50% | 26.41% |
| 573, 15 Ultra | +76.24% | +65.04% | 17.83% |
| 1142, 15 Ultra | +75.57% | +76.58% | 41.08% |

Visual inspection of all five comparison sheets supports rejection: foliage/sky
edges show stronger green and magenta fringes; the ISO521 defocused window has
more coloured speckle; the low-ISO 17 Ultra skin/hair crop also shows added green
at its bright boundary. The shrink reduces some edge colour excursions but is
not sufficient and increases magenta in some shadow/foliage areas.

At ISO1142, Co=2 quiet-crop luma HF rises 34.57% and chroma HF rises 39.95%.
The pre-colour green plane is identical, but changing R/B still changes final
luma and green through the colour matrix, clipping and tone path. Thus holding
the Sharp table fixed does not imply identical finished-image texture.

Final render gains agree within `3.21e-16 EV`; all differences at ISO104 are
floating-point roundoff. The maximum absolute whole-frame mean channel shift
for Co=2 is 2.173 RGB8 levels, at ISO1142 red. Small mean shifts conceal large
local edge defects.

## Checks completed

- All four CFA layouts: independent producer equations, 16 constant-colour
  cases, crop phase translation, unchanged green and unchanged border10.
- 19,744 signed consumer samples match the independent two-traversal oracle,
  including odd dimensions, negative averages and final clamps.
- 62,199,760 supported green samples match the actual frozen native green+Sharp
  implementation on the five full frames.
- Each candidate preserves 62,914,560 full-frame native green samples exactly.
- All five baseline JPEG hashes match DETAIL1B byte for byte. All fifteen new
  JPEG hashes were verified; all five comparison sheets were visually inspected.

## Boundaries and next priorities

This is a **partial reconstruction probe**, not a Noise2 implementation or full
Leica parity. The current NORM030 sensor input is converted to 14-bit camera
values; the correct relationship to Leica's upstream white balance and scaling
has not been established. Both this domain adaptation and the omitted Noise2
stage are unresolved. The present comparison does not isolate which is
responsible for each defect.

1. Trace the upstream domain into `GreenInterpolationWithCo`, including WB,
   scaling and clipping, and verify it against the current camera-native input.
   Preserve the strict Co gate and cross-phase geometry as explicit contracts.
2. Port the actual Noise2 carrier filter and adaptive combination between the
   recovered producer and consumer. Audit coefficients, signed widths, clamps,
   phase layout and support. Evaluate it with the same Sharp and baseline gains.
3. Require clean foliage/sky edges, bright skin/hair boundaries and shadow
   texture before reopening Sharp ISO mapping. Add high-ISO 17 Ultra and telephoto
   coverage before a sensor-wide policy or phone candidate is promoted.

No production source, default, APK or preview changed. The MHC difference
baseline remains the control. The 1× Sharp mapping remains an earlier research
candidate, and this result supplies no new reason to adopt 2×.

## Reproduce

Requires DETAIL1B's assembled hash-verified sources/dependencies and the Sharp
header generated from the already-verified M9 firmware.

```bash
python3 research/detail1a/rb_probe.py /absolute/path/probe-build
python3 research/detail1a/rb_run.py \
  --assembled PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/detail1c-output \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng \
  /absolute/path/15u-1142.dng
```

`results/rb_report.json` retains input identities, preprocessing metadata, gain
decisions, native checks, RGB8 measurements and output hashes. The neutral
exposure intent, DNG/Camera2 replay, host OpenCV and JPEG95/4:2:0 limitations from
DETAIL1B remain. Full JPEGs and comparison sheets are delivered separately.
