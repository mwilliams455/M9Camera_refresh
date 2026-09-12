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

## Important new gate: Noise mode 2 is an active image-processing stage

The BF561 `Process_Noise` dispatch shows that `nNoise=2` is not only a border/support selector. Mode 2 dispatches the real `ASMBox9CDI` path. The recovered mode dispatch is:

- mode 1 -> `Gauss5CDI`
- **mode 2 -> `ASMBox9CDI`**
- mode 3 -> `Gauss13CDI`
- mode 4 -> `Gauss17CDI`
- mode 5 -> `Gauss21CDI`

Therefore the Leica stage order `GreenInterpolationWithCo -> Noise(mode2) -> Sharp` contains an active filtering stage between the recovered green source and Sharp. The current SHARPSOURCE1A offline discriminator intentionally omitted Leica Noise pixel processing and used only its now-proven support-margin effect.

Before claiming a device candidate is firmware-faithful, trace the Noise2 buffer flow and determine whether the `ASMBox9CDI` result becomes the `frame+0x3c` signal consumed by `Process_Sharpness`. If it does, either port/emulate the required Noise2 source behavior or explicitly label a device build as a diagnostic approximation.

## Interpretation

This closes the whole-frame support-margin ambiguity for the controlled ISO160/Standard sharpness validation path. The evidence continues to support the SHARPSOURCE direction: retain the validated neutral-MHC RGB foundation and derive the Sharp correction from the Leica-side source domain rather than sharpening MHC green directly.

Do not weaken the recovered Leica x2 Standard LUT to address the green/cyan halo. The current evidence points to Sharp source-domain mismatch as the dominant problem.

## Next fidelity gate before device promotion

1. Trace `Process_Noise` mode-2 (`ASMBox9CDI`) input/output buffer identity through `Run`.
2. Prove whether its output is the signal subsequently presented as Sharp `frame+0x3c`.
3. If yes, reproduce the minimum Noise2 source-domain behavior offline on the same five RAWs and re-run the halo/clamp gate.
4. Only then build/promote `SHARPSOURCE1B` as a firmware-fidelity candidate. A diagnostic APK may be built earlier if explicitly labelled as such.
5. Keep exposure, SOURCECAL, HSM, TC20, JPEG-quality, and saturation frozen throughout.

## Later app-control requirement (not part of this fidelity gate)

Once lens/rendering work is stable and the app is being productized, use Photon UI controls rather than permanently hard-coding recovered Leica defaults:

- map the Photon **sharpness slider** to the recovered Leica five-level Sharp behavior (Off / Low / Standard / Medium high / High and their firmware-derived ISO-dependent internal transforms);
- map the Photon **saturation slider** to the recovered Leica saturation behavior/modes.

This UI/control-layer work must remain separate from current firmware-fidelity validation so slider wiring cannot contaminate the photographic baseline.
