# M9 BESTFIT1A — BRIGHT blind decode 1A

Research-only. No live renderer/APK change.

## User blind preferences

| Frame | Blind choice | Decoded | Interpretation |
|---|---|---|---|
| 184927 | R | RGB075 | clear preference |
| 184937 | Q/R leaning R | RGB050 over Frozen | medium treatment |
| 190346 | R/S leaning S | RGB075 over RGB035 | strong treatment |
| 190401 | R/S leaning R | Frozen over RGB050 | correction should be withheld |
| 190429 | Q/R | RGB075 / RGB035 tie | treatment preferred; magnitude unresolved |
| 194307 | maybe Q | RGB075 | tentative strong treatment |

## Main findings

1. RGB075 is preferred or tied on four of six confirmed BRIGHT_FAIL frames. A 0.75 EV pivot-strength ceiling is therefore supported photographically, not merely as a technical bound.
2. It is not a universal treatment. 184937 prefers RGB050 and 190401 prefers Frozen.
3. BRIGHT_LOWKEY_OPENING1A behaves well on this six-frame bank: it selects 184927, 184937 and 194307, all treatment-positive under the blind review; it rejects 190401, where Frozen wins.
4. 190346 and 190429 are treatment-positive misses for BRIGHT_LOWKEY_OPENING1A. They should seed a second BRIGHT morphology rather than cause the low-key branch to be widened.
5. Treatment magnitude is not monotonic in global median or structuralLowKeyScore. The near-matched 184927/184937 pair alone prefers 0.75 versus 0.50 despite similar placement statistics.
6. Zero false activation remains more important than full BRIGHT recall.

## Current architecture

```text
BRIGHT eligibility
  -> subtype A: LOWKEY_OPENING1A
  -> subtype B: unresolved second morphology (190346 / 190429 anchors)
  -> subtype-specific candidate density
  -> RGB pivot bank {0.35, 0.50, 0.75}
  -> lower-body / endpoint safety
  -> publish best safe candidate or Frozen
```

Do not weaken LOWKEY_OPENING1A to gain recall.
