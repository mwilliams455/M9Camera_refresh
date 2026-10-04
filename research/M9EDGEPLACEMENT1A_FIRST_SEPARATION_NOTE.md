# M9EDGEPLACEMENT1A — first tail-separation note

Research-only. No live selector and no renderer mutation.

## 1. Corpus state

Placement labels presently supported by prior visual review:

- six exact `BRIGHT_FAIL` evening captures from v2.81;
- five September-4 v0.7ZZS `DARK_FAIL` scenes by corpus ordinal: #4, #40, #73, #80, #98;
- shaded-park #86/#87 retained as ambiguous/boundary controls;
- `IMG_20260904_101204` is an exact `GOOD + M9_STRONG` control;
- `IMG_20260904_080247_1788505367414_00` is a strong diagnostic dark candidate pending direct visual confirmation.

Exact ordinal-to-capture mapping for the five v0.7ZZS dark failures is still pending because the original ZIP bytes are not mounted in the current runtime. The visual labels themselves are not pending.

## 2. First important discriminator failure: TC20 branch is not enough

The six confirmed bright failures contain both TC20 binding families:

- five are primarily median-limited;
- `19:04:01` is highlight-guard limited.

The v0.7ZZS handoff establishes that all 27 positive-MFM captures were TC20 highlight-guard limited. The previously reviewed positive-MFM scene list includes #4, #40, #73, #80, #86, #87 and #98.

Therefore:

- all five visually confirmed v0.7ZZS `DARK_FAIL` frames (#4/#40/#73/#80/#98) sit in the guard-limited positive-MFM population;
- the two shaded-park boundary frames (#86/#87) also sit in the same population;
- at least one confirmed `BRIGHT_FAIL` (`19:04:01`) is guard-limited as well.

Conclusion:

> `tc20Binding == guard` cannot classify DARK_FAIL, and `tc20Binding == median` cannot classify BRIGHT_FAIL.

Binding branch is context, not authority.

## 3. What appears more promising for DARK_FAIL

The direct-render diagnostic capture `IMG_20260904_080247_1788505367414_00` supplies a useful shape for the dark-tail hypothesis.

Existing telemetry records approximately:

- TC20 gain: 1.269x
- base median gain: 7.012x
- therefore guard-limited
- RAW q99: 0.515
- RAW hard clip: ~0.000098
- finished global median: 17/255
- finished centre median: 11/255
- finished middle-centre median: 12/255
- finished centre q95: 98/255
- finished middle-centre q95: 81/255
- finished dark fraction <=Y64: ~0.809
- `wholeFrameStarvationEvidence = 1`
- `localizedUpperPlacementEvidence = 0`
- `globalBrightSupportEvidence ~= 0.000679`
- `renderLiftNeedEvidence = 1`
- `renderHoldEvidence = 0`

This is qualitatively different from merely having dense M9 shadows. The useful body itself is extremely low while there is no strong rendered-body adequacy/hold signal.

This suggests the dark-tail research question should be narrowed to:

> Among guard-limited / difficult spatial scenes, what diagnostic evidence distinguishes **healthy dense placement** from **finished useful-body collapse**?

Do not ask merely whether the scene is dark.

## 4. Candidate feature families to test first

Priority order once exact corpus identity is restored:

1. Existing render-meter evidence for offline truth checking:
   - `renderLiftNeedEvidence`
   - `renderHoldEvidence`
   - `wholeFrameStarvationEvidence`
   - `localizedUpperPlacementEvidence`
   - global/centre/middle-centre median and q95

2. Pre-render structural proxies that might predict the same failure without reading final JPEG:
   - centre/global median relationship
   - spatial low-region collapse
   - spatial axis separation
   - dark-body occupancy
   - upper bright-support occupancy
   - raw tail/headroom
   - TC20 guard/base margin

3. MFM/intent only as context:
   - achieved positive intent
   - whether TC20 subsequently cancelled that intent

Do not use positive MFM, high ISO or guard binding by themselves.

## 5. BRIGHT_FAIL remains asymmetric

Five of six confirmed bright failures are median-limited and were shown to be pushed toward a fixed TC20 body key. The sixth is guard-limited. This means the bright-tail gate will probably need a different evidence combination from the dark-tail gate.

Current architecture should therefore remain asymmetric:

```text
Frozen
  |
  +-- high-confidence BRIGHT_FAIL -> bounded density restraint / BESTFIT candidate
  |
  +-- high-confidence DARK_FAIL   -> independently developed recovery candidate
  |
  +-- otherwise                   -> Frozen
```

Do not force one signed scalar 'placement error' formula to solve both tails yet.

## 6. M9ness remains a separate axis

`GOOD + M9_IMPROVABLE` is intentionally valid and must remain GOOD for placement training. The M9ness tag is for later BESTFIT/treatment evaluation and must not become exception-gate authority.

## 7. Immediate blocker

Quantitative threshold/rule search should not be interpreted until:

- at least five exact GOOD controls are joined to diagnostics; and
- the five ordinal DARK_FAIL labels are mapped back to exact capture identities.

The new `m9edgeplacement1a_archive_index.py` exists specifically to reconstruct those mappings when the five archive bytes become accessible.
