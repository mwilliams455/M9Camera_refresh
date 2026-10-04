# M9 SHARPSOURCE1A — CROSS-SCENE OFFLINE GATE

Date: 2026-09-12
Branch: `research/sharpness-rbclosure1a-forensics`
Production renderer: **unchanged / frozen**

## Purpose

Test the existing untuned SHARPSOURCE1A mobile source-adapter discriminator on independent Xiaomi 15 Ultra M9-project RAWs before authorizing any device APK candidate.

No per-scene tuning was allowed. Every RAW used the same:

- frozen neutral-MHC RGB reconstruction,
- Xiaomi RAW -> Leica 14-bit bridge,
- firmware-derived Leica green source for Sharp only,
- recovered ISO160 / Standard mode-4 x2 Sharp reference,
- `sharpDelta = sharp(G_leica) - G_leica`,
- same sharpDelta applied to frozen MHC R/G/B,
- six highest-edge 512x512 tiles plus one low-edge control,
- six-pixel interior metric margin.

## RAW set

Five independent RAWs were replayed:

1. `IMG_20260906_185135.dng`
2. `IMG_20260907_074800_1788763680653_00.dng`
3. `IMG_20260907_112105_1788776465605_00.dng`
4. `IMG_20260907_131216_1788783136268_00.dng`
5. `IMG_20260912_124558_1789213558532_00.dng` — known CLOSURETEST1B foliage/sky regression frame

This first cross-scene gate intentionally uses already-resolved original M9-project DNGs. The September 9/11 SKYSAT-specific corpus remains a desirable second validation set, but is not required to interpret this gate.

## Per-scene mean results

### 2026-09-06 18:51:35

- edge R-zero: `1.13939% -> 0.07684%` (**-93.3% relative**)
- edge B-zero: `0.66975% -> 0.06400%` (**-90.4% relative**)
- edge cyan: `0 -> 0`
- no max-channel clamp regression

### 2026-09-07 07:48:00

- edge R-zero: `0.47840% -> 0.02197%` (**-95.4% relative**)
- edge B-zero: `0.69582% -> 0.01365%` (**-98.0% relative**)
- edge cyan: `0.003029% -> 0.001135%` (**-62.5% relative**)
- no max-channel clamp regression

### 2026-09-07 11:21:05

- edge R-zero: `12.84020% -> 8.19376%` (**-36.2% relative**)
- edge B-zero: `7.24262% -> 3.59080%` (**-50.4% relative**)
- edge cyan: `3.08574% -> 2.54896%` (**-17.4% relative**)
- one interior tile gains one blue-max pixel (`0 -> 0.0004%` in that tile; scene mean `0.000057%`)

### 2026-09-07 13:12:16

- edge R-zero: `17.96240% -> 10.71685%` (**-40.3% relative**)
- edge B-zero: `10.65881% -> 5.23068%` (**-50.9% relative**)
- edge cyan: `0.13572% -> 0.06954%` (**-48.8% relative**)
- no max-channel clamp regression

### 2026-09-12 12:45:58 regression frame

- edge R-zero: `25.03458% -> 16.29315%` (**-34.9% relative**)
- edge B-zero: `19.61671% -> 13.05397%` (**-33.5% relative**)
- edge cyan: `0.32215% -> 0.23184%` (**-28.0% relative**)
- no max-channel clamp regression

## Tile-level directional result

Across all **35 automatically selected tiles**:

- edge R-zero: **32 improved / 3 tied / 0 worse**
- edge B-zero: **35 improved / 0 tied / 0 worse**
- edge cyan: **17 improved / 18 tied / 0 worse**
- overall R-zero: **35 improved / 0 tied / 0 worse**
- overall B-zero: **35 improved / 0 tied / 0 worse**
- overall cyan: 15 improved / 19 tied / 1 microscopically worse
- R-max: 35 tied / 0 worse
- B-max: 34 tied / 1 microscopically worse

The two microscopic adverse events are:

1. one 512px tile in the 2026-09-07 11:21 RAW gains one blue-max pixel (`0.0004%` of the tile interior), and
2. one tile in the 2026-09-12 regression RAW changes overall cyan classification from `0.0012%` to `0.0016%` while that scene's **edge-cyan metric still improves substantially**.

Neither event resembles the CLOSURETEST1B coloured-edge failure mechanism.

## Interpretation

This cross-scene result materially strengthens the source-domain hypothesis.

The improvement is not confined to the September 12 foliage/sky frame. The same untuned firmware-derived Sharp source adapter reduces R/B zero clamping over low-artifact controls and high-stress scenes, and no selected tile shows worse edge R-zero, edge B-zero, or edge-cyan behavior.

The evidence therefore argues against weakening the Leica Standard x2 LUT merely to suppress the regression. The more likely incompatibility was feeding that recovered Leica Sharp stage with the frozen MHC green signal rather than a Leica-compatible `GreenInterpolationWithCo` source domain.

## Gate decision

**MULTI-RAW SHARPSOURCE1A GATE: PASS, provisionally.**

Remaining blocker before a device candidate:

- close or explicitly bound the BF561 border/stride traversal of the green-producing stage so the mobile implementation has deterministic whole-frame boundary behavior.

Desirable additional evidence, but not a blocker to the present conclusion:

- replay the September 9/11 SKYSAT-specific RAWs once their original bytes are mounted,
- full photographic JPEG A/B once a device candidate exists.

If the border/stride gate closes without changing the proven interior arithmetic, proceed to a tightly isolated `SHARPSOURCE1B` APK candidate while freezing SOURCECAL2A, neutral-MHC, BASISHSM1P/H25, TC20, curve02, JPEG quality, and every non-sharpness stage.