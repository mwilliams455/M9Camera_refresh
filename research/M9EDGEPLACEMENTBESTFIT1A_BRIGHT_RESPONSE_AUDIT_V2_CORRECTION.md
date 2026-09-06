# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT RESPONSE AUDIT V2 CORRECTION

**Status:** research-tool correction only  
**No photographic path change.**

## 1. Correction discovered during Prospect-2 freeze

Review of `m9edgeplacementbestfit1a_bright_response_audit.py` found two semantic extraction defects in the first audit harness revision.

### Defect A — achieved intent path

The original audit looked recursively for compatibility names such as:

```text
achievedIntentEv
intentAchievedEv
```

The current diagnostic capture schema actually records the relevant achieved capture offset at:

```text
m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv
```

with:

```text
m9ExposureAudit.derived.captureEnergyVsPreviewEv
```

available as a fallback/reference coordinate.

Therefore audit-v1 could report intent as missing even when the current sidecar contained the exact value.

The corrected v2 parser uses `captureEnergyVsPhotonOnlyEv` first and never assumes missing intent is zero.

### Defect B — applied TC20 gain versus base median gain

The LOWKEY seed is defined using the **actual applied TC20 gain**:

```text
tc20Gain >= 1.50
```

Audit-v1 extracted `baseMedianGain` for this condition.

That is incorrect on guard-limited frames because:

```text
baseMedianGain
```

is the gain the median branch would like, while:

```text
gain
```

is the gain TC20 actually applies after median/guard arbitration and clamps.

A concrete prospective control demonstrates the importance:

```text
181423
structuralLowKeyScore  ~0.808704
applied TC20 gain      ~1.4461x
baseMedianGain         ~5.7030x
```

Using `baseMedianGain` would incorrectly satisfy the 1.50 gain floor even though the renderer actually applied less than the required normalization gain.

Audit-v2 now resolves the TC20 decision dictionary containing:

```text
gain
baseMedianGain
tc20GuardGain
```

and uses only `gain` for LOWKEY eligibility. Base and guard values remain diagnostics.

## 2. What this correction does NOT invalidate

### `BRIGHT_BROADOPENING FULL47 1A` remains valid

The full47 BROAD result depends only on direct preview and finished-image luminance percentiles:

```text
medianShiftEv = log2(finishedMedian / previewMedian)
q95ShiftEv    = log2(finishedQ95 / previewQ95)
```

It found only:

```text
181404
181559
```

as BROAD-positive in 47 frames.

Neither achieved intent nor TC20 gain is part of the BROAD sign test, so the audit-v1 defects do not affect this 2/47 result.

### `LOWKEY_BROAD FULL47 1A` remains valid

Because only two frames survived BROAD, the conjunction was closed directly on those two frames using their exact diagnostics:

```text
181404
  structuralLowKeyScore ~0.544791 < 0.60
  => LOWKEY OFF

181559
  achieved intent ~0
  structuralLowKeyScore 0.876096
  applied TC20 gain ~2.0633x
  finished median 82Y
  => LOWKEY ON
```

Therefore the existing conclusion:

```text
1 / 47 LOWKEY_BROAD1A positive
= 181559 only
```

is unchanged.

## 3. What must NOT be reused from audit-v1

Do not rely on any audit-v1 aggregate claiming:

- LOWKEY activation count;
- intent-known count;
- applied-gain qualification;
- LOWKEY_BROAD count derived solely through the old parser.

Those quantities must be regenerated with audit schema:

```text
m9edgeplacementbestfit1a.brightresponseaudit.v2
```

The direct published BROAD full47 measurements and the manually closed two-frame conjunction remain the current evidence baseline.

## 4. Regression protection added

The repository now includes dedicated tests that lock:

1. `181559`-shaped diagnostics -> LOWKEY+BROAD positive;
2. `181423`-shaped diagnostics -> base gain may exceed 5x but applied gain <1.50 keeps LOWKEY OFF;
3. missing intent remains UNKNOWN, never zero;
4. exact `captureEnergyVsPhotonOnlyEv` takes precedence over compatibility aliases;
5. conflicting TC20 decision triplets are treated as ambiguous rather than silently selected.

The canonical multibranch selector also has regression tests for existing DARK branch priority and BRIGHT/HOLD semantics.

## 5. Current disposition

This is a research-harness correction, not a reason to change the camera.

The photographic conclusion remains:

> Frozen is the default; BRIGHT_LOWKEY_BROAD is a rare eligibility mechanism under prospective falsification; treatment severity and HOLD remain separate.
