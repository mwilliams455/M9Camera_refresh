# M9EDGEPLACEMENTLIFT1A — pre-curve treatment / selector pass 1

Research-only. No live APK pixel mutation is authorized by this note.

## 1. Frozen baseline remains authoritative

The current capture exposure policy, TC20, R3.8-H25/TG1, Cobalt calibration, M9 bridge/HSM, SAT3 M06/M07, firmware curve02, exact BT.601 4:2:2, 12 MP JPEG95 and DNG output remain frozen.

The problem under investigation is rare finished-placement failure, not a global exposure calibration error.

## 2. Treatment stage tested

The first DARK treatment probe applies a small exposure-equivalent multiplier only to the frozen TC20 render gain after TC20 has completed its decision and before SAT3/curve02:

`effectiveRenderGain = frozenTc20Gain * 2^liftEv`

Test bank:

- Frozen / +0.00 EV
- +0.15 EV
- +0.25 EV
- +0.35 EV

This is a global development-style placement change. Capture exposure and TC20 decision math are untouched. No local tone mapping is used.

The replay used the retained Part-3 Android DNGs, exact firmware curve02 extracted from the current METADATAFIX1A APK calibration asset, Cobalt Xiaomi 15 Ultra main DCP, SAT3 M06/M07, exact BT.601 arithmetic, and R3.8 HSM hue strength 0.25. The replayed outdoor frames were daylight (>4500 K), so TG1 is inactive.

## 3. Visual treatment result

### `IMG_20260904_164048_1788536448208_00` — confirmed DARK_FAIL

Frozen leaves the statue/sculpture useful body substantially too dense.

The treatment progression is monotonic and photographically coherent:

- +0.15 EV: subtle recovery;
- +0.25 EV: clearly useful body recovery while preserving the scene's contrast principle;
- +0.35 EV: stronger recovery and still restrained in this failure.

There is no evidence from this frame that the required correction should exceed +0.35 EV.

### `IMG_20260904_164019_1788536419887_00` — DARK candidate

The same progression restores statue/body readability without turning the scene into an HDR/open-shadow rendering. +0.25 to +0.35 EV is the useful range in this candidate.

### GOOD / BOUNDARY controls

The same lift is visibly unnecessary on healthy controls such as the positive-intent swan `164402` and the dense woodland boundary `163702`. This reinforces that the treatment itself is acceptable only behind a very conservative selector.

Therefore pass 1 does **not** support a universal +0.25/+0.35 EV change. It supports a bounded pre-curve treatment bank behind a rare exception gate.

## 4. Selector audit

The current Part-3 spatial-collapse probe is the descriptive conjunction:

- achieved capture intent >= +0.10 EV;
- finished-vs-preview upper/lower separation shift >= +1.50 EV;
- broad finished 4x6 body remains very low: render-cell median P75 <= 30/255;
- Integral-weighted field fails to recover materially relative to the overall rendered mean: Integral relative shift <= +0.15 EV.

These values remain research probe values, not production constants.

Fresh replay/audit results:

| capture | label | intent EV | upper/lower shift EV | Integral relative shift EV | cell median P75 | probe |
|---|---|---:|---:|---:|---:|---|
| 163553 | GOOD | 0.000 | -0.267 | +0.267 | 26.25 | off |
| 163702 | BOUNDARY | 0.000 | +0.737 | +0.486 | 4.00 | off |
| 163847 | GOOD | 0.000 | +0.237 | +0.265 | 22.00 | off |
| 164019 | DARK candidate | +0.299 | +2.492 | -0.018 | 15.25 | **on** |
| 164048 | DARK_FAIL | +0.138 | +2.865 | +0.097 | 24.75 | **on** |
| 164247 | GOOD | 0.000 | +0.420 | +0.185 | 27.25 | off |
| 164331 | GOOD | 0.000 | -1.218 | +0.475 | 16.25 | off |
| 164402 | GOOD positive-intent hard negative | +0.202 | +0.459 | +0.529 | 13.50 | off |

This reproduces the qualitative INTENTCOLLAPSE1A separation: the two statue frames have unusually large upper/lower separation growth while the Integral-weighted useful field fails to improve relative to the frame mean.

Critically, `164402` demonstrates why positive capture intent plus a dark render is insufficient: it has +0.202 EV intent and a low broad body, yet the spatial relationship remains healthy and the probe stays off.

## 5. Treatment-strength conclusion

Do not freeze a single correction strength yet.

Retain the bounded bank:

- +0.15 EV
- +0.25 EV
- +0.35 EV

Current visual evidence makes +0.25 EV the best centre point for the next comparison, with +0.35 EV retained for severe useful-body collapse. The final amount should remain scene-adaptive or severity-bounded rather than becoming a universal fixed lift.

No amount is allowed unless the exception gate is high-confidence.

## 6. Remaining blocker before live mutation

The selector must be challenged against the recent prospective hard negatives, especially:

- `IMG_20260905_084325_1788594205278_00`
- `IMG_20260905_084328_1788594208373_00`
- `IMG_20260905_084333_1788594213200_00`
- `IMG_20260905_084525_1788594325303_00`
- `IMG_20260905_084858_1788594538919_00`
- BOUNDARY `IMG_20260905_084154_1788594114928_00`

`084858` is the strongest falsification target because it is visually GOOD despite an extremely low finished global median and severe TC20 guard suppression.

A selector that activates on `084858` is rejected regardless of historical DARK recall.

## 7. Next implementation step

1. Keep current METADATAFIX1A APK photographic pixels frozen.
2. Compute the spatial-collapse probe offline on the prospective hard negatives as soon as their original JPEG + `_M9.json` pairs are available to the analysis runtime.
3. If all hard negatives remain off, implement `EDGEPLACEMENTGATE1A` as diagnostic-only telemetry first.
4. Collect prospective ordinary frames without hunting for trigger scenes.
5. Only after zero false activation is demonstrated, allow the gate to select a pre-curve `EDGEPLACEMENTLIFT1A` treatment.
6. Initial live treatment bank remains +0.15/+0.25/+0.35 EV with Frozen mandatory fallback.
7. Do not change capture AE, TC20 or global shadow/black-point rendering.

## 8. Current interpretation

The exposure problem is becoming more specific:

> genuine DARK failure is not 'the JPEG is dark.' It is a rare collapse in which the useful spatial body loses placement through Frozen rendering despite real capture intent, while the central/Integral-weighted field fails to retain enough support relative to the frame.

That is the mechanism EDGEPLACEMENTLIFT1A should target.
