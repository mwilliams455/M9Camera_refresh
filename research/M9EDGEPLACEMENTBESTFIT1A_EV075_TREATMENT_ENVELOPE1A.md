# M9 EDGEPLACEMENT — EV075 TREATMENT ENVELOPE1A

Research-only. No live APK or frozen renderer changes.

## Proposal

Use ±0.75 EV as an absolute edge-correction envelope, not as a universal target.
Eligibility remains asymmetric (BRIGHT and DARK are separate selectors).
Treatment amount must be chosen separately from the hard envelope and separately from the finished-highlight safety veto.

Current DARK test used pre-curve +0.75 EV while preserving TC20 decision, H25/HSM, M9 bridge, SAT3 M06/M07, curve02, exact BT.601 4:2:2 and TG1.

Existing shadow highlight budget: q95 <= 242 Y and increase in Y>=224 area <= 0.040.

## +0.75 EV results

| Frame | Morphology | q95 0 EV | q95 +0.75 | ΔY>=224 | +0.75 inside budget? |
|---|---|---:|---:|---:|---|
| 142840 | DARK_ZERO_INTENT | 133 | 174 | 0.291 pp | YES |
| 142939 | DARK_ZERO_INTENT | 93 | 133 | 0.429 pp | YES |
| 144210 | DARK_FOREGROUND | 231 | 254 | 9.689 pp | NO |
| 174410 | DARK_ZERO_INTENT | 59 | 94 | 0.359 pp | YES |
| 174457 | DARK_ZERO_INTENT | 163 | 201 | 0.724 pp | YES |
| 174956 | DARK_ZERO_INTENT | 145 | 186 | 1.750 pp | YES |

## Interpretation

- Both original Branch-B anchors and all three prospective Branch-B positives remain safely inside the existing highlight budget at +0.75 EV.
- The foreground-placement anchor 144210 fails the budget at +0.75 EV and also at +0.50 EV; its previously accepted +0.25 EV remains the bounded result.
- Therefore +0.75 EV is defensible as a DARK-side hard research ceiling, but a strongest-safe-first policy would automatically drive every tested Branch-B case to +0.75. That is not equivalent to photographic best fit.
- Recommended architecture: selector -> severity/desired EV -> clamp to [-0.75,+0.75] -> finished-highlight veto/rollback -> publish.
- The same absolute envelope can be mirrored conceptually to BRIGHT at -0.75 EV, but negative-side treatment still requires direct replay of established BRIGHT_FAIL DNGs before promotion.

## Status

Provisional research envelope only. Do not change live APK yet.
