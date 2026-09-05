# M9EDGEPLACEMENT1A — September-4 Part-3 recovery

Research-only. No live selector and no photographic renderer mutation.

## 1. Archive bytes recovered

Mounted archive:

`again again part 3.zip`

Observed archive shape:

- ZIP members: **116**
- unique chronological capture stems: **30**
- DNGs: **29**
- JSON files: **87**
- JPEGs: **0**

Chronological capture range:

- first retained stem: `IMG_20260904_163347_1788536027742_00`
- last retained stem: `IMG_20260904_164845_1788536925171_00`

The archive therefore cannot directly reconstruct the original 121-JPEG visual
ordering from JPEG members. However, the sidecar telemetry contains an
independent ordinal anchor.

## 2. Global ordinal offset recovered from saturated-preview controls

The earlier visual corpus retained these known safety ordinals:

- #41: `preview globalQ95 == 255`, positive capture assist
- #43: `preview globalQ95 == 255`, neutral / no achieved positive assist

Inside Part-3, chronological local positions are:

### local #11

`IMG_20260904_164035_1788536435593_00`

- preview `globalQ95 = 255`
- achieved capture energy vs Photon-only: approximately `+0.070 EV`

### local #13

`IMG_20260904_164104_1788536464382_00`

- preview `globalQ95 = 255`
- achieved capture energy vs Photon-only: `0 EV`

The two local positions are separated by exactly two, and their positive/neutral
stress signatures match preserved global #41/#43 independently.

Therefore the Part-3 visual offset is:

`global ordinal = local ordinal + 30`

So Part-3 covers original visual ordinals approximately **#31–#60**.

This mapping is not inferred from archive name or assumed equal archive sizes; it
is anchored by the preserved q95/MFM safety pair.

## 3. Exact #40 DARK_FAIL recovered

Global #40 therefore maps to Part-3 local #10:

`IMG_20260904_164019_1788536419887_00`

Scene: backlit statue.

This matches the previously retained visual description of #40.

Exact app finished-render evidence from `_M9_PRIMARY.json`:

- build: `1.61-...sceneexposure1h...rendermeter1c...m10rmfmtest1a...`
- scene schema: `m9cam.sceneexposure.v8.renderaware1h`
- renderer schema: `m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1`
- preview global median: `65`
- preview q95: `204`
- achieved capture assist: approximately `+0.299 EV`
- TC20 gain: approximately `1.455x`
- base median gain request: `16x`
- TC20 guard gain: approximately `1.455x`
- RAW hard clipping: approximately `0.0000067`
- finished global median: `5`
- finished center median: `5`
- finished middle-center median: `4`
- finished global q95: `155`
- finished global q99: `216`
- finished dark fraction <=Y64: approximately `0.8766`
- center dark fraction <=Y64: approximately `0.9232`

The RAW is not broadly blown. The body collapses in the finished frozen JPEG.

`#40` is now an **exact-ID DARK_FAIL**, not merely an ordinal label.

## 4. Same-build cohort established

All 29 `_M9.json` capture sidecars in Part-3 report the same build generation:

`1.61-m9modern7r38...sceneexposure1h...rendermeter1c...m10rmfmtest1a...capturemeter1b`

All 29 also report:

- scene schema `m9cam.sceneexposure.v8.renderaware1h`
- frozen renderer schema `m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1`

This is exactly the kind of compatible cohort required by
`m9edgeplacement1a_cohort_readiness.py`.

The high-value review groups from this same build are now:

### priority GOOD-pool hard negatives

- #32
- #35
- #39
- #45
- #46
- #47
- #51
- #52
- #56
- #57
- #59

These are ordinary paths / trees / swan scenes in the recovered frozen R3.8
replay and are the first candidates for same-build GOOD confirmation.

### priority boundary review

- #38
- #44
- #53
- #54
- #55
- #58

These are deliberately retained as review/boundary candidates rather than
force-labelled because they are very dense or backlit yet may still be
photographically coherent.

### safety controls

- #41 = exact `IMG_20260904_164035_1788536435593_00`
- #43 = exact `IMG_20260904_164104_1788536464382_00`

Saturation is not a placement label.

## 5. RENDERMETER1C is falsified as a standalone DARK gate

This recovered same-build cohort gives a strong negative result for the old
render-meter evidence model.

Among the 29 sidecar-backed Part-3 frames:

- `renderLiftNeedEvidence >= 0.95`: **24 / 29**
- `wholeFrameStarvationEvidence >= 0.95`: **24 / 29**
- `renderLiftNeedEvidence >= 0.50`: **25 / 29**
- only **4 / 29** have `renderHoldEvidence > 0.10`

Several ordinary healthy-looking path/tree/animal renders therefore receive the
same nominal `liftNeed=1 / starvation=1 / hold=0` signature as confirmed #40.

This is expected from the original RENDERMETER1C design: it was an
**evidence-only calibration model**, not a production classifier. The new corpus
now demonstrates why that distinction matters.

Do not promote:

`renderLiftNeedEvidence == 1`

or:

`wholeFrameStarvationEvidence == 1`

as live DARK authority.

## 6. Other simple DARK predictors also remain rejected

Part-3 plus the September-2 boundary controls continue to falsify simple rules
based on any one of:

- preview darkness
- preview dark occupancy
- low RAW q99
- TC20 guard binding
- more severe TC20 guard margin
- positive MFM / capture assist
- finished global darkness alone

A photograph can be intentionally dense and still be correct.

The research target is narrower:

> identify **wrong useful-body collapse** after the frozen rendering decision,
> while protecting coherent M9 darkness, intentional silhouettes, bright subjects
> on dark backgrounds, and off-center subjects.

## 7. Likely next diagnostic direction

Part-3 shows why global + centre-only finished-render statistics are insufficient.
Examples such as bright swans on dark backgrounds can be photographically valid
while global and centre medians remain extremely low.

The next offline diagnostic should therefore test a small finished-render spatial
grid, not semantic face detection and not local tone mapping.

Candidate research-only `RENDERGRID1A`:

1. sample the finished frozen bitmap at the same tiny diagnostic resolution;
2. compute a 4x6 or 3x3 grid of cell medians / q95 / dark occupancy;
3. compare spatial support against incoming preview geometry / existing 4x6 M10-R-inspired topology;
4. search only conservative conjunctions;
5. rank zero false activation on confirmed GOOD and BOUNDARY first;
6. Frozen remains mandatory fallback.

The grid is classifier evidence only. It must not become spatial/local image
processing.

## 8. Current label count effect

New exact DARK labels now include:

- `IMG_20260903_094446_1788425086751_00`
- `IMG_20260903_095258_1788425578865_00`
- `IMG_20260904_164019_1788536419887_00` (#40)

So the global DARK target-count minimum is no longer the immediate blocker.

The blocker has shifted to **confirmed GOOD/boundary specificity**, especially
same-build 1.61/v8/R3.8 controls.

No live APK correction is authorized by this recovery.
