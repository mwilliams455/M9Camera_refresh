# M9 SHARPSOURCE1A — OFFLINE RESULT

Date: 2026-09-12
Branch: `research/sharpness-rbclosure1a-forensics`
Production renderer: **unchanged / frozen**

## Question

The CLOSURETEST1B APK applies the recovered Leica ISO160 / Standard x2 Sharp path to the frozen neutral-MHC green plane, then reconstructs R/B from full-resolution MHC colour differences. The regression frame showed green/cyan foliage/sky halos and heavy R/B zero clamping.

The firmware proves that Leica Sharp consumes `frame+0x3c`, the green signal produced by `GreenInterpolationWithCo`. It does **not** prove that the mobile neutral-MHC green plane is signal-equivalent to that Leica green signal.

SHARPSOURCE1A tests whether the sharpness **source domain** is a major part of the defect while preserving the validated MHC RGB foundation.

## Recovered green arithmetic

### Missing-green colour CFA sites

`ASMFilter_010_101_010_2` generates the coefficient as `1 << (16-2) = 0x4000` and uses unsigned-fraction multiplies. This resolves to:

`G = (N + S + W + E) / 4`

### Measured-green CFA sites

`ASMFilter_101_040_101_An` uses unsigned-fraction coefficients `0x2000` and `0x8000`, resolving to:

`G = center/2 + (NW + NE + SW + SE)/8`

At a Bayer green site the four diagonal sites are also green. The same BF561 routine also produces the absolute residual/guide used later by `ASMRedBlueAndGreenDiffer`.

## Interior CFA phase routing — now closed

Symbolic tracing of the `GreenInterpolationWithCo` caller resolves the start offsets of the first four green-producing calls.

Let `W` be the row width and `s` the current diagonal phase index. The first two `ASMFilter_010_101_010_2` calls start at linear pixel offsets:

- `(W + 1) * s`
- `(W + 1) * (s + 1)`

These correspond to image coordinates `(s,s)` and `(s+1,s+1)`: the two main-diagonal Bayer colour phases (R/B for RGGB, with exact R-vs-B identity depending on origin phase).

The two `ASMFilter_101_040_101_An` calls start one column adjacent to those diagonal positions:

- `(W + 1) * s + 1`
- `(W + 1) * (s + 1) - 1`

These are the two green CFA phases.

The later pair of `ASMFilter_010_101_010_2` calls operate in-place on the `frame+0x38` guide buffer before `ASMRedBlueAndGreenDiffer`; they are not a second write to the Sharp green source.

Therefore the **interior** `frame+0x3c` green topology used by SHARPSOURCE1A is now firmware-supported:

- R/B sites: cardinal four-neighbour green average /4
- Gr/Gb sites: center /2 + four diagonal greens /8

Remaining parity work is border/tile traversal and exact packed boundary behavior, not the interior CFA phase assignment.

## Signal-domain seam

The BF561 stages operate on the stored 14-bit signal. SHARPSOURCE1A was rerun with the Xiaomi RAW first mapped into the Leica 14-bit domain, then the recovered integer green filters applied.

This produced almost the same result as the earlier 16-bit-filter-then-quantize replay, so the finding is not a quantisation-placement artifact.

## Mobile-source-adapter discriminator

The experiment intentionally does **not** replace the frozen MHC RGB image.

1. Generate frozen neutral-MHC RGB exactly as CLOSURETEST1B.
2. Map the Xiaomi RAW into Leica 14-bit.
3. Independently construct the firmware-derived interior green source above.
4. Apply the existing recovered ISO160 / Standard x2 Sharp reference to that green source.
5. Compute `sharpDelta = sharp(G_leica_green) - G_leica_green`.
6. Apply the same `sharpDelta` to frozen MHC R, G, and B.

This preserves the frozen MHC colour differences and uses the Leica green signal only to determine the Sharp correction.

This is a **mobile source adapter diagnostic**, not a claim that Leica itself mixes MHC RGB with this green source.

## Regression RAW

`IMG_20260912_124558_1789213558532_00.dng`

RGGB, 4096 x 3072. Seven 512x512 tiles were selected automatically: six highest edge-stress tiles plus one low-edge control. Metrics exclude a six-pixel tile margin, so the current unresolved BF561 border traversal does not drive the comparison.

## 14-bit-first result

Mean across seven tiles:

| Metric | CLOSURETEST1B | SHARPSOURCE1A | Change |
|---|---:|---:|---:|
| R == 0 | 17.9224% | 11.6153% | -35.2% relative |
| B == 0 | 17.4637% | 11.7929% | -32.5% relative |
| edge R == 0 | 25.0346% | 16.2931% | -34.9% relative |
| edge B == 0 | 19.6167% | 13.0540% | -33.5% relative |
| cyan pixels | 0.05137% | 0.03754% | -26.9% relative |
| edge cyan | 0.32215% | 0.23184% | -28.0% relative |
| R max clamp | 0% | 0% | unchanged |
| B max clamp | 0% | 0% | unchanged |

The earlier 16-bit-first replay produced edge R-zero `16.2983%` and edge cyan `0.23107%`; the 14-bit-first values are `16.2931%` and `0.23184%` respectively. The difference is negligible.

The worst foliage/sky tile also remains materially improved relative to CLOSURETEST1B.

## Rejected controls

The following did **not** solve the problem and should not be promoted:

- full-resolution MHC `R-G/B-G` closure by itself (CLOSURETEST1B)
- simple CFA-phase-native bilinear colour-difference reconstruction
- the recovered `ASMRedBlueAndGreenDiffer` limiter followed by that bilinear scaffold
- applying only the recovered limiter to completed MHC full-resolution colour differences
- replacing MHC green outright with the one-stage cardinal-green proxy

The last control reduced some clamps but increased cyan-edge incidence overall; it is not the recommended direction.

## Interpretation

SHARPSOURCE1A is the strongest discriminator so far that the new green/cyan halo is substantially a **Sharp source-domain mismatch**.

The recovered Leica x2 LUT/kernel can be correct while producing the wrong photographic behaviour when fed a green signal with different high-frequency semantics. Neutral-MHC remains the validated demosaic foundation; the evidence does not justify weakening the Leica Sharp LUT or undoing MHC.

The promising mobile architecture is:

`frozen neutral-MHC RGB`

plus

`firmware-derived Leica green source -> Leica Sharp -> sharp correction`

then apply that correction to the frozen MHC RGB.

## Status / fidelity boundary

Firmware-proven or now strongly closed from the BF561 arithmetic/caller:

- Sharp consumes Leica `frame+0x3c`.
- final R/B reconstruction consumes the sharpened green/base.
- `010/101/010` coefficient/normalisation behavior.
- `101/040/101` coefficient/normalisation behavior.
- interior colour-site vs green-site phase routing of those two filters.
- later `010/101/010` calls act on the guide path, not the Sharp green plane.
- packed/interleaved colour-difference architecture.
- recovered edge-aware colour-difference limiter and shift 2.

Still open:

- exact BF561 border/tile traversal parity.
- full bit-for-bit `GreenInterpolationWithCo` scalar emulation around boundaries.
- using the Leica green only as a Sharp source while retaining MHC RGB. This remains a deliberate Xiaomi/mobile adapter rather than an original-Leica architecture claim.

## Next gate

Do **not** build a new APK yet.

Next:

1. replay SHARPSOURCE1A against additional known pathological RAWs (especially prior foliage/sky/magenta cases and ordinary detail controls);
2. ensure the source adapter does not reintroduce the demosaic magenta defect or visibly reduce fine detail;
3. optionally close exact BF561 border traversal for completeness;
4. if the multi-RAW replay remains positive, create a tightly isolated device candidate (`SHARPSOURCE1B`) while keeping SOURCECAL2A, BASISHSM1P/H25, TC20, curve02 and JPEG quality frozen.
