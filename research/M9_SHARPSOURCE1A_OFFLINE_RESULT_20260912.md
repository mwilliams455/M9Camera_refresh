# M9 SHARPSOURCE1A — OFFLINE RESULT

Date: 2026-09-12
Branch: `research/sharpness-rbclosure1a-forensics`
Production renderer: **unchanged / frozen**

## Question

The CLOSURETEST1B APK applies the recovered Leica ISO160 / Standard x2 Sharp path to the frozen neutral-MHC green plane, then reconstructs R/B from full-resolution MHC colour differences. The regression frame showed green/cyan foliage/sky halos and heavy R/B zero clamping.

The firmware proves that Leica Sharp consumes `frame+0x3c`, the green signal produced by `GreenInterpolationWithCo`. It does **not** prove that the mobile neutral-MHC green plane is signal-equivalent to that Leica green signal.

SHARPSOURCE1A tests whether the sharpness **source domain** is a major part of the defect while preserving the validated MHC RGB foundation.

## Recovered green arithmetic used

### Missing-green colour CFA sites

`ASMFilter_010_101_010_2` generates the coefficient as `1 << (16-2) = 0x4000` and uses unsigned-fraction multiplies. This resolves to a four-neighbour cardinal average:

`G = (N + S + W + E) / 4`

### Measured-green CFA sites

`ASMFilter_101_040_101_An` uses unsigned-fraction coefficients `0x2000` and `0x8000`, resolving to:

`G = center/2 + (NW + NE + SW + SE)/8`

At a Bayer green site the four diagonal sites are also green, so this is a green-only operation. The same BF561 routine also produces the absolute residual/guide used later by `ASMRedBlueAndGreenDiffer`.

The coefficient arithmetic and phase roles are firmware-derived. The current offline image-space mapping is **not yet claimed bit-for-bit packed-pointer/border parity** with the BF561 implementation.

## Mobile-source-adapter discriminator

The experiment intentionally does **not** replace the frozen MHC RGB image.

1. Generate frozen neutral-MHC RGB exactly as CLOSURETEST1B.
2. Independently construct the two-stage Leica-like green source above from the same RAW.
3. Apply the existing recovered ISO160 / Standard x2 Sharp reference to that green source.
4. Compute `sharpDelta = sharp(G_leica_like) - G_leica_like`.
5. Apply the same `sharpDelta` to frozen MHC R, G, and B.

This preserves the frozen MHC colour differences and uses the Leica-like green signal only to determine the Sharp correction.

This is a **mobile source adapter diagnostic**, not a claim that Leica itself mixes MHC RGB with this green source.

## Regression RAW

`IMG_20260912_124558_1789213558532_00.dng`

RGGB, 4096 x 3072. Seven 512x512 tiles were selected automatically: six highest edge-stress tiles plus one low-edge control.

## Result

Mean across seven tiles:

| Metric | CLOSURETEST1B | SHARPSOURCE1A | Change |
|---|---:|---:|---:|
| R == 0 | 17.9224% | 11.6017% | -35.3% relative |
| B == 0 | 17.4637% | 11.7926% | -32.5% relative |
| edge R == 0 | 25.0346% | 16.2983% | -34.9% relative |
| edge B == 0 | 19.6167% | 13.0622% | -33.4% relative |
| cyan pixels | 0.05137% | 0.03743% | -27.1% relative |
| edge cyan | 0.32215% | 0.23107% | -28.3% relative |
| R max clamp | 0% | 0% | unchanged |
| B max clamp | 0% | 0% | unchanged |

Worst foliage/sky tile `[1536,1536,512,512]`:

- edge R-zero: `33.779% -> 25.364%`
- edge cyan: `1.306% -> 1.075%`

Other high-edge tiles also improved materially. The low-edge control did not show the regression seen in the earlier one-stage cardinal-only test.

## Rejected controls from this block

The following did **not** solve the problem and should not be promoted:

- full-resolution MHC `R-G/B-G` closure by itself (CLOSURETEST1B)
- simple CFA-phase-native bilinear colour-difference reconstruction
- the recovered `ASMRedBlueAndGreenDiffer` limiter followed by that bilinear scaffold
- applying only the recovered limiter to completed MHC full-resolution colour differences
- replacing MHC green outright with the cardinal-green proxy

The final item reduced some clamps but increased cyan-edge incidence overall; it is not the recommended direction.

## Interpretation

SHARPSOURCE1A is the strongest discriminator so far that the new green/cyan halo is substantially a **Sharp source-domain mismatch**.

The recovered Leica x2 LUT/kernel can be correct while producing the wrong photographic behaviour when fed a green signal with different high-frequency semantics. Neutral-MHC remains the validated demosaic foundation; the evidence does not justify weakening the Leica Sharp LUT or undoing MHC.

The promising mobile architecture is therefore:

`frozen neutral-MHC RGB`

plus

`Leica-derived green source -> Leica Sharp -> sharp correction`

then apply that correction to the frozen MHC RGB.

## Status / fidelity boundary

Firmware-proven:

- Sharp consumes Leica `frame+0x3c`.
- final R/B reconstruction consumes the sharpened green/base.
- `010/101/010` coefficient/normalisation behaviour.
- `101/040/101` coefficient/normalisation behaviour.
- packed/interleaved colour-difference architecture.
- recovered edge-aware colour-difference limiter and shift 2.

Still provisional:

- exact image-space correspondence of every packed BF561 pointer increment/border case in `GreenInterpolationWithCo`.
- using the Leica-style green only as a Sharp source while retaining MHC RGB. This is a deliberate Xiaomi/mobile adapter.

## Next gate

Do **not** build a new APK yet.

Next:

1. close packed pointer/phase/border parity for the green-producing portion of `GreenInterpolationWithCo`;
2. reproduce SHARPSOURCE1A with the exact scalar green reference;
3. require the regression improvement to survive that parity correction;
4. replay additional known edge/pathological RAWs, not only the 124558 frame;
5. only then create a device candidate (`SHARPSOURCE1B` or later) while keeping SOURCECAL2A, BASISHSM1P/H25, TC20, curve02 and JPEG quality frozen.
