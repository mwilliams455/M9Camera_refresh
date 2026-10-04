# M9_NATIVE_HSM_ROLE_DECISION_v1

Date: 2026-09-16
Project: Leica M9 emulation on portable Xiaomi/Camera2 RAW sources
Research branch: `research/m9nativehsm1a-sameraw-ab`
Frozen control: run `35085472220`, head `59a8f1ceeccca299c25568fc16f65bd251614785`

## Question

What M9-native stage, if any, should replace the historical Cobalt/Xiaomi 15 Ultra Adobe `ProfileHueSatMap` currently applied after `TARGETINPUTADAPTER1A`?

## Frozen experiment rule

The first same-RAW experiment changes only the HSM operation. It does not change:

- physical SOURCECAL / Camera2-DNG source calibration;
- `TARGETINPUTADAPTER1A` algebra;
- exposure or TC20;
- demosaic;
- sharpening;
- the current firmware-derived saturation matrix bank;
- curve02;
- BT.601 conversion;
- TG1;
- JPEG encoding/quality.

The frozen A control remains the run `35085472220` behavior.

## Firmware evidence already recovered

The checked-in firmware state model establishes the following for the recovered M9 rendering system:

1. Standard sRGB uses firmware saturation state `nSaturation = 2`.
2. That state selects signed 3x3 matrix pair `M04/M05`.
3. Matrix choice is made per pixel using the recovered condition `R >= G`.
4. The RGB curve stage is independently applied per R/G/B after the signed matrix stage in the reconstructed colour path.
5. The FPGA RGB/YCbCr conversion is a separate subsystem rather than evidence for an Adobe-style HSM.
6. No generic post-YCbCr creative-saturation operation has been recovered from the firmware evidence summarized in `forensics/M9_FIRMWARE_RENDER_STATE_MODEL_v1.json`.

Therefore the known M9 nonlinear/creative colour mechanisms are already represented by firmware-native matrix/curve operations. There is currently no firmware evidence for a separate Adobe `ProfileHueSatMap`-equivalent stage at the portable renderer's `camToPp -> HSM -> ppToM9` seam.

## Current implementation fact

The native portable colour core currently has an explicit Adobe-style HSM seam:

`camToPp -> applyHsm -> ppToM9`

The historical production path populates that HSM from the old Xiaomi 15 Ultra Cobalt calibration asset. That table was useful historically but its provenance does not prove that it is part of the Leica M9 rendering mechanism or that it is portable across arbitrary source sensors.

The renderer also already contains an exact identity HSM representation: a 2x2 hue/saturation grid containing four `{0 degrees, 1x saturation, 1x value}` entries.

## Decision for M9NATIVEHSM1A

Do not invent or fit a new HSV/HSL/3D-LUT stage to make `M9NATIVEHSM1A` visually distinct from HSM bypass.

The current evidence-based null/native hypothesis is:

> The M9 has no separately proven Adobe-style HSM role at this seam. When the downstream firmware-derived M9 colour stages are retained, the M9-native operation at the HSM seam is identity.

Under the frozen first experiment, this means `M9NATIVEHSM1A` is expected to be mathematically/pixel equivalent to `HSMBYPASS1A` unless further firmware evidence identifies a missing colour operation that belongs specifically at this location.

This is a valid forensic result, not a failed experiment.

## Same-RAW variants

### A — HSMCONTROL1A

Current frozen production control:

`SOURCECAL -> TARGETINPUTADAPTER1A -> historical Cobalt-derived HSM -> existing M9 stages`

### B — HSMBYPASS1A

Strict single-variable test:

`SOURCECAL -> TARGETINPUTADAPTER1A -> identity HSM -> existing M9 stages`

Implemented by `patches/apply-m9cam-hsmbypass1a-sameraw.py`.

### C — M9NATIVEHSM1A

Current forensic definition:

`SOURCECAL -> TARGETINPUTADAPTER1A -> no separately proven M9 HSM operation -> existing firmware-derived M9 stages`

With the present evidence and frozen downstream path, C should equal B. C must not gain an arbitrary LUT merely to force an A/B/C visual difference.

## Separate follow-up: firmware Standard saturation state

A separate fidelity question has been exposed and must not be mixed into the first HSM test.

The current renderer constant is:

`SATURATION_BANK = 3`

The checked-in matrix-bank mapping identifies this as firmware pair `M06/M07`.

The recovered Standard sRGB firmware state instead uses saturation state `2`, pair `M04/M05`.

Both are firmware-native matrix pairs, but SAT3 is not the recovered Standard setting. Therefore after the HSM A/B result is understood, run a separate tone-locked experiment, tentatively `SATSTATE1A`, comparing:

- identity HSM + current SAT3 `M06/M07`; versus
- identity HSM + Standard SAT2 `M04/M05`.

Do not change TARGETINPUTADAPTER1A, curve02, BT.601, TG1, exposure or tone in that comparison.

## Promotion criteria

The historical Cobalt HSM should be removed from production only after same-RAW evidence shows that identity/native handling:

- does not create unacceptable skin, yellow, foliage, cyan/blue or tungsten errors;
- reduces or does not worsen cross-sensor colour drift;
- preserves neutral-axis stability;
- does not cause unintended luma/exposure changes;
- retains the desired M9-like colour character through the actual firmware-derived downstream stages.

The later SAT2/SAT3 experiment must remain a separate decision so its effect is not incorrectly attributed to HSM removal.

## Current interpretation

The strongest evidence-based architecture is therefore trending toward:

`physical sensor SOURCECAL -> common scene -> target-input/reference transform -> no Adobe-HSM dependency -> firmware-native M9 matrix/curve/chroma/tone path`

Further firmware forensics may revise this only if a concrete missing operation, stage order, coefficient set or LUT semantics is recovered.