# M9 Sharpness RBCLOSURE1A findings

Date: 2026-09-12
Branch: `research/sharpness-rbclosure1a-forensics`

## Purpose

Resolve the green/cyan foliage-sky halo exposed by `SHARPNESS_CLOSURETEST1B` without regressing the validated neutral-aware MHC demosaic or weakening firmware-proven Leica Standard sharpness mode 4.

Regression frame:
`IMG_20260912_124558_1789213558532_00.dng`

## Closed facts

1. The older magenta foliage/sky failure and the current green/cyan CLOSURETEST1B failure are not the same root cause.
   - The current neutral-aware MHC remains cleaner than OpenCV EA on the supplied DNG foliage/sky boundary.
   - Do not revert the frozen demosaic to fix this new halo.

2. Leica post-Sharp R/B reconstruction is additive colour-difference reconstruction.
   - `ASMRedBlueInterpolation1` adds signed interpolated colour differences to the green/base plane.
   - Results are clamped to `0..16383`.
   - A multiplicative/hue-preserving closure can suppress the artifact offline but is not firmware-correct and must not be promoted as Leica behaviour.

3. Sharp -> R/B green alias is closed.
   - `frame+0x3c` is sharpened in place by the Sharp path.
   - The same `frame+0x3c` is supplied as the packed green/base input to `ASMRedBlueInterpolation1`.
   - `frame+0x38` is Gaussian/work scratch in the Sharp stage, not the sharpened output.

4. CLOSURETEST1B's full-resolution MHC colour-difference preservation is structurally approximate.
   - It computes full-resolution `R-G` and `B-G` from the frozen MHC RGB image and adds those differences to sharpened green.
   - Firmware does not reconstruct R/B from two ordinary full-resolution RGB-derived difference planes.

5. Firmware uses a packed/two-phase colour-difference representation.
   - `GreenInterpolationWithCo` invokes `ASMRedBlueAndGreenDiffer` twice with complementary CFA-phase pointer offsets.
   - `ASMRedBlueAndGreenDiffer` explicitly computes signed `sample - green` words and writes a 16-bit difference stream.
   - The two phase calls feed a packed/interleaved colour-difference representation which is filtered before final R/B reconstruction.
   - `ASMRedBlueInterpolation1` executes two complementary passes over that packed stream. The second pass shifts the stream/base phase by two bytes and uses mirrored/shifted interpolation geometry.

6. The earlier shorthand that `frame+0x40` and `frame+0x44` are simply two independent full-resolution R/B difference planes is rejected.
   - The BF561 ABI/call trace shows a more compact packed representation and stage-dependent reuse of frame buffers.
   - Do not encode +0x40/+0x44 as direct R-G/B-G identities without a complete consumer proof.

## CLOSURETEST1B DNG regression result

Using the supplied DNG as a fixed foliage/sky regression frame:

- Current neutral-MHC with Sharp bypassed has substantially less green/cyan edge excursion than OpenCV EA.
- CLOSURETEST1B mode4 x2 plus provisional full-resolution MHC difference preservation strongly amplifies the edge chroma/clamp problem.
- Ratio/hue-preserving closure removes most of the clamp pressure but contradicts the recovered Leica additive architecture.
- A crude CFA difference-lane interpolation is insufficient; the firmware's packed difference production/filtering/interpolation semantics matter.

Therefore the target is not `change demosaic` and not `reduce Leica sharpness by eye`.

## Canonical BF561 evidence generated

Successful forensic runs:

- `34695003096` — `M9 Sharpness RBCLOSURE1A Forensics`
- `34695307740` — `M9 Sharpness RBCLOSURE1B Symbol Map`
- `34695431553` — `M9 Sharpness RBCLOSURE1C Consumer Trace`

Important recovered routines:

- `GreenInterpolationWithCo`
- `ASMRedBlueAndGreenDiffer`
- `ASMFilter_101_040_101_An`
- `ASMFilter_101_000_101_2`
- `ASMRedBlueInterpolation1`
- `Process_Sharpness`
- `ExecuteColorMatrix_14FM1`
- `Process_WB`
- `L3L1_Put16BitRGB`
- `L3L1_Put3rgb`

## Next proof gate

Build an **offline scalar RBCLOSURE reference**, not an APK first.

Required sequence:

1. Reconstruct the packed two-phase difference-buffer geometry from `GreenInterpolationWithCo` call offsets.
2. Port the signed-word arithmetic of `ASMRedBlueAndGreenDiffer` and its two filter stages.
3. Port the two-pass `ASMRedBlueInterpolation1` arithmetic, preserving 14-bit clamps and phase offsets.
4. Validate internal invariants against the disassembly anchors and synthetic arrays before using real RAW data.
5. Replay the exact supplied DNG with:
   - frozen NORM030 source treatment,
   - frozen DEMOSAICMHCNEUTRAL1A green reconstruction,
   - frozen Standard slot0 mode4 x2 Sharp,
   - only the new packed Leica-style R/B closure changed.
6. Compare against CLOSURETEST1B using:
   - green/cyan foliage-sky edge excursion,
   - R/B 14-bit clamp frequency,
   - ordinary-scene colour preservation,
   - high-frequency edge detail / halo metrics.
7. Only if the offline result improves the supplied regression frame without changing unrelated photographic behaviour should a `CLOSURETEST1C` APK be built.

## Do not change yet

- frozen production branch
- neutral-aware MHC demosaic
- SOURCECAL2A
- BASISHSM/H25
- TC20/tone placement
- Standard mode4 x2 Sharp LUT strength
- JPEG quality

The green/cyan issue is now isolated to the fidelity of the post-Sharp colour-difference reconstruction until contrary evidence appears.
