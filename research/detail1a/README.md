# M9DETAIL1A — ISO sharpening replay, 21 September 2026

GL2G's saved-image detail stage still uses the ISO160/Standard Sharp row. This
offline candidate executes its actual native functions with the recovered
13-row M9 Standard schedule. **No application source, APK, or production default
has changed.** The purpose is to evaluate an integration gap before choosing a
sensor ISO mapping.

## What is verified

- Native `m9color_jni.cpp` and `M9R35Renderer.java` match the exact frozen GL2G
  manifest hashes at `bc7bd4d9db8aeffd94a4792ce0a12198973c8a76`.
- The bank is regenerated from hash-verified M9 1.216 firmware using the existing
  exporter. It is not retuned or copied from Cobalt.
- Both actual JNI demosaic entry points, helper functions and threaded RGB loops
  are compiled. Only JNI memory access is stubbed. The candidate changes one
  shared coefficient lookup and supports the four conventional Bayer layouts.
- All 13 Standard rows pass an independent NumPy integer-kernel comparison;
  mode2 preserves the signed arithmetic shift. Constants and the 9-pixel
  unmodified perimeter pass. Slots 0–2 reproduce the current fixed row exactly.
- 36 synthetic CFA/dimension cases compare 212,184 RGB samples exactly.
- Complete 4096×3072 frames from 15 Ultra RGGB and 17 Ultra BGGR compare
  **75,497,472 RGB samples with zero difference** at slot0.
- Eight real RAWs (ISO50–1142) yield 16 fixed-grid tiles. Every tile was replayed
  with every one of the 13 rows. Low-ISO equivalence is also checked on all tiles.

## Photographic finding

The higher-ISO rows reduce small-residual sharpening and, at higher slots,
large-residual amplification too. This can reduce unwanted high-frequency
variation, but also reduces real texture contrast. The old main-camera `ISO×2`
rule is therefore a meaningful photographic choice, not harmless indexing.

The following figures are relative to current fixed ISO160 processing. They
describe the **native green detail stage**, not a final JPEG or pure noise level.

| RAW ISO | Mapping probe | Leica row | Edge-tile HF RMS change | Edge-gradient p95 change | Quiet-tile HF RMS change |
| --- | --- | --- | --- | --- | --- |
| 521 | 1× | 500 | −5.59% | −0.67% | −13.08% |
| 521 | 2× | 1000 | −29.65% | −3.54% | −24.67% |
| 573 | 1× | 640 | −17.52% | −11.29% | −24.63% |
| 573 | 2× | 1250 | −17.59% | −11.41% | −26.68% |
| 1142 | 1× | 1250 | −19.84% | −12.56% | −30.96% |
| 1142 | 2× | 2500 | −29.84% | −18.96% | −33.02% |

On the ISO573/1142 edge tiles, RGB zero-channel clipping decreases by about
1.6–2.7 percentage points. On the quiet shadow tiles it increases slightly
(about 0.10–0.22 points). This prevents claiming an unconditional improvement.
Visual inspection of the ISO1142 foliage crop confirms stronger softening with
the 2× probe. The ISO521 edge tile is visibly defocused and cannot establish
preservation of fine in-focus subject detail.

## Inputs and limits

`inputs.py` reconstructs the physical map grid from the four Android DNG
OpcodeList2 GainMaps, applies the current NORM030 geometric-mean decomposition,
outside-center median target 0.30EV, global representation scale, and full-image
bilinear coordinates **before cropping**. Black subtraction/normalization use
the native float32 sequence. CFA position and neutral are taken from each DNG.
This avoids the earlier invalid RAW replay which omitted lens shading.

This is a metadata replay of the preprocessing equations, not an independently
bit-verified Android/HAL preprocessing replay. Exact source/hash checks cover
the native spatial stage; they do not turn the whole offline pipeline into an
on-phone parity claim.

The DNGs' ISO tags are used as recorded, with 1× and 2× labeled as probes. Neither
mapping is calibrated to equivalent M9 noise. The recovered high-ISO RAWs are
15 Ultra main captures. There is no high-ISO 17 Ultra or telephoto validation.
All source images stay single-frame and unchanged.

The existing red/blue reconstruction is retained as the documented
RBANCHOR1A/MHC colour-difference approximation. Noise2's full filter is **not**
implemented by this change; its recorded mode/support relationship must not be
misrepresented as a completed noise-reduction pipeline.

TC20, source colour, SAT2, curve02, TG1, final JPEG encoding and preview are not
executed by this spatial-stage experiment. They remain unchanged in production,
but altered spatial pixels can affect downstream metering/clipping; full-render
same-RAW comparison is required before photographic promotion. Comparison PNGs
are grayscale green-stage diagnostics using a common display scale per tile.

Local reconstruction of the historical workflow produced mixed UI/exposure
file versions despite completing. Only the two required renderer sources have
been verified against current GL2G hashes. No new full Android assembly/build or
installation success is claimed, and no manifest was weakened to proceed.

## Run

From the repository root, with assembled GL2G renderer files and the canonical
decrypted M9 1.216 firmware available:

```bash
python3 research/detail1a/run.py \
  --assembled PhotonCamera \
  --firmware /absolute/path/m9-1_216.decrypted.upd \
  --out /absolute/path/detail1a-output \
  --full-parity \
  /absolute/path/15u.dng /absolute/path/17u.dng
```

Requires Python, NumPy, SciPy, tifffile, Pillow and a C++17 compiler. Firmware
bytes, generated bank/header, native library, photos and assembled Photon source
are not committed. `results/report.json` preserves hashes, exact input names,
metadata, tile coordinates, every row's metrics and the validation scope.

## Next work

1. Extend the replay through the exact current source-colour/TC20/JPEG path;
   retain fixed-slot baseline and explicit 1×/2× probes on the same RAW.
2. Evaluate in-focus faces, fur/fabric and shadow detail, not only foliage or a
   defocused window. Use the existing high-ISO originals recovered here first.
3. Establish a per-sensor ISO/noise policy; do not generalize the historical main
   sensor ×2 factor to all four lenses or the 17 Ultra.
4. Recover the complete Noise2 packed-difference filtering path and test it
   separately from the Sharp schedule. Retain the current RGB foundation until
   the replacement has proved its quality.
5. Build an isolated phone candidate after these photographic gates. Keep
   public sharpness-slider wiring separate from the fidelity comparison.
