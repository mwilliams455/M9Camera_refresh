# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot. No live selector is authorized from this state.

## Confirmed placement counts

### GOOD: 23

Ten Part-3 same-build R3.8 controls remain confirmed by direct visual review, but all previously assigned Part-3 global ordinal numbers are withdrawn. Their placement labels do not depend on the invalid ordinal mapping.

Seven prospective September-5 visual-first controls are now confirmed GOOD:

- `IMG_20260905_084106_1788594066806_00` — sunny path/tree; deep local shadow remains coherent
- `IMG_20260905_084129_1788594089422_00` — sunny path; strong luminance split remains photographically healthy
- `IMG_20260905_084146_1788594106149_00` — sunny path hard negative; healthy result despite approximately +0.176 EV actual capture intent
- `IMG_20260905_084224_1788594144656_00` — bright-sky path; correct dense placement at 0 EV actual offset
- `IMG_20260905_084303_1788594183914_00` — playground/grass; healthy strong-sun result and useful TC20 median-limited branch control
- `IMG_20260905_084325_1788594205278_00` — backlit swing hard negative; deep foreground/shadow density remains intentional and coherent
- `IMG_20260905_084328_1788594208373_00` — black-dog hard negative; very dark subject retains coat separation and must not be confused with scene underexposure

Additional historical/global GOOD controls remain joined, including `IMG_20260904_101204` (`M9_STRONG`).

### BOUNDARY: 6

Existing five boundaries remain. New prospective boundary:

- `IMG_20260905_084154_1788594114928_00` — direct-sun stress frame. Foreground is extremely dense but a silhouette/direct-sun interpretation remains photographically plausible; do not auto-promote to DARK_FAIL without explicit reviewer judgement.

### BRIGHT_FAIL: 6

Unchanged evening bright-tail set.

### DARK_FAIL: 3

- `IMG_20260903_094446_1788425086751_00`
- `IMG_20260903_095258_1788425578865_00`
- `IMG_20260904_164048_1788536448208_00` — likely retained visual #73, sculpture/statue against bright field/sky

`IMG_20260904_164019_1788536419887_00` remains an unconfirmed same-build DARK candidate. Its previous #40 assignment has been retracted.

## September-5 prospective field result

The prospective sequence is labelled directly by exact filename rather than reconstructed viewer ordinal. JPEG placement is judged first, then telemetry is interpreted.

### First four-frame block

| capture | label | actual capture offset vs Photon | TC20 base gain | TC20 guard gain | finished global median | center median | q95 |
|---|---|---:|---:|---:|---:|---:|---:|
| 084106 | GOOD | 0 EV | 4.216x | 2.233x | 43 | 57 | 224 |
| 084129 | GOOD | 0 EV | 3.544x | 2.301x | 49 | 99 | 230 |
| 084146 | GOOD | +0.176 EV | 1.968x | 1.910x | 78 | 110 | 227 |
| 084154 | BOUNDARY | +0.433 EV | 4.040x | 1.300x | 23 | 39 | 195 |

All four are TC20 highlight-guard limited. Therefore guard binding is again falsified as a placement class selector.

The set strengthens two negatives:

1. **absolute finished darkness is insufficient** — 084106 is visually GOOD with global median 43 and >58% of sampled output at or below Y64;
2. **positive capture intent is insufficient** — 084146 is GOOD after +0.176 EV actual capture offset.

084154 remains a hard boundary because its body is extremely dense after +0.433 EV actual capture offset, but direct sun in frame makes automatic lifting unsafe.

### Second four-frame visual block

Visual-first labels:

- `084224` — **GOOD**
- `084303` — **GOOD**
- `084325` — **GOOD** hard negative, backlit swing
- `084328` — **GOOD** hard negative, black dog

Telemetry is presently available for the first two:

| capture | actual offset vs Photon | diagnostic meter request vs Photon | TC20 base gain | TC20 guard gain | limiting branch | finished median | center median | q95 |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| 084224 | 0 EV | -0.192 EV | 2.236x | 2.052x | guard | 73 | 111 | 228 |
| 084303 | +0.098 EV | +0.202 EV | 2.462x | 2.552x | median | 84 | 103 | 230 |

This adds useful branch diversity. 084303 is a visually healthy **median-limited** result (`baseGain < guardGain`), so GOOD is not confined to guard-limited scenes.

084224 is also important because the completed-RAW diagnostic meter requests a negative correction while the actual frozen 0 EV capture already looks right. That reinforces the decision not to promote the diagnostic meter directly into live exposure control.

084325 and 084328 are retained from visual evidence even without matching sidecars in this upload block. They are valuable specificity controls: backlighting and a genuinely black subject can both produce very dark regions without constituting a DARK placement failure.

No thresholds are tuned from this prospective set.

## Part-3 ordinal correction

The earlier `+30` Part-3 global offset is withdrawn. Telemetry stress signatures were not unique ordinal identities. `164048` remains the strongest visual anchor as likely #73, but no complete ordinal reconstruction is required for the prospective test path.

## Global readiness guard

Defaults:

- minimum GOOD: 30
- minimum BOUNDARY: 2
- minimum target-tail examples: 2

Current counts:

- GOOD: **23 / 30**
- BOUNDARY: **6 / 2** — cleared
- BRIGHT_FAIL: **6 / 2** — cleared
- DARK_FAIL: **3 / 2** — cleared

Global interpretation remains **NOT READY** because GOOD is short by **7** controls.

## Compatible-cohort readiness

For the 1.61 / sceneexposure-v8 / frozen R3.8 Part-3 generation:

- compatible GOOD: **10 / 10** — cleared
- compatible BOUNDARY: **2 / 2** — cleared
- compatible confirmed DARK_FAIL: **1 / 2** — not cleared

The September-5 prospective frames are not silently folded into this historical Part-3 cohort count unless exact build/schema compatibility is explicitly established.

## RENDERMETER1C disposition unchanged

RENDERMETER1C remains descriptive evidence only, not standalone DARK authority.

## RENDERGRID1A / INTENTCOLLAPSE1A

The current Part-3 descriptive conjunction remains research-only. Prospective GOOD hard negatives now include low-output scenes, positive-intent scenes, backlit scenes, direct-sun ambiguity, a median-limited healthy scene, and a genuinely black subject. Any future DARK gate must survive all of them.

## Exposure-direction conclusion becoming stronger

The prospective field sequence increasingly separates **capture exposure** from **finished placement**:

- correct GOOD JPEGs occur at 0 EV and positive actual capture offsets;
- correct GOOD JPEGs occur in both TC20 guard-limited and median-limited branches;
- a diagnostic completed-RAW meter can request positive or negative capture changes on frames that are already visually correct;
- direct-sun density can remain photographically intentional even after positive capture assist.

Therefore the remaining edge problem should not be treated as a general live-AE calibration problem. Capture exposure should remain frozen while rare JPEG placement failures are studied independently.

## Immediate next actions

1. Continue prospective exact-filename testing.
2. Add at least **7 more confirmed GOOD** controls globally.
3. Seek several independently judged DARK_FAIL and BRIGHT_FAIL examples, while retaining intentional silhouettes/direct-sun/backlit/dark-object frames as specificity controls.
4. Judge JPEG placement first, then inspect telemetry.
5. Do not tune a rule from the same small set used to invent it.
6. Keep M9ness independent from placement.
7. Frozen remains mandatory fallback.

No live APK EDGEPLACEMENT correction is authorized from the current state.
