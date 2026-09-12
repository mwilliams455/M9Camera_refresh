# SHARPSOURCE1B — nNoise=2 / exact 9-pixel support gate closed

Date: 2026-09-12
Branch: `research/sharpness-rbclosure1a-forensics`
Production renderer: untouched

## Result

The controlled photographic processing serializer at BF547 `0x37070` begins its processing record at `P5+0x12c` (four-byte marker copied there first) and serializes:

- record `+0x09` <- state `+0x40`
- record `+0x0A` <- state `+0x440`
- record `+0x0B` <- state `+0x44c`
- record `+0x0C` <- state `+0x444` (previously proven Sharp)
- record `+0x0D` <- literal `2`
- record `+0x0E` <- state `+0x448`

The firmware's own BF547 processing-settings diagnostic consumer at `0x6ca6c..0x6cae0` directly labels:

- `+0x09` = `nIso`
- `+0x0A` = `nContrast`
- `+0x0B` = `nSaturation`
- `+0x0D` = `nNoise`
- `+0x0E` = `nColorSpace`

Therefore the photographic record built by this serializer has **`nNoise = 2`**. This is an explicit literal in this serializer, not an ISO160 inference.

The active-profile source mapping is also closed by the profile diagnostic consumer: active-profile `+0x64` is the value printed for `ColorSpace`, and state `+0x448` is copied from active-profile `+0x64`. This independently confirms record `+0x0E` is ColorSpace and removes the prior field-origin ambiguity.

## Exact cumulative support margin

Recovered BF561 `Process_Noise` behavior:

- mode <= 0: +0 px
- mode 1: +2 px
- **mode 2: +4 px**
- mode 3: +6 px
- mode 4: +8 px
- mode 5: +10 px

The same cumulative processing-border counter is advanced by:

- `GreenInterpolationWithCo`: +3 px
- `Process_Noise`, mode 2: +4 px
- `Process_Sharpness`: +2 px

So the controlled Green -> Noise -> Sharp path has an exact valid support margin of **9 pixels**.

## Five-RAW exact-margin regression gate

The existing SHARPSOURCE1A replay was rerun with the metric/core exclusion changed from the provisional margin to the proven 9-pixel margin. The same five RAWs and automatic 7-tile-per-RAW selection were used (35 tiles total); there was no per-image tuning.

Tile result:

- edge R->0 clamp: 32 improved / 3 ties / **0 regressions**
- edge B->0 clamp: 35 improved / **0 regressions**
- edge-cyan metric: 17 improved / 18 ties / **0 regressions**

Mean across the five RAWs:

- edge R->0: 11.5012% -> 7.0693% (**-38.53% relative**)
- edge B->0: 7.7832% -> 4.3989% (**-43.48% relative**)
- edge cyan: 0.71029% -> 0.57272% (**-19.37% relative**)

Regression-frame (`IMG_20260912_124558_1789213558532_00.dng`) exact-margin means:

- edge R->0: 25.0407% -> 16.3071%
- edge B->0: 19.6371% -> 13.0660%
- edge cyan: 0.32461% -> 0.23545%

## Interpretation

This closes the remaining whole-frame support-margin ambiguity for the controlled ISO160/Standard sharpness validation path. The evidence continues to support the SHARPSOURCE approach: retain the validated neutral-MHC RGB foundation, derive the Leica Standard mode-4/x2 Sharp correction from the recovered Leica-style green source, and apply that correction to the frozen RGB foundation rather than sharpening MHC green directly.

Do not weaken the recovered Leica x2 Standard LUT to address the green/cyan halo. The current evidence points to Sharp source-domain mismatch as the dominant problem.

## Next device gate

Build an isolated `SHARPSOURCE1B` candidate with:

1. frozen production renderer as parent;
2. frozen neutral-MHC RGB output;
3. Leica-style 14-bit green Sharp source for interior pixels;
4. ISO160 Standard mode-4/x2 Sharp LUT unchanged;
5. exact 9-pixel valid support/border policy for this controlled path;
6. explicit diagnostic metadata identifying SHARPSOURCE1B, Sharp menu/mode, nNoise=2, and supportMargin=9;
7. no exposure, SOURCECAL, HSM, TC20, JPEG-quality, or saturation changes.

## Later app-control requirement (not part of this fidelity gate)

Once lens/rendering work is stable and the app is being productized, use Photon UI controls rather than permanently hard-coding recovered Leica defaults:

- map the Photon **sharpness slider** to the recovered Leica five-level Sharp behavior (Off / Low / Standard / Medium high / High and their firmware-derived ISO-dependent internal transforms);
- map the Photon **saturation slider** to the recovered Leica saturation behavior/modes.

This UI/control-layer work must remain separate from current firmware-fidelity validation so slider wiring cannot contaminate the photographic baseline.
