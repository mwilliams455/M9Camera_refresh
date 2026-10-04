# M9 PROJECT HANDOFF v2.80 — TC20INTENT1A OFFLINE NEXT

Date: 2026-09-05
Project: M9 Project / M9Camera_refresh
Device target: Xiaomi 15 Ultra, rear wide/main camera
Current priority: preserve the frozen M9 photographic rendering and image quality while fixing exposure-intent transfer through TC20.

---

## 1. Executive state

The project has reached a cleaner development split.

The latest live field build, **v0.7ZZS / M10RMFMTEST1A**, is healthy and photographically intact. The M10-R-inspired 16×22 / 4×6 multi-field geometry appears promising for identifying backlit / spatially difficult scenes, but the field corpus also shows that positive capture assistance is being largely cancelled downstream by TC20's highlight-limited normalization.

Therefore the active investigation is now:

**TC20INTENT1A — offline first**

Do **not** increase MFM live positive exposure magnitude yet. Do **not** build a combined live meter + TC20 change yet. Do **not** add SUBJECTLIFT yet.

The immediate goal is to answer:

> When the meter or photographer intentionally gives the sensor +0.10 to +0.30 EV of real exposure, how much of that intent should TC20 preserve in the finished M9 rendering without damaging highlights, deep blacks, colour, or the frozen M9 character?

---

## 2. Current repository state

Repository:

`mwilliams455/M9Camera_refresh`

### Active offline investigation branch

`tc20intent1a-offline3`

Current head:

`35dd589fc1496b9eb5fd7becb61d6573b3cb241d`

Head commit message:

`Verify TC20INTENT1A replay syntax in CI`

Relevant recent commit chain:

- `f6eed8954a452cd8b43936cf39d084cdd79351d1` — Add TC20INTENT1A offline replay harness
- `f429e578efab35cc9418ebc0691b4320aa705968` — Harden TC20INTENT1A corpus replay and bundle indexing
- `35dd589fc1496b9eb5fd7becb61d6573b3cb241d` — Verify TC20INTENT1A replay syntax in CI

### Offline replay harness

`research/tc20intent1a_replay.py`

This is research-only and does not alter the Android runtime renderer.

### Latest CI validation

GitHub Actions run:

`33910863216` / run number 149

Result:

**SUCCESS**

Verified steps include:

- TC20INTENT1A offline harness syntax
- full cumulative M9 patch chain
- M10RMFMTEST1A verifier chain
- Android `assembleDebug`
- artifact upload

Artifact from run 149:

`M9Cam-v0.7ZZS-M10RMFMTEST1A-EXACT-INTEGRAL-4x6-PERF3I-recovered`

Artifact ID:

`9951394013`

Artifact digest:

`sha256:1e1e1a6998d207b4c4dedace2cc752cf594ceef14ae5e609e2fe1b16266463db`

Important: the APK generated on the offline branch is only a CI regression check of the existing live v0.7ZZS chain. The TC20INTENT1A experiment itself is **offline only** at this point.

---

## 3. Frozen photographic constraints

Do not change these while evaluating TC20INTENT1A:

- 12 MP output, approximately 4096×3072
- JPEG + DNG automatic save
- JPEG quality 95
- current R3.8-H25/TG1 photographic behavior
- Cobalt Xiaomi 15 Ultra main-camera calibration
- M9 bridge / colour conversion
- SAT3 M06/M07
- firmware curve02
- exact BT.601 4:2:2 path
- current WB/CCT/TG1 path
- current DNG pixels
- current OpenCV / demosaic path
- frozen dense-shadow / signed-negative M9 character

Image quality remains higher priority than speed. Do not trade visible photographic quality for performance.

No global black lift.

---

## 4. Accepted field-corpus baseline

Five test archives from the latest v0.7ZZS field session are the active corpus:

- `photos.zip`
- `again part 1.zip`
- `again again part 2.zip`
- `again again part 3.zip`
- `again again 4.zip`

Accepted corpus baseline:

- JPEGs: **121**
- complete capture/RAW sets: **120**
- exact capture/RAW identity: **120 / 120**
- primary timing records: **120 / 120**
- queue accepted: **120 / 120**
- DNG async fallback: **0**
- JPEG and DNG saved: **120 / 120**
- median render time: **592 ms**
- mean render time: **608 ms**
- render range: **497–958 ms**
- fastest successive captures: approximately **2.097 s** apart

This supersedes the earlier accidental 119-timing-record count.

Runtime conclusion:

**No evidence of the former crash/freeze/queue-ownership regression in this corpus.**

---

## 5. M10RMFMTEST1A field findings

MFM live decisions across the 120 captures:

- positive: **27**
- neutral: **93**
- negative: **0**

Mean requested positive assist:

`+0.267 EV`

Mean actual achieved capture change:

`+0.261 EV`

Maximum requested assist:

`+0.532 EV`

Camera2 request/result behavior was good; requested assistance was being achieved apart from ordinary ISO / exposure-time quantisation.

### Important MFM snapshot bug

For **16 of the 27** corrected captures, the mutable `m9M10rMfmTest.appliedExposureCorrectionEv` snapshot was later overwritten by a preflight evaluation and ended up showing zero.

For this corpus, use:

`m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv`

as the authoritative achieved intent value.

Do not use the overwrite-prone MFM snapshot as the intent source.

### M10-R architecture conclusion

The recovered M10-R-style geometry remains useful:

- 16×22 preview grid
- exact recovered M10-R Integral spatial weighting mask
- 4×6 / 24-region spatial topology

It often selects plausible backlit / spatially difficult scenes and does not produce a general HDR-like lift.

However, MFMTEST1A has **not** demonstrated that stronger capture EV by itself will fix the finished JPEG.

---

## 6. Why TC20 is now the central problem

All **27 positive MFM captures** were found to be limited by TC20's **highlight guard**, not by the median-derived gain.

Representative examples:

- fire engine / bright window: capture assist roughly +0.25 EV; base gain wanted ~15×; guard held actual gain near ~1.08×
- backlit statue: capture assist roughly +0.30 EV; base gain wanted ~16×; guard held actual gain near ~1.46×
- sculpture / bright field: capture assist roughly +0.24 EV; base gain wanted ~12.8×; guard held actual gain near ~1.71×

Mechanism:

1. capture exposure increases by +δ
2. RAW median and RAW upper tail rise
3. TC20 highlight guard sees the higher tail
4. TC20 gain drops approximately inversely
5. much of the intended JPEG tonal movement is cancelled

This means extra real exposure is not useless — it can improve shadow signal / SNR — but the renderer may remove much of its visible global exposure effect.

Therefore the next breakthrough is more likely to come from **coordinating capture intent with TC20** than from simply increasing MFM capture EV.

---

## 7. RAW safety-oracle caution

Do not interpret repeated `+0.50 EV` additional headroom as a photographic recommendation.

In the current corpus, the heuristic RAW model reaches its hard +0.50 EV measurement cap in many frames. Therefore repeated values of approximately +0.50 EV remaining headroom often mean:

> the oracle stopped measuring at its cap

not:

> the photograph definitely wants another half stop

The RAW model remains useful as a **constraint teacher**, not as the target magnitude.

It is heuristic and based principally on high RAW percentiles, hard clipping evidence, and linear counterfactual scaling.

---

## 8. Highlight-stress cohort

The saturated-preview cases are especially important.

Positive-assist stress frames include:

- #9
- #41
- #121

These had `preview globalQ95 == 255` and already meaningful RAW clipping.

Across all globalQ95==255 examples, the corpus showed appreciable existing clipping.

Current policy direction for future MFM2A:

`preview globalQ95 == 255 -> veto positive automatic capture assist`

For TC20INTENT1A, these frames are **not** used to select the preferred normal strength. They are a destructive / safety cohort used to reveal whether intent-preservation worsens an already-stressed highlight situation.

Also continue logging / evaluating:

`brightFractionGE240`

It appeared more promising than q95 alone as a predictor of RAW clipping, but it is **not yet** calibrated into a direct EV ceiling.

---

## 9. CFC / history disposition

Do not restore CURRENTFRAMECEILING1A or historical nearest/tie as live authority.

The large corpus again showed that both can produce unsafe overshoot despite respectable average error.

Current decision:

- CURRENTFRAMECEILING1A: research-only
- nearest/tie historical constraints: research-only
- PHOTOMETRICNORM1A: useful foundation / evidence, not standalone live authority
- historical arbitration: premature

Do not return to this line until the capture/render intent-transfer problem is understood.

---

## 10. TC20INTENT1A experiment definition

The offline harness now evaluates five variants from the **same RAW**.

### A0 — frozen TC20

Exact frozen reference.

The harness asserts A0 gain against the authoritative frozen renderer's own `tc20_meter()` result before accepting experimental output.

If A0 parity fails, the experiment stops.

### A1_010 — preserve up to +0.10 EV

Intent source:

`m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv`

Preserved intent:

`min(max(actualCaptureEnergyVsPhotonOnlyEv, 0), 0.10)`

TC20 virtual measurement:

`virtualMedian = physicalMedian / 2^preservedIntent`

`virtualTail = physicalTail / 2^preservedIntent`

Candidate gain is calculated from the virtual measurements and applied to the **actual unchanged RAW**.

### A1_020

Same experiment, cap +0.20 EV.

### A1_030

Same experiment, cap +0.30 EV.

### A2_020 — clipping-location probe

Uses the same A1_020 intent-aware gain, but defers the current early per-channel `RAW_MAX` clamp until the later matrix/LUT indexing boundary.

Purpose:

> determine whether curve02 / Leica matrix-LUT handling can accommodate a small amount of intentionally elevated upper energy more gracefully if it is not destroyed by the current pre-matrix channel clamp

A2 is research-only.

It is **not** a new production highlight policy.

Do not invent a new shoulder or arbitrary gain blend before A1/A2 results are understood.

---

## 11. Physical vs virtual telemetry rule

Never hide physical highlight damage by normalising it away.

Every variant keeps both:

### Physical RAW measurements

- `physicalMedian`
- `physicalTail`
- `physicalHardClipFraction`
- physical TC20 base gain
- physical TC20 guard gain
- physical binding term

### Virtual experiment measurements

- `virtualMedian`
- `virtualTail`
- virtual base gain
- virtual guard gain
- virtual binding term
- `preservedIntentEv`
- candidate gain
- gain delta versus A0

Physical RAW clipping remains authoritative evidence of actual sensor damage.

---

## 12. Replay telemetry currently produced

Per frame / variant the hardened harness records at least:

- actual `captureEnergyVsPhotonOnlyEv`
- metadata source and source path
- preview `globalQ95`
- preview `brightFractionGE240`
- positive-intent cohort flag
- saturated-preview safety-cohort flag
- physical hard clip fraction
- physical median / tail
- virtual median / tail
- physical / virtual base gain
- physical / virtual guard gain
- physical / virtual binding term
- A0 gain
- candidate gain
- gain delta versus A0 in EV
- `physicalTailTimesGain`
- pre-matrix any-channel clip fraction
- pre-matrix all-channel clip fraction
- matrix-index high / low clip fraction
- rendered near-white fraction
- rendered any-channel full-clip fraction
- rendered all-channel full-white fraction
- global rendered median
- center rendered median
- rendered q95 / q99
- deep-black fraction
- deltas versus A0

The harness also produces:

- `tc20intent1a_metrics.csv`
- `blind_key.csv`
- `skipped.csv` when needed
- `summary.json`
- `manifest.json`
- per-frame randomized blinded contact sheets
- all A0/A1/A2 rendered JPEGs

Blinded labels are randomized as:

`P / Q / R / S / T`

with the decoding key saved separately.

---

## 13. Corpus metadata recovery fix

Important implementation detail:

Not every DNG necessarily has a standalone `_M9.json` exported beside it.

The hardened harness now indexes both:

1. standalone capture JSONs
2. `capture_metadata` payloads embedded in `M9_DIAGNOSTICS_BURST_*.json`

DNG pairing is by the exact DNG filename.

If duplicate metadata representations disagree on `captureEnergyVsPhotonOnlyEv`, the harness refuses the frame rather than guessing.

This is necessary for the current field archives.

---

## 14. Execution limitation encountered in the current conversation

The five ZIP archives are present in the user's File Library / conversation history.

However, the current execution runtime began returning a platform `ClientError` for direct `/mnt/data` access through Python and container execution, so the actual DNG replay has **not yet been run** in this conversation.

Do not treat this as missing data.

Do **not** ask the user to re-shoot or re-upload the corpus without first checking whether the next runtime can access the existing File Library / active attachments.

If the next environment exposes the ZIPs byte-for-byte, immediately extract and run the offline harness.

If File Library search only returns file references and still cannot mount the ZIP bytes into execution, clearly state that this is a platform-access limitation rather than a data problem.

Do not fabricate A1/A2 numerical results.

---

## 15. Exact next action — Track A

### Step 1

Locate / mount / extract the five existing field archives.

Expected corpus:

120 unique DNGs with recoverable authoritative capture-intent audit records.

### Step 2

Run:

`research/tc20intent1a_replay.py`

against:

- the extracted corpus root
- authoritative frozen Python renderer `m9render_v26r35_tc20_frozen.py` or the exact equivalent frozen TC20 renderer currently used by the project
- Xiaomi 15 Ultra rear-wide Cobalt DCP
- M9 firmware / curve02 source

Do not substitute a different renderer or colour profile.

### Step 3

Confirm before interpreting anything:

- rendered DNG count is 120
- no unexpected metadata conflicts
- A0 parity max error is effectively zero
- positive intent count matches expected corpus behavior
- saturated-preview cohort is recovered correctly

### Step 4

Evaluate A1 on the **ordinary positive-intent cohort** first:

- A0
- A1_010
- A1_020
- A1_030

Questions:

1. Does subject / body placement improve progressively?
2. Do deep blacks remain stable?
3. Does the global rendering still look M9-like rather than HDR/open-shadow?
4. Do near-white / full-clip metrics grow gradually and acceptably?
5. Does the visible change correlate with actual achieved capture intent?

### Step 5

Evaluate #9 / #41 / #121 and other q95==255 frames separately.

They are stress tests, not preference votes.

### Step 6

Compare A2_020 against A1_020.

Key question:

> At the same preserved intent, does deferring the early pre-matrix clip preserve highlight shape / curve02 behavior better without introducing colour breakage or unacceptable clipping?

### Step 7

Perform blinded visual review on representative frames before choosing any production direction.

Priority scenes:

- fire engine / bright window
- backlit statue
- sculpture / bright field
- dark lane / bright background
- shaded park / backlight
- backlit person
- ordinary indoor controls
- ordinary daylight controls
- intentional low-key / silhouette
- saturated-preview stress cohort

---

## 16. Success criteria for TC20INTENT1A

TC20INTENT1A is successful only if several things line up.

Not enough:

> the JPEG is brighter

Required evidence:

- dense subject / foreground cases improve
- ordinary zero-intent scenes remain effectively unchanged
- intentional deep-black placement remains black
- 0.10 → 0.20 → 0.30 behaves progressively rather than breaking suddenly
- highlight stress increases gradually and explainably
- A0 remains exact frozen reference
- any preferred A1/A2 variant preserves M9 colour and contrast character
- physical clipping evidence remains visible and is not hidden by virtual normalisation
- visual change correlates with achieved exposure intent

Desired photographic relationship:

`meter / photographer gives more real exposure -> finished photograph reflects some of that exposure decision`

This is the more M9-faithful behavior.

---

## 17. Track B — M10RMFM2A preparation only

Track B may be prepared in parallel, but do not promote it into a new live APK until TC20INTENT1A is understood.

Approved M10RMFM2A scope:

- fix capture-frozen MFM diagnostics
- preserve the 16×22 grid
- preserve exact recovered Integral weighting
- preserve 4×6 / 24-region geometry
- add absolute body-level telemetry
- add preview highlight-risk telemetry
- log `brightFractionGE240`
- add `globalQ95 == 255` positive-assist veto
- keep positive MFM magnitude unchanged
- do not force the negative path to fire just for symmetry
- collect / label scenes that genuinely need negative capture exposure before tuning negative thresholds

Do not yet calibrate a complete continuous highlight ceiling from q95 or brightFractionGE240.

---

## 18. SUBJECTLIFT1A disposition

Subject lift remains a legitimate future tool, but is deferred.

Order of operations should be:

1. M10-R-style geometry identifies difficult scene structure
2. safe real sensor exposure is allocated
3. TC20 preserves appropriate intentional global exposure
4. frozen M9 renderer produces the global photographic result
5. only then measure any residual subject deficit
6. optional restrained local subject lift may address that residual

Any later subject lift must have strict controls against:

- halos
- flattened contrast
- global shadow opening
- grey blacks
- HDR appearance
- colour shifts

Manual EV should remain authoritative over any automatic subject lift.

---

## 19. Viewfinder direction

Longer-term, the electronic viewfinder should display a predictive approximation of the intended M9 render.

The phone viewfinder should not leave the photographer blind to the difference between Photon preview and the final M9 JPEG.

Preferred hierarchy:

`manual EV > automatic meter recommendation > optional subject assist`

Manual compensation must survive TC20 rather than being normalized away.

The predictive preview does not need full-resolution renderer parity, but it should show approximately the same intended tonal placement.

---

## 20. Colour / green-cast side track

A slight green/cyan tendency was observed in a mixed-light indoor portrait.

Do not compensate globally yet.

Keep this separate from exposure work.

Future colour telemetry should include:

- AsShotNeutral
- CCT
- TG1 weight
- neutral-region RGB/chroma
- rendered neutral RGB/chroma

The current TC20INTENT1A work should not retune WB, tint, Cobalt calibration, SAT3, or colour matrices.

---

## 21. What NOT to do next

Do not:

- increase MFM positive EV globally
- promote the RAW +0.50 EV oracle cap as a target
- restore CFC1A as authority
- restore nearest/tie historical matching as authority
- invent a new TC20 shoulder before A1/A2 results exist
- add global black lift
- alter curve02
- alter Cobalt calibration
- alter SAT3
- alter TG1
- reduce JPEG quality
- trade visible image quality for speed
- add live SUBJECTLIFT before intent-aware global rendering is understood
- treat q95==255 frames as ordinary preference examples
- use requested MFM EV instead of achieved capture audit EV
- use the mutable MFM snapshot as authoritative exposure intent
- claim exact M10-R numerical parity; the current M10-R contribution is architectural / spatial, not full CA9/Prepro numerical reproduction

---

## 22. Key current conclusion

The project has moved from:

`find a bigger automatic exposure correction`

to:

`make intentional capture exposure survive the renderer correctly`

That is the central next question.

M10RMFMTEST1A has demonstrated promising **scene selection** and a healthy live runtime. It has not yet demonstrated that simply increasing capture EV improves the finished photograph because TC20 is guard-limited on every positive MFM case in the current corpus.

The next decision should therefore come from **TC20INTENT1A offline A0/A1/A2 replay**, not from another live exposure-strength build.

---

## 23. Resume instruction for next conversation

Start by reading this handoff and checking the current branch:

`tc20intent1a-offline3`

Expected head at handoff creation:

`35dd589fc1496b9eb5fd7becb61d6573b3cb241d`

Then:

1. verify branch/head and CI run 149 still match
2. locate the existing five field ZIPs
3. attempt byte-level extraction in the active runtime
4. run `research/tc20intent1a_replay.py`
5. validate A0 parity and corpus count before interpreting results
6. compare A1_010 / A1_020 / A1_030 ordinary positive-intent cohort
7. evaluate q95==255 stress cohort separately
8. compare A2_020 to A1_020
9. choose next architecture only from the measured + blinded results

Do not build the combined live MFM2A + TC20INTENT1A APK before this offline result is understood.
