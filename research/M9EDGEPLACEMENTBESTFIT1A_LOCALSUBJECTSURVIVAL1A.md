# M9EDGEPLACEMENTBESTFIT1A — LOCALSUBJECTSURVIVAL1A

**Date:** 2026-09-05  
**Branch:** `m9edgeplacementbestfit1a-offline3`  
**Status:** research-only. No live lift, capture mutation, TC20 change, or renderer mutation.

## Finding

The 29-frame Part-3 replay exposed one new provisional `ZERO_INTENT_COLLAPSE` activation: `IMG_20260904_164436_1788536676888_00`.

Do not fix that by moving Branch B's preview thresholds. Instead it exposes a protective morphology: a compact central bright subject can remain strongly preserved while the surrounding/global field is intentionally very dark.

The required evidence already exists in PRIMARY `directRenderedLuma` telemetry.

## Research feature

```text
localQ95 = max(center50.q95, middleCenter33.q95)
localHighlightConcentrationY = localQ95 - global.q95
```

Provisional protective seed only:

```text
LOCAL_SUBJECT_SURVIVAL =
    localQ95 >= 220
    AND localHighlightConcentrationY >= 80
```

## Part-3 evidence

| capture | label | global q95 | local q95 | delta Y | guard |
|---|---|---:|---:|---:|---|
| 163702 | BOUNDARY | 89 | 253 | +164 | ON |
| 164436 | unlabelled audit candidate | 106 | 255 | +149 | ON |
| 164420 | unlabelled | 118 | 255 | +137 | ON |
| 164331 | GOOD | 119 | 255 | +136 | ON |
| 164402 | GOOD | 168 | 249 | +81 | ON |
| 164736 | unlabelled | 161 | 228 | +67 | OFF |

Known Part-3 DARK anchors do not have this morphology:
- `164019` DARK candidate: delta about -10 Y
- `164048` DARK_FAIL: delta about +12 Y

This is therefore supported by multiple protected frames rather than being invented only for `164436`.

## Critical anchors

| frame | role | global q95 | local q95 | delta Y | guard |
|---|---|---:|---:|---:|---|
| 142840 | DARK_FAIL / ZERO_INTENT | 138 | 91 | -47 | OFF |
| 142939 | DARK_FAIL / ZERO_INTENT | 91 | 111 | +20 | OFF |
| 084858 | GOOD extreme-dark hard negative | 151 | 197 | +46 | OFF |
| 144210 | FOREGROUND boundary | 232 | 247 | +15 | OFF |
| 143532 | GOOD | 239 | 250 | +11 | OFF |

The guard therefore does not erase either current Branch-B positive and does not interfere with Branch C.

## Replay qualification

A research R3.8/H25/TC20/SAT3/curve02 luma proxy was checked against the eight Part-3 frames with exact historical rendered P75 values. Absolute P75 error was 0.25–1.75 Y, median 1 Y. It is useful for falsification but is not claimed as pixel-identical Android display output.

Across all 29 Part-3 DNGs the provisional selector proxy produced:

```text
HOLD             25
DARK_INTENT       2
DARK_ZERO_INTENT  1  (164436)
DARK_FOREGROUND   0
```

The `164436` activation motivated this protective probe. The Part-3 archive contains no original JPEGs, so `164436` is not retrospectively relabelled GOOD from the proxy.

## Architecture implication

Do not add a fourth DARK branch. If prospective evidence continues to support it, use this only as a protective veto inside Branch B:

```text
zeroIntentCandidate = existing Branch-B conjunction
if zeroIntentCandidate and LOCAL_SUBJECT_SURVIVAL:
    HOLD
elif zeroIntentCandidate:
    DARK_ZERO_INTENT
```

No new APK telemetry is required for further offline testing.

## Next falsification

1. Sweep available GOOD/BOUNDARY PRIMARY sidecars for the protective morphology.
2. Keep `142840` and `142939` mandatory Branch-B positives with guard OFF.
3. Keep `084858` as the extreme-dark hard negative.
4. Seek prospective compact-bright-subject low-key controls with the existing diagnostic APK; do not manufacture failures.
5. Integrate into BESTFIT1A only after prospective falsification.
6. No live lift is authorized.
