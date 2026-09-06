# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY+BROAD PROSPECTIVE-2 PROTOCOL

**Status: SUSPENDED — do not request new photographs yet.**  
**Branch:** `m9edgeplacementbestfit1a-offline3`  
**Supersedes:** the earlier instruction to collect another natural cohort immediately.

## Why this protocol is suspended

The project already has a large recent natural-shooting corpus from the last ~36 hours. Repeatedly asking for another cohort before exhausting that material is not justified.

Current Dropbox evidence under `/chatgpt/m9/exposure` includes:

- hundreds of diagnostic bundle files;
- September-5 JPEG/DNG/capture/PRIMARY assets;
- the 47-frame untouched late-afternoon cohort;
- the 13-frame morning hard-negative/control cohort;
- additional same-day natural frames and diagnostic bundles beyond the repeatedly discussed anchors.

The next task is therefore **existing-corpus exhaustion**, not more shooting.

Git history preserves the original Prospective-2 capture protocol if it is needed later.

## Frozen research rule remains unchanged

Do not retune these values while auditing the existing corpus.

```text
BRIGHT_LOWKEY_OPENING1A =
    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND appliedTc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75
```

Important correction: `appliedTc20Gain` means the renderer's actual `gain`, not `baseMedianGain`.

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BRIGHT_BROADOPENING1A =
    medianShiftEv > 0
    AND q95ShiftEv > 0
```

```text
BRIGHT_LOWKEY_BROAD1A =
    BRIGHT_LOWKEY_OPENING1A
    AND BRIGHT_BROADOPENING1A
```

No BROAD magnitude threshold is introduced. Treatment/severity remains separate.

## Required existing-corpus work order

Before any new capture request:

1. inventory every recent September-5 frame for which JPEG + capture diagnostics + PRIMARY diagnostics exist;
2. deduplicate diagnostic-bundle copies by photographic frame identity;
3. run the corrected BRIGHT response auditor over every usable frame;
4. score every frame with the frozen LOWKEY, BROAD, and LOWKEY_BROAD rules;
5. rank all `LOWKEY_BROAD` activations first;
6. rank all BROAD-positive / LOWKEY-negative near misses second;
7. rank high-lowkey-score dense controls third;
8. join every existing visual label from prior chats/research notes where possible;
9. visually inspect any new activation against its Frozen JPEG before applying treatment;
10. only after the available corpus has been exhausted decide whether a genuinely new cohort is necessary.

## Existing prospective anchors remain evidence, not the whole corpus

Retained examples:

```text
181404 -> BROAD ON, LOWKEY OFF, HOLD/Frozen
181559 -> BROAD ON, LOWKEY ON, mild-treatment positive
```

These are useful anchors, but the audit must not keep recycling only these two images.

## Treatment policy remains unchanged

Detection does not imply mandatory correction.

```text
mechanism eligibility
        ↓
photographic severity / treatment value
        ↓
HOLD whenever Frozen is already right
        ↓
if justified: RGB015 first
               RGB025 escalation only
        ↓
finished-response safety / rollback
```

Do not revive MIDKEY by threshold fitting. Do not map structuralLowKeyScore, TC20 gain, finished median, or BROAD magnitude monotonically to treatment strength.

## New-capture bar

A new shooting request is allowed only when one of these is true:

- the recent existing corpus has been exhaustively scored and deduplicated;
- a specific missing morphology cannot be represented by any retained frame;
- a controlled prospective replication is required to falsify one already-defined hypothesis.

Generic requests for another ordinary natural cohort are explicitly disallowed until then.
