# M9DETAIL1B — finished-image sharpening comparison

21 September 2026. Continuation of DETAIL1A on the unchanged GL2G renderer.

The higher-ISO Sharp rows change the finished JPEG, and the historical 2× ISO
probe sacrifices more fine texture. The 1× probe is the less aggressive option
to carry into further evaluation. Neither ISO mapping is promoted, and reducing
sharpening is not implementation of Leica Noise2.

## Result

Five 4096×3072 RAWs were rendered with the current fixed ISO160 row, the 1×
physical-ISO probe and the historical 2× probe: fifteen full JPEGs. ISO50 from
15 Ultra and ISO104 from 17 Ultra are low-ISO controls; ISO521, 573 and 1142 are
15 Ultra main-camera captures. All inputs were recovered originals.

The following changes are measured on **decoded JPEG95 crops**, relative to
fixed ISO160. They use the same coordinates selected for DETAIL1A. High-frequency
RMS contains noise and scene detail; it is not a noise-reduction score.

| Sensor ISO | Probe | Leica row | Edge HF RMS | Edge gradient p95 | Quiet HF RMS |
| --- | --- | --- | --- | --- | --- |
| 521 | 1× | 500 | −5.81% | −3.77% | −10.70% |
| 521 | 2× | 1000 | −10.22% | −9.13% | −17.34% |
| 573 | 1× | 640 | −22.69% | −16.29% | −21.51% |
| 573 | 2× | 1250 | −23.89% | −17.68% | −22.73% |
| 1142 | 1× | 1250 | −26.65% | −20.56% | −26.03% |
| 1142 | 2× | 2500 | −36.04% | −28.02% | −27.09% |

At ISO1142, 2× loses substantially more edge contrast for little additional
quiet-crop HF reduction. Visual inspection confirms smoother but softer foliage
and shadow detail. Coloured artifacts remain in the shadow/edge crops. The
ISO521 window is defocused and cannot validate retention of in-focus detail.

The final render gain is **identical across all three variants in each scene**.
The higher-ISO candidates do move TC20's measured median slightly. Raw-tail
headroom limits the gain in these three scenes, so the median change does not
change their exposure placement. This finding does not establish invariance in
scenes where the median determines the gain.

| Sensor ISO | Final tone placement, all variants |
| --- | --- |
| 50 | +0.367862 EV |
| 104 | +0.500000 EV (tone bound engaged) |
| 521 | +0.125754 EV |
| 573 | +0.337531 EV |
| 1142 | +0.407220 EV |

Colour transforms are held fixed, but changed spatial samples still interact
with clipping and nonlinear colour/tone arithmetic. The largest whole-frame
mean channel shift in the decoded JPEGs is 1.0692 levels on the 0–255 scale
(ISO573, 2×, red). Whole-frame mean luma shifts by at most 0.4619 levels. These
small averages do not rule out local colour or fringe differences. At ISO1142,
zero-valued decoded channels decrease by 0.9549 percentage points with 1× and
0.9867 points with 2×.

## Executed path and checks

`downstream.py` adds a host runner for the frozen downstream path. The numerical
Java functions are extracted from `M9R35Renderer.java` and the unchanged Photon
`Converter.java`, then executed with Java 17. Camera2 metadata containers are
stubbed with each DNG's rational matrices, illuminants and neutral. The source
context function itself is unchanged. Android Rational float conversion is
preserved. Supported illuminants are restricted to D65/Standard A, the pair
present in these captures; other illuminants fail explicitly.

The sequence is:

1. DETAIL1A's black normalization and NORM030 reconstruction from DNG GainMaps.
2. The actual native CFA-aware detail stage, with only the Sharp row changed.
3. Saturating RGB16 representation-scale restoration using host OpenCV.
4. Native Camera2 source calibration, identity HSM, channel clipping and direct
   M9 target context from the exact Java methods.
5. OpenCV area resize to a 1600-pixel long side; original Java centre weights;
   literal native weighted-median/P98 kernel; original Java raw-tail and gain
   calculations; the exact GL2G ±0.5 EV tone-bound block.
6. Literal native `renderStripScalar`: SAT2 M04/M05, firmware curve02, TG1 and
   horizontal BT.601 4:2:2 arithmetic.
7. DNG orientation and one shared Pillow/libjpeg encoder, quality95, 4:2:0.

The renderer, native source and firmware curve are checked against the GL2G
manifest. Converter is independently hash-guarded and unchanged from Photon
upstream commit `f0e6425d2509fb8ab834d5d3af593183038b778c`.

Full-frame fixed-row versus candidate-slot0 checks compare **75,497,472 RGB16
samples and 75,497,472 RGB8 samples with zero difference**, across 15 Ultra RGGB
and 17 Ultra BGGR. Meter results are identical too. Serial and parallel colour
execution match, including odd-width inputs. The ISO50 and ISO104 variants have
identical final JPEG SHA256 hashes. All fifteen JPEG hashes and five comparison
PNGs were verified before packaging.

## Offline boundaries

- These older DNGs do not contain the current GL2G exposure-plan state. The
  replay explicitly uses neutral intent, zero edge-placement EV and the current
  disabled shaded guard. It does not reproduce the historical capture's JPEG.
- The DNG/Camera2 bridge and NORM030 equations are an offline metadata replay,
  not an independently verified capture-time HAL reconstruction.
- Host OpenCV restoration uses `addWeighted` with the same scale, zero second
  contribution and unchanged uint16 depth. Host OpenCV and floating-point
  rounding have not been bit-compared with the Android implementation.
- The shared JPEG encoder makes the candidate comparison controlled; it does
  not establish Android `Bitmap.compress` byte parity. RGB8 measurements before
  encoding are also retained in the report.
- There are no high-ISO 17 Ultra or telephoto captures in this evaluation, and
  no calibrated per-sensor ISO-to-Leica-noise mapping.
- No preview, application source, APK or production default changed. The
  existing MHC red/blue difference approximation remains. Noise2 remains absent.

## Reproduce

```bash
python3 research/detail1a/full_run.py \
  --assembled PhotonCamera \
  --firmware /absolute/path/m9-1_216.decrypted.upd \
  --out /absolute/path/detail1b-output \
  /absolute/path/15u-low.dng /absolute/path/17u-low.dng \
  /absolute/path/15u-521.dng /absolute/path/15u-573.dng \
  /absolute/path/15u-1142.dng
```

Requires DETAIL1A's dependencies plus OpenCV and Java 17 with `jdk.compiler`.
The compiler is invoked through `java com.sun.tools.javac.Main`. Generated
Java/C++, firmware tables, binaries, assembled source and photos stay outside
the commit. `results/full_report.json` records all source and JPEG hashes,
camera contexts, preprocessing metadata, gain decisions and tile measurements.

## Next decision

Keep fixed ISO160 as the production control. Carry 1× as the gentler research
candidate; do not generalize 2× across sensors. Prioritize recovery/testing of
the actual Noise2 packed-difference filtering path independently of Sharp.
Before a phone candidate is promoted, evaluate in-focus faces, fabric/fur and
shadow texture, including high-ISO 17 Ultra and telephoto inputs.
