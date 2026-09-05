# M9EDGEPLACEMENTBESTFIT1A — SHADOWSTACK1A AUDIT

## Status
Research-only composite audit. No APK or pixel mutation.

## Proposed stack

1. Canonical BESTFIT1A answers only whether an edge-placement rescue is eligible:
   - `DARK_INTENT`
   - `DARK_ZERO_INTENT`
   - `DARK_FOREGROUND`
   - otherwise `HOLD`
2. `LOCALSUBJECTSURVIVAL1A` is a protective veto **only** for `DARK_ZERO_INTENT`.
3. `TREATMENTLADDER1A` runs only after a DARK selection:
   - +0.50
   - +0.35
   - +0.25
   - +0.15
   - frozen baseline
4. First candidate inside the provisional finished-highlight budget is accepted:
   - q95 <= 242 Y
   - increase in Y>=224 area <= +0.040 absolute
5. `HOLD` publishes the frozen baseline and never enters treatment.

## Established-anchor audit

| Anchor | Visual/research role | Canonical selector | Protective guard | Shadow result | Current treatment result |
|---|---|---|---|---|---:|
| 084858 | GOOD hard negative, very dark zero-intent | HOLD (preview guards reject B) | n/a | HOLD | 0 |
| 163553 | GOOD | HOLD | n/a | HOLD | 0 |
| 163702 | boundary hard negative | HOLD | local-subject guard ON but irrelevant | HOLD | 0 |
| 163847 | GOOD | HOLD | n/a | HOLD | 0 |
| 164019 | DARK candidate / intent collapse | DARK_INTENT | n/a | DARK_INTENT | +0.50 |
| 164048 | DARK_FAIL / intent collapse | DARK_INTENT | n/a | DARK_INTENT | +0.50 |
| 164247 | GOOD | HOLD | n/a | HOLD | 0 |
| 164331 | GOOD bright local subject | HOLD | guard ON but irrelevant | HOLD | 0 |
| 164402 | GOOD bright local subject | HOLD | guard ON but irrelevant | HOLD | 0 |
| 164420 | swan hard-negative pair member | HOLD (misses B by ~0.003 EV at one retention boundary) | guard ON | HOLD | 0 |
| 164436 | swan pair, canonical B candidate | DARK_ZERO_INTENT | guard ON | HOLD_LOCAL_SUBJECT_SURVIVAL | 0 |
| 142840 | DARK_FAIL, zero-intent broad collapse | DARK_ZERO_INTENT | guard OFF | DARK_ZERO_INTENT | +0.50 |
| 142939 | DARK_FAIL, zero-intent broad collapse | DARK_ZERO_INTENT | guard OFF | DARK_ZERO_INTENT | +0.50 |
| 143018 | exact 2PM control | HOLD | n/a | HOLD | 0 |
| 143027 | acceptable/boundary control | HOLD | n/a | HOLD | 0 |
| 143432 | GOOD/mild boundary | HOLD | n/a | HOLD | 0 |
| 143532 | GOOD | HOLD | n/a | HOLD | 0 |
| 144210 | foreground-placement boundary/problem | DARK_FOREGROUND | n/a | DARK_FOREGROUND | +0.25 |

## What this stack solves structurally

- Detection and treatment strength remain separate.
- Normal photographs remain bit-for-bit on the frozen path in concept: `HOLD` never enters rescue.
- A/B are allowed to take a stronger correction when the finished highlight response permits it.
- C naturally rolls back to a weaker correction without hard-coding `Branch C = +0.25`.
- Bright compact subjects can protect zero-intent dark scenes from an unnecessary broad lift.

## What is still weak

- `LOCALSUBJECTSURVIVAL1A` has morphology evidence but the swan pair is not a formally user-labelled prospective negative set.
- Branch C has only one strong positive treatment anchor (`144210`).
- The treatment budget is supported by five exact-DNG dark anchors, not yet a broad prospective set.
- A two-stage rerender is computationally more expensive on DARK edge cases, though DARK cases are expected to be rare.

## Promotion decision

Do **not** promote to live mutation yet.

The architecture is now coherent enough that additional threshold fitting on the existing anchors is more likely to overfit than improve it. The next useful evidence is prospective capture using the unchanged diagnostic APK and visual-first labelling.

Minimum useful prospective evidence before a live experiment:

- at least one additional natural foreground-placement failure resembling the Branch-C concept but not necessarily the same composition
- at least one bright-subject-in-dark-field hard negative that challenges the Branch-B protective guard
- at least one ordinary dark M9-looking scene that must remain HOLD

No exposure or EV manipulation should be used merely to force these conditions.
