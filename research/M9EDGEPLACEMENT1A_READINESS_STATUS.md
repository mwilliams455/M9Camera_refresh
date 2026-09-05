# M9EDGEPLACEMENT1A — current corpus readiness

Research-only status snapshot. No live selector is authorized from this state.

## Confirmed placement counts

### GOOD: 28

Ten Part-3 same-build R3.8 controls remain confirmed by direct visual review, but all previously assigned Part-3 global ordinal numbers are withdrawn. Their placement labels do not depend on the invalid ordinal mapping.

Twelve prospective September-5 visual-first controls are now confirmed GOOD:

- `IMG_20260905_084106_1788594066806_00` — sunny path/tree; deep local shadow remains coherent
- `IMG_20260905_084129_1788594089422_00` — sunny path; strong luminance split remains photographically healthy
- `IMG_20260905_084146_1788594106149_00` — sunny path hard negative; healthy result despite approximately +0.176 EV actual capture intent
- `IMG_20260905_084224_1788594144656_00` — bright-sky path; correct dense placement at 0 EV actual offset
- `IMG_20260905_084303_1788594183914_00` — playground/grass; healthy strong-sun result and useful TC20 median-limited branch control
- `IMG_20260905_084325_1788594205278_00` — backlit swing hard negative; deep foreground/shadow density remains intentional and coherent
- `IMG_20260905_084328_1788594208373_00` — black-dog hard negative; very dark subject retains coat separation and must not be confused with scene underexposure
- `IMG_20260905_084333_1788594213200_00` — second backlit swing hard negative; foreground remains deliberately dense yet retains readable structure
- `IMG_20260905_084513_1788594313506_00` — sunlit path/field control with deep vegetation and path shadow but coherent placement
- `IMG_20260905_084525_1788594325303_00` — black dog against bright grass; strong positive diagnostic meter demand is a false exposure cue on a visually correct frame
- `IMG_20260905_084712_1788594432601_00` — open path/field; deep lower-frame shade remains coherent and is a healthy median-limited control
- `IMG_20260905_084858_1788594538919_00` — shaded apple-tree canopy extreme-dark hard negative; very low finished luma remains photographically coherent and must not be auto-lifted

Additional historical/global GOOD controls remain joined, including `IMG_20260904_101204` (`M9_STRONG`).

### BOUNDARY: 6

Existing five boundaries remain. Prospective boundary:

- `IMG_20260905_084154_1788594114928_00` — direct-sun stress frame. Foreground is extremely dense but a silhouette/direct-sun interpretation remains photographically plausible; do not auto-promote to DARK_FAIL without explicit reviewer judgement.

### BRIGHT_FAIL: 6

Unchanged evening bright-tail set.

### DARK_FAIL: 3

- `IMG_20260903_094446_1788425086751_00`
- `IMG_20260903_095258_1788425578865_00`
- `IMG_20260904_164048_1788536448208_00` — likely retained visual #73, sculpture/statue against bright field/sky

`IMG_20260904_164019_1788536419887_00` remains an unconfirmed same-build DARK candidate. Its previous #40 assignment has been retracted.

## September-5 prospective field result

The prospective sequence is labelled directly by exact filename. JPEG placement is judged first; telemetry is interpreted only after the visual label is fixed.

### First block

| capture | label | actual offset vs Photon | TC20 base gain | TC20 guard gain | finished median | center median | q95 |
|---|---|---:|---:|---:|---:|---:|---:|
| 084106 | GOOD | 0 EV | 4.216x | 2.233x | 43 | 57 | 224 |
| 084129 | GOOD | 0 EV | 3.544x | 2.301x | 49 | 99 | 230 |
| 084146 | GOOD | +0.176 EV | 1.968x | 1.910x | 78 | 110 | 227 |
| 084154 | BOUNDARY | +0.433 EV | 4.040x | 1.300x | 23 | 39 | 195 |

This block falsified guard binding, absolute finished darkness, and positive capture intent as standalone DARK selectors.

### Second block

- `084224` — GOOD
- `084303` — GOOD
- `084325` — GOOD backlit hard negative
- `084328` — GOOD dark-subject hard negative
- `084333` — GOOD repeated-backlit hard negative

084224 is visually correct at 0 EV while the completed-RAW diagnostic meter requests approximately -0.192 EV. 084303 is visually correct in the TC20 median-limited branch. Repeated backlighting and a genuinely black subject therefore remain specificity controls rather than DARK evidence.

### Third block

Visual-first labels are all GOOD:

| capture | actual offset vs Photon | same-frame diagnostic meter request | TC20 base gain | TC20 guard gain | limiting branch | finished median | center median | q95 |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| 084513 | +0.084 EV | -0.231 EV | 1.639x | 1.938x | median | 76 | 131 | 219 |
| 084525 | 0 EV | +0.822 EV | 5.269x | 4.578x | guard | 79 | 67 | 226 |
| 084712 | 0 EV | -0.277 EV | 1.092x | 2.164x | median | 74 | 114 | 196 |
| 084858 | 0 EV | +0.907 EV | 7.395x | 1.690x | guard | 14 | 34 | 151 |

This block is particularly strong falsification evidence:

1. **Diagnostic meter direction is not photographic truth.** Two visually GOOD frames request negative changes and two visually GOOD frames request large positive changes.
2. **Large positive meter demand is insufficient.** 084525 is GOOD despite +0.822 EV same-frame meter demand.
3. **Severe TC20 guard suppression is insufficient.** 084858 is GOOD even though median demand is 7.395x and the guard allows only 1.690x.
4. **Extremely low finished output is insufficient.** 084858 is visually coherent with global median 14, center median 34, q95 151, and about 84.5% of sampled output at or below Y64.
5. **No single TC20 branch defines GOOD or failure.** Prospective GOOD frames exist in both median-limited and guard-limited branches.

084858 should be retained as an explicit extreme-dark hard negative for every future DARK gate. Any rule that automatically lifts it is too broad.

No thresholds are tuned from these prospective frames.

## Part-3 ordinal correction

The earlier `+30` Part-3 global offset is withdrawn. Telemetry stress signatures were not unique ordinal identities. `164048` remains the strongest visual anchor as likely #73, but no complete ordinal reconstruction is required for the prospective path.

## Global readiness guard

Defaults:

- minimum GOOD: 30
- minimum BOUNDARY: 2
- minimum target-tail examples: 2

Current counts:

- GOOD: **28 / 30**
- BOUNDARY: **6 / 2** — cleared
- BRIGHT_FAIL: **6 / 2** — cleared
- DARK_FAIL: **3 / 2** — cleared

Global interpretation remains **NOT READY** only because GOOD is short by **2** controls.

## Compatible-cohort readiness

For the historical 1.61 / sceneexposure-v8 / frozen R3.8 Part-3 generation:

- compatible GOOD: **10 / 10** — cleared
- compatible BOUNDARY: **2 / 2** — cleared
- compatible confirmed DARK_FAIL: **1 / 2** — not cleared

The September-5 prospective frames are not silently folded into that historical cohort count.

## RENDERMETER1C disposition

RENDERMETER1C remains descriptive evidence only, not standalone DARK authority. The new prospective set makes this restriction stronger, especially 084858.

## RENDERGRID1A / INTENTCOLLAPSE1A

The Part-3 descriptive conjunction remains research-only. Prospective hard negatives now span low-output scenes, positive-intent scenes, backlighting, repeated backlighting, direct sun, median-limited healthy scenes, genuinely black subjects, large positive diagnostic meter requests, and an extreme-dark canopy frame.

Any future DARK selector must survive all of them before production consideration.

## Exposure-direction conclusion

The prospective field sequence now strongly separates **capture exposure** from **finished placement**:

- visually correct JPEGs occur at 0 EV and positive actual capture offsets;
- visually correct JPEGs occur in both TC20 limiting branches;
- completed-RAW diagnostic meter requests can be strongly positive or negative on already-correct photographs;
- very dark local or global output can be intentional and photographically coherent;
- severe highlight-guard suppression can occur without a placement failure.

Therefore the remaining edge problem should not be treated as a general live-AE calibration problem. Capture exposure should remain frozen while rare JPEG placement failures are handled, if at all, by an independent and highly conservative finished-placement gate.

## Immediate next actions

1. Add **2 more confirmed GOOD** controls to clear the global readiness count.
2. Continue visual-first prospective labelling; do not hunt for telemetry-triggering scenes.
3. Retain 084858, 084525, 084333, 084328 and 084154 as hard specificity tests for any DARK proposal.
4. Do not tune a rule from the same small set used to invent it.
5. Keep M9ness independent from placement.
6. Frozen remains mandatory fallback.

No live APK EDGEPLACEMENT correction is authorized from the current state.
