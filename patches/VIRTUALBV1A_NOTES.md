# VIRTUALBV1A

Diagnostic-only cross-generation Leica exposure experiment.

## Purpose

Test whether a simple Leica-like scalar meter -> BV abstraction predicts signed exposure direction more usefully than the existing positive-oriented preview classifier, while keeping completed-RAW SIGNEDCAL1A as an independent post-capture teacher.

## Frozen

- SCENEEXPOSURE1H behavior and schema
- CAPTUREMETER1B / SCENEFINGERPRINT1A threshold=1.0 and 60s age gate
- M9NEGATIVE1C / SIGNEDCAL1A recommendation math
- RENDERMETER1C
- Camera2/Photon exposure allocation
- M9ModernExposurePolicy motion behavior
- native M9 renderer/color pipeline
- DNG values
- JPEG quality/output

## VIRTUALBV1A meter proxy

No new pixel sampling pass is added. It reuses the existing SCENEEXPOSURE1H preview scalar diagnostics:

- 70% `centerMedian`
- 30% `globalMedian`

`meterProxyTemporal` is the same snapshot scalar in 1A because the existing preview-luma analyzer has already supplied the capture-time preview history. No new cross-capture temporal memory is introduced, avoiding stale-scene carry-over.

The provisional neutral proxy is Y=120, chosen from the existing M9Cam field corpus as a first diagnostic reference. It is explicitly NOT an M9 firmware constant and NOT an absolute calibration of the M9 TTL photodiode.

## BV construction

Photon-equivalent BV is expressed in standard APEX coordinates from the phone's photon-only exposure decision and physical aperture:

`BV_photon = TV + AV - SV`

The provisional virtual meter residual is:

`meterResidualEv = log2(meterProxy / 120)`

Then:

`virtualBvUncalibratedEv = photonEquivalentBvEv + meterResidualEv`

The 1A calibration offset is 0 EV and is logged separately.

The raw signed comparison is:

`signedMeterDeltaEv = photonEquivalentBvEv - virtualBvEv`

It is intentionally unbounded in VIRTUALBV1A. A small 0.08 EV deadband is used only for the textual direction label; the raw value remains available.

## M9 APEX baseline

The recovered M9 reduced-form baseline is logged using:

`TV = BV + SV - 5 - Override`

with the already-established M9 base ISO160 state for the baseline diagnostic solve.

VIRTUALBV1A does NOT invent the lens-dependent TV threshold required to finish the M9 Auto-ISO constraint solve. Therefore threshold and Auto-ISO activation fields are emitted as unavailable/null and the predicted TV/SV pair is explicitly labelled `base_iso160_reduced_m9_apex_baseline_only`.

## M10-R usage rule

M10-R contributes only the cross-generation architectural evidence that Leica separates meter/BV, calibration/override and TV/SV allocation. No M10-R camera-specific constants are copied, including the recovered 59/256 EV calibration offset or 25/256 EV source-change hysteresis.

## Validation goal

For each capture compare:

1. `m9VirtualBv.signedMeterDeltaEv`
2. LUMA2.4 recommendation/applied EV
3. CAPTUREMETER stabilized diagnostic
4. scene-matched completed-RAW M9NEGATIVE/SIGNEDCAL evidence
5. final RAW/render placement

Judge sign first (negative / neutral / positive), then magnitude. Do not promote to live exposure until the virtual meter is validated against completed RAWs and photographic labels.
