# M9 PROJECT HANDOFF v2.83
## EDGEPLACEMENTBESTFIT1A MULTI-BRANCH SEED → TARGETED PROSPECTIVE FALSIFICATION / REPLAY NEXT

**Date:** 2026-09-05  
**Project:** M9 Project — Leica M9-like Android camera app on Xiaomi 15 Ultra main camera  
**Repo:** `mwilliams455/M9Camera_refresh`  
**Research branch:** `m9edgeplacementbestfit1a-offline3`  
**Primary priority:** preserve current photographic quality and the current M9-like rendering. No broad exposure/tone change and no live edge-placement lift is authorized.

---

# 1. Executive conclusion

The first offline `EDGEPLACEMENTBESTFIT1A` pass supports the v2.82 conclusion that the DARK tail is not one failure class.

Three separate candidate morphologies now have useful first-order separation:

1. **INTENT_COLLAPSE**
   - canonical anchor `164048`
   - positive achieved capture intent
   - strong preview→finished upper/lower divergence
   - low finished useful-body placement
   - existing Part-3 conjunction remains the best current seed

2. **ZERO_INTENT_COLLAPSE**
   - anchors `142840`, `142939`
   - achieved intent ≈ 0 EV
   - broad matched-region preview→finished retention collapse
   - not primarily an upper/lower split problem

3. **FOREGROUND_COLLAPSE**
   - anchor `144210`
   - upper/high field survives
   - lower field loses much more placement than the rest of the frame
   - global finished P75 remains high

The current best-fit selector is still **research-only**.

> Do not promote any branch into a live lift yet.

---

# 2. Frozen photographic baseline remains unchanged

Do not alter:

- R3.8-H25/TG1
- Cobalt Xiaomi 15 Ultra main-camera calibration
- M9 bridge / HSM
- SAT3 M06/M07
- firmware curve02
- exact BT.601 4:2:2
- 12 MP output
- JPEG quality 95
- DNG + JPEG output
- current capture/exposure framework
- current TC20 rendering decision
- current exposure policy
- current color science

The edge-placement investigation remains a rare-case finished-placement correction project, not a new global exposure system.

---

# 3. New offline research branch

Branch:

`m9edgeplacementbestfit1a-offline3`

Created from:

`m9edgeplacementlift1a-offline2`

Parent SHA:

`61bb1bd03c94d5a5b7343b20af959f49ff1eb611`

Current research files:

- `research/m9edgeplacementbestfit1a_multibranch.py`
- `research/m9edgeplacementbestfit1a_anchor_audit.csv`
- `research/M9EDGEPLACEMENTBESTFIT1A_MULTIBRANCH_SEED.md`

Important commits:

- selector script: `45bde7f01c4e7d522e4ffd3df4363a32c61359ac`
- anchor audit CSV: `04554fda71ec2907ecf69e276c62521a0249fafc`
- seed findings: `bb227f17d68e70e0c91ce1cdad706a21cc3c5e8c`

The script emits diagnostic JSON only and explicitly records:

```text
liveLiftEnabled=false
thresholdStatus=provisional_falsification_seed_not_frozen_not_live
```

No capture or renderer source is changed on this branch.

---

# 4. Candidate Branch A — INTENT_COLLAPSE

Preserve the existing Part-3 conjunction unchanged for now:

```text
achievedIntentEv >= +0.10
upperLowerShiftEv >= +1.50
renderCellMedianP75 <= 30
integralRelativeShiftEv <= +0.15
```

Existing Part-3 result remains:

- `164048` DARK_FAIL -> ON
- `164019` DARK candidate -> ON
- `164402` GOOD -> OFF
- `163702` boundary -> OFF
- prior GOOD / boundary audit controls -> OFF

Do not widen Branch A merely to recover the newer failures. Those belong to different morphologies.

---

# 5. Candidate Branch B — ZERO_INTENT_COLLAPSE

The strongest new feature is broad matched-region retention.

Define for the same preview/finished 4x6-derived geometry:

```text
retentionEv = log2(renderRegionY / previewRegionY)
```

Exact 2 PM values:

| Frame | Class | Center | Lower | Upper | Edge | regions <= -1.50 EV |
|---|---|---:|---:|---:|---:|---:|
| 142840 | DARK_FAIL | -1.880 | -2.807 | -2.015 | -2.031 | 4/4 |
| 142939 | DARK_FAIL | -1.735 | -2.481 | -2.084 | -2.518 | 4/4 |
| 143432 | GOOD / mild boundary | -0.150 | -1.350 | -0.329 | -0.519 | 0/4 |
| 143532 | GOOD | -0.059 | -0.779 | -0.080 | -0.328 | 0/4 |
| 144210 | foreground boundary | -0.295 | -1.733 | -0.289 | -0.513 | 1/4 |

This is a much cleaner separation than a simple darkness test.

Provisional Branch B seed:

```text
achievedIntentEv < +0.10
previewSceneSpreadEv >= 1.30
previewBrightRegionFraction >= 0.20
renderCellMedianP75 <= 15
renderGridMeanY <= 30
at least 3 of {center, lower, upper, edge}
    have retentionEv <= -1.50
```

Current result:

- `142840` -> DARK_ZERO_INTENT
- `142939` -> DARK_ZERO_INTENT
- `143432` -> OFF
- `143532` -> OFF
- `144210` -> OFF

---

# 6. Why 084858 remains the critical hard negative

`084858` is visually GOOD despite being very dark and having approximately zero achieved intent.

Available preview structure:

```text
preview Integral Y ≈ 82.49
preview scene spread ≈ 0.875 EV
preview bright-region fraction = 0.125
preview upper/lower ≈ -0.207 EV
```

Legacy finished sampling:

```text
global mean ≈ 33.67
global median = 14
dark <= 64 ≈ 0.845
```

Therefore absolute finished darkness is unsafe.

The current Branch B seed remains OFF before matched finished geometry is needed because:

```text
sceneSpreadEv < 1.30
brightRegionFraction < 0.20
```

This is promising because it asks whether a preview with real tonal structure subsequently collapsed, instead of asking whether the JPEG is dark.

Caveat:

`084858` predates the exact `EDGEPLACEMENTGATE1A` finished 16x22 schema, so the same-schema 4x6 retention test is not available in its PRIMARY sidecar.

Do not claim full exact-schema hard-negative falsification for `084858` yet.

---

# 7. Other legacy protected controls

Two older controls provide useful supporting evidence but not exact spatial falsification.

## 084525 — GOOD control

Legacy finished-luma sampling:

```text
global mean ≈ 86.95
global median = 79
center mean ≈ 74.98
center median = 67
```

Preview MFM:

```text
scene spread ≈ 1.971 EV
upper/lower ≈ 1.569 EV
```

This frame does not resemble the catastrophic global finished collapse of `142840` / `142939`.

## 084154 — boundary control

Legacy finished-luma sampling:

```text
global mean ≈ 55.49
global median = 23
center mean ≈ 81.30
center median = 39
```

Preview MFM:

```text
scene spread ≈ 2.360 EV
```

Again this is materially healthier globally than the zero-intent failure anchors.

However both frames predate the exact finished spatial gate, so Branch C cannot be considered fully falsified on them.

---

# 8. Candidate Branch C — FOREGROUND / SPLIT-FIELD COLLAPSE

Use preview→finished change, not absolute finished spatial separation.

Exact 2 PM comparison:

| Frame | Class | preview U/L | render U/L | change | render lower | render P75 |
|---|---|---:|---:|---:|---:|---:|
| 143432 | GOOD / mild boundary | 1.947 | 2.968 | +1.021 | 21.51 | 183.5 |
| 143532 | GOOD | 1.496 | 2.195 | +0.699 | 43.59 | 207.5 |
| 144210 | foreground boundary | 2.161 | 3.605 | **+1.444** | **13.75** | 161.75 |

Provisional Branch C seed:

```text
upperLowerShiftEv >= +1.20
renderLower12Y <= 18
renderUpper6Y >= 140
renderCellMedianP75 >= 120
centerRetentionEv >= -1.00
```

Current result:

- `144210` -> DARK_FOREGROUND
- `143432` -> OFF
- `143532` -> OFF
- `142840` / `142939` -> OFF

This is deliberately not tied to achieved intent. It is a spatial finished-placement morphology.

---

# 9. Architecture decision — do not add on-device BESTFIT flag yet

The current `EDGEPLACEMENTGATE1A` helper is attached to the existing read-only finished-bitmap diagnostic and receives the finished `Bitmap` only.

It deliberately has no capture-side preview/intent context and reports:

```text
gateDecisionAvailableInRenderer=false
combinationPolicy=combine_with_capture_M9_json_preview_grid_and_achieved_intent_offline
```

Do not punch a new capture-metadata path through the renderer merely to make the BESTFIT result appear in the PRIMARY JSON.

The safer architecture for the next falsification is:

1. keep the existing diagnostic APK unchanged;
2. collect normal `*_M9.json` + `*_M9_PRIMARY.json` pairs;
3. run `m9edgeplacementbestfit1a_multibranch.py` offline;
4. inspect any activations visually;
5. only after the branch rules survive prospective controls consider a diagnostic on-device combiner.

This keeps the frozen photographic path untouched.

---

# 10. Current acceptance status

## Seed recall

Passes current anchors:

- `164048` -> DARK_INTENT
- `142840` -> DARK_ZERO_INTENT
- `142939` -> DARK_ZERO_INTENT
- `144210` -> DARK_FOREGROUND candidate

## Exact-schema protected controls

Current exact controls remain OFF:

- `143432`
- `143532`
- `164402` under Branch A
- `163702` under Branch A

## Legacy hard-negative evidence

Promising but not fully exact:

- `084858` -> Branch B preview guard OFF
- `084525` -> legacy finished body clearly healthier than zero-intent fails
- `084154` -> legacy finished body healthier, but Branch C spatial falsification unavailable

## Still not passed

- full exact-schema GOOD sweep for Branch B/C
- exact same-schema `084858` matched-retention check
- exact spatial Branch C check on older boundary/GOOD controls
- opposite-tail BRIGHT_FAIL audit under the full selector
- treatment-strength replay for current 2 PM DNGs

Therefore:

> **No live lift is authorized.**

---

# 11. Next experiment — targeted prospective falsification, not random shooting

Continue using the already-built:

`M9Cam-EDGEPLACEMENTGATE1A`

No new APK is required for the next pass.

The next capture batch should be intentionally small and should create exact-schema controls that replace the legacy telemetry gap.

Recommended minimum:

### A. Dark-but-GOOD low-key controls — 2 to 3 frames

Aim for deliberately dense scenes where a dark M9-like JPEG is still desirable.

Purpose:

- challenge Branch B
- reproduce the role of `084858` with exact finished geometry

### B. Bright-sky / dark-foreground controls that still look GOOD — 2 to 3 frames

Aim for scenes with a meaningful upper/lower split where the foreground remains photographically usable.

Purpose:

- challenge Branch C
- reproduce the role of `143432` under different composition/light

### C. Naturally encountered failure candidates — only if they occur

Do not force exposure or manually manufacture a failure.

If a JPEG genuinely collapses, keep it as prospective evidence and let the offline selector classify it before changing thresholds.

For every frame retain:

- JPEG
- DNG
- `*_M9.json`
- `*_M9_PRIMARY.json`

Do not change EV manually during this falsification unless a separate manual-EV control is explicitly desired.

---

# 12. What to do after the targeted batch

Run the offline selector over every pair and record:

```text
visual class
selector result
branch checks
preview structure
matched-region retention
finished spatial placement
```

Priority remains:

1. zero GOOD false positives
2. zero hard-negative activation
3. minimal boundary activation
4. correct subtype recall
5. treatment strength only after selector credibility

If the prospective controls remain clean, proceed to research-only pre-curve replay:

```text
Frozen
+0.15 EV
+0.25 EV
+0.35 EV
+0.50 EV research-only for severe zero-intent cases
```

Do not assume one lift for all three branches.

Likely treatment hypothesis remains:

- DARK_FOREGROUND: small, probably +0.15 to +0.25 range
- DARK_INTENT: likely +0.25 central treatment
- severe DARK_ZERO_INTENT: test through +0.50 only to understand severity scaling

These are research hypotheses, not live constants.

---

# 13. Bright tail remains separate

Known BRIGHT_FAIL anchors remain:

- `184927`
- `184937`
- `190346`
- `190401`
- `190429`
- `194307`

Do not merge BRIGHT_FAIL and DARK_FAIL.

Current conceptual split remains:

- DARK = useful-body / placement collapse
- BRIGHT = relative ambience / placement loss

The tails are asymmetric.

---

# 14. Do not do next

Do not:

- enable any edge-placement lift
- change capture AE
- change TC20 globally
- lift shadows globally
- move black point
- alter curve02
- alter color science
- alter JPEG quality
- add a renderer metadata dependency merely for convenience
- collapse A/B/C back into one threshold
- use old legacy luma controls as if they were exact same-schema evidence
- request a broad random shooting batch
- trade image quality for performance

---

# 15. Current project-level conclusion

`EDGEPLACEMENTBESTFIT1A` is now a credible **classification research direction**, but not yet a production selector.

The important advance is that the feature shapes make photographic sense:

- Branch A identifies a positive-intent render-placement collapse;
- Branch B identifies broad structural loss from a preview that contained real tonal support;
- Branch C identifies lower-field collapse while upper/high support survives.

That is much closer to the intended M9 project behavior than any global “dark image -> brighten it” rule.

The next evidence should be prospective exact-schema falsification of those branch boundaries while the frozen renderer remains untouched.
