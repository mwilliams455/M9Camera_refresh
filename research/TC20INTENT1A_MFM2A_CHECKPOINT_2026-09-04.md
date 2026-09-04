# M9 Project checkpoint — TC20INTENT1A / M10RMFM2A

**Date:** 2026-09-04  
**Primary device:** Xiaomi 15 Ultra main/wide  
**Frozen photographic family:** R3.8-H25/TG1 + TC20 + SAT3 M06/M07 + curve02 + exact BT.601 4:2:2 + JPEG95

## 1. Corrected v0.7ZZS field baseline

Latest M10-R-inspired field corpus establishes:

- 121 JPEGs;
- 120 complete DNG/capture sets;
- exact capture/RAW identity: 120/120;
- queue accepted: 120/120;
- primary timing records: 120/120;
- DNG async fallback: 0;
- JPEG + DNG saved: 120/120;
- median render: 592 ms;
- mean render: 608 ms;
- render range: 497–958 ms;
- fastest successive captures: 2.097 s;
- MFM live decisions: 27 positive, 93 neutral, 0 negative;
- mean requested positive MFM assist: +0.267 EV;
- mean achieved capture delta: +0.261 EV;
- maximum requested assist: +0.532 EV.

Camera2 result matched request; request/actual differences are ordinary ISO/shutter quantisation.

The MFM snapshot overwrite bug is confirmed: 16/27 corrected captures later reported zero in `m9M10rMfmTest.appliedExposureCorrectionEv` because a later preflight evaluation replaced the snapshot. `m9ExposureAudit` is therefore the field authority for achieved intent.

## 2. Dominant renderer finding

All 27 positive-MFM frames were TC20 highlight-guard limited rather than median/base-gain limited.

This establishes the working hypothesis:

```text
intentional +delta sensor exposure
        -> physical RAW upper tail rises
        -> TC20 physical tail guard lowers render gain
        -> much of the intended global tonal movement disappears from JPEG
```

The real additional exposure is not useless: it can improve signal/noise in the lower negative. But increasing MFM capture EV alone is not expected to solve dense rendered subjects while TC20 continues cancelling the tonal intent.

Repeated +0.50-EV 'unused RAW headroom' values must not be interpreted as requested additional exposure: the current RAW teacher caps `additionalCaptureHeadroomEv` at +0.50 EV in most of the corpus.

## 3. Saturated-preview safety cohort

Frames with preview `globalQ95 == 255` are separated from ordinary intent-strength selection.

Known positive-MFM stress cases include #9, #41 and #121. They already contain meaningful physical RAW clipping and exist to answer a safety question, not to vote for the preferred intent-preservation strength.

`brightFractionGE240` remains diagnostic because it correlated materially better with physical RAW clipping than q95 in the field corpus. It is not yet an EV conversion.

## 4. TC20INTENT1A — active experiment

Branch:

`tc20intent1a-offline`

Current validated FIX1 head:

`e292e4aecff27c210433abcd240b156c859b1fef`

Validation run:

`33908887045` — SUCCESS

The harness is:

`research/tc20intent1a_offline.py`

FIX1 entry point:

`research/tc20intent1a_offline_fix1.py`

FIX1 only widens preview-safety metadata discovery to current/older sidecar locations, especially `m9SceneExposureDiagnostic.inputs`; it does not alter TC20 or render equations.

### Intent authority

Use only:

`m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv`

For cap C:

```text
preservedIntentEv = min(max(actualCaptureEnergyVsPhotonOnlyEv, 0), C)
```

Caps:

- 0.00 EV
- 0.10 EV
- 0.20 EV
- 0.30 EV

### A0

Frozen physical TC20:

```text
physicalMedian
physicalTail
basePhysical
physicalGuard
A0 = min(basePhysical, physicalGuard)
```

### A1

Full virtual intent-normalized measurement:

```text
virtualMedian = physicalMedian / 2^preservedIntentEv
virtualTail   = physicalTail   / 2^preservedIntentEv

baseVirtual
virtualGuard
A1 = min(baseVirtual, virtualGuard)
```

A1 gain is applied to the unchanged physical RAW-derived M9 image.

Physical clipping/headroom metrics are never normalized away.

For a guard-limited frame while the guard remains binding:

```text
A1Gain ~= A0Gain * 2^preservedIntentEv
```

Reference multipliers:

- +0.10 EV -> 1.072x
- +0.20 EV -> 1.149x
- +0.30 EV -> 1.231x

### A2 control

A2 currently tests:

```text
virtual median/base request
+
physical RAW tail guard
```

This is a blocker/control only. Since all positive field frames were guard-limited, A2 is expected to remain at/near A0 and demonstrate whether the physical hard guard is the blocker.

A delayed-precurve-clipping/curve02 A2b experiment is deliberately **not implemented yet**. Do not invent another highlight policy before A1 identifies a useful strength.

### Required metrics

Keep side by side:

- achieved capture intent;
- test cap / preserved intent;
- physical median / tail / hard clip;
- virtual median / tail;
- physical and virtual base/guard gains;
- gain delta vs A0;
- physical tail * candidate gain;
- pre-matrix high-channel clipping;
- QE/QO matrix-index clipping;
- JPEG near-white / any-channel full clip / all-white;
- global / center / middle-center exact-Y medians;
- q95/q99;
- deep-black fraction.

### Visual test

For positive achieved-intent frames, create deterministic blinded sheets containing:

- A0
- A1 +0.10 cap
- A1 +0.20 cap
- A1 +0.30 cap

Store the decoding key separately.

The saturated-preview cohort must be reported separately from the ordinary positive cohort.

### First gate

Before judging A1 photographs, require offline A0 gain parity against the Android `_M9_PRIMARY.json` TC20 gain. Default tolerance is 0.025 EV. If A0 parity fails materially, fix offline parity first.

## 5. M10RMFM2A — diagnostic/safety prep only

Branch:

`m10r-mfm2a-diagnostic-prep`

Current validation head:

`3f365a8d695c8780ae65b8fd82b762aee642d873`

Validation run:

`33908616170` — SUCCESS

The complete pinned Photon patch chain passed, the dedicated MFM2A verifier passed, Java/Kotlin application sources compiled, and the workflow explicitly confirmed that no APK artifact was produced/promoted.

### Implemented preparation

- exact step-0 MFM decision becomes capture-frozen;
- later preflight/evaluation snapshots cannot replace capture metadata;
- 16x22 preview geometry retained;
- exact recovered Integral spatial mask retained;
- 4x6 / 24-region structure retained;
- absolute body-level telemetry added;
- preview global median/q95/q99 added;
- `brightFractionGE224` / `brightFractionGE240` added;
- dark-fraction telemetry added;
- `globalQ95 == 255` vetoes **positive automatic assist only**;
- original MFM recommendation remains logged even when the veto suppresses application.

### Explicitly unchanged

- positive magnitude equation;
- +0.75 EV positive bound;
- negative magnitude equation;
- -0.50 EV negative bound;
- 0.08 EV deadband;
- manual EV / ISO / shutter authority;
- TC20;
- Cobalt calibration;
- H25/TG1;
- SAT3;
- curve02;
- BT.601;
- JPEG95;
- DNG path.

Absolute body level is telemetry only in this branch. The dormant negative path is not forced to generate negative decisions.

## 6. Development order now frozen for this investigation

1. Run TC20INTENT1A A0/A1/A2 against the existing 120-RAW v0.7ZZS corpus.
2. Require A0 Android parity before evaluating A1.
3. Judge ordinary positive cohort separately from saturated-preview safety cohort.
4. Select whether 0.10 / 0.20 / 0.30 EV preservation produces a coherent photographic improvement while preserving blacks and highlight character.
5. Only if needed, investigate delayed early clipping / curve02 handling as a separate A2b experiment.
6. Do not increase MFM capture magnitude yet.
7. Do not build a combined MFM2A + TC20INTENT live APK yet.
8. After offline evidence, make controlled real MFM-on/MFM-off captures; same-RAW replay cannot test alternate sensor clipping, motion or noise.
9. Defer SUBJECTLIFT1A until intent-aware global rendering is understood. Any later local lift addresses only a measured residual deficit.

## 7. Project principle

> Preserve the negative; make intentional global exposure survive development; use local subject manipulation only for a measured residual need.
