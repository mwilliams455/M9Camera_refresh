# M9 BESTFIT1A — BRIGHT SEVERITY FALSIFICATION1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, colour science, JPEG quality, or DNG change.

## Purpose

Separate **mechanism evidence** from **treatment-strength authority**.

Recent retrospective work strengthens `PLACEMENTOPENING1A` / `BROADOPENING1A` as evidence that a coherent low-key scene was actually opened by the frozen render. That does **not** imply that any available scalar can safely determine how much RGB-pivot density should be applied.

This note explicitly falsifies the obvious strength mappings before they can enter production design.

## Reference classes

### HOLD / boundary

`181404`:

- structuralLowKeyScore ~0.5448
- TC20 gain ~2.554x
- frozen global median 82
- global median opening ~+0.072
- global q95 opening ~+0.030
- broadOpeningMinProxyEv ~+0.030
- centre median opening ~+0.659
- status: `BOUNDARY_HOLD`, Frozen

### NATURAL_MILD treatment-positive

`181559`:

- structuralLowKeyScore ~0.8761
- TC20 gain ~2.063x
- frozen global median ~82
- global median opening ~+0.313
- global q95 opening ~+0.191
- broadOpeningMinProxyEv ~+0.191
- centre median opening ~+0.599
- exact blind preference: RGB015 / RGB025 region

### Historical severe/treatment-positive LOWKEY anchors

`184927`:

- structuralLowKeyScore ~0.732
- TC20 gain ~2.63x
- frozen global median ~93
- blind preference: RGB075

`184937`:

- structuralLowKeyScore ~0.625
- TC20 gain ~1.60x
- frozen global median ~92
- blind preference: RGB050

`194307`:

- structuralLowKeyScore 1.000
- TC20 gain ~4.94x
- frozen global median ~87
- blind preference: RGB075 tentative

Historical paired preview/finished opening telemetry is not retained for these three, so opening magnitude cannot yet be evaluated as a severe-strength predictor.

## Candidate severity features

| candidate | evidence | result |
|---|---|---|
| `structuralLowKeyScore` magnitude | mild 181559 ~0.876; severe anchors span ~0.625, ~0.732, 1.000 | **REJECT strength mapping** |
| TC20 gain magnitude | mild ~2.06; severe anchors span ~1.60, ~2.63, ~4.94 | **REJECT strength mapping** |
| frozen global median | mild ~82; severe ~87–93; near-matched 184927/184937 still prefer different strengths | **REJECT direct strength mapping** |
| centre opening magnitude | HOLD 181404 ~+0.659 > mild 181559 ~+0.599 | **REJECT** |
| q99 opening | positive on 8/29 same-build Part-3 controls while global body remains non-positive | **REJECT authority** |
| q95 opening alone | positive on GOOD 164510 and BOUNDARY 164622 while global median is non-positive | **REJECT authority** |
| global median opening sign | strong specificity evidence so far | **MECHANISM diagnostic, not strength** |
| `BROAD_POSITIVE` median+q95 sign | clean current ordering; 0/29 Part-3 broad-positive | **PROMISING corroboration, not strength** |
| `broadOpeningMinProxyEv` magnitude | HOLD ~+0.030 vs mild ~+0.191, but historical severe values unavailable | **UNRESOLVED; do not map to RGB strength** |
| MILDRESPONSE finished-response envelope | aligns with RGB015/RGB025 preference on two exact prospective frames | **SAFETY / rollback evidence, not scene severity** |
| visual confirmed severe class | historical RGB050/RGB075 preferences | **CURRENT ONLY severe authority; research labels only** |

## Strong falsifiers

### Score magnitude fails

If score magnitude controlled treatment strength, `181559` (~0.876) should be at least as severe as `184927` (~0.732) and `184937` (~0.625). It is not: the prospective frame only supports approximately RGB015–RGB025, while the historical pair prefers RGB075 / RGB050.

`194307` at score 1.0 does prefer a strong treatment, but that single point cannot repair the non-monotonic ordering.

### TC20 gain fails

`184937` prefers RGB050 at only ~1.60x gain, while `181559` at ~2.06x is NATURAL_MILD. Thus larger gain does not imply stronger desired density.

The natural cohort supplies an even stronger mechanism control: `174327` has ~4.32x TC20 gain and structural score ~0.876, yet its body becomes *denser* (preview 66 -> finished 39) and BRIGHT treatment is correctly OFF.

### Frozen median fails

`181559` and `181404` both finish around median 82, but one is mild-treatment positive and the other HOLD.

Historical `184927` and `184937` finish around 93/92 and prefer different strengths despite nearly identical body placement.

Frozen median can describe where the JPEG landed; it does not specify how much density is photographically desirable.

### Centre opening fails decisively

`181404` centre median moves 69 -> 109 (~+0.659 proxy), while `181559` moves 66 -> 100 (~+0.599).

If centre opening were a severity axis, the HOLD frame would rank *more severe* than the treatment-positive frame. Therefore centre movement is useful only as spatial diagnostic context.

## What remains viable

The evidence currently supports a **categorical, HOLD-first** architecture rather than a continuous severity formula:

```text
BRIGHT subtype eligibility
  -> mechanism corroboration (PLACEMENTOPENING / BROADOPENING)
  -> HOLD if evidence is weak, mixed, or Frozen is already right
  -> unknown natural activation defaults to NATURAL_MILD research class
       -> RGB015 first
       -> RGB025 escalation-only
       -> RGB035 stress bound
  -> SEVERE_CONFIRMED_FAIL remains historical/visually confirmed research class
       -> RGB035 / RGB050 / RGB075 bank
       -> no automatic severe classifier yet
  -> finished-response safety / rollback
  -> Frozen fallback
```

This architecture intentionally sacrifices automatic severe recall until a genuine discriminator is found.

## Why this is preferable

The project already renders most photographs correctly. The cost of under-correcting a rare BRIGHT edge case is a JPEG that can still be developed from DNG. The cost of falsely applying a strong density treatment is erosion of an already-correct M9-like JPEG.

Therefore unknown cases should bias toward:

```text
Frozen > mild probe > strong treatment
```

not toward strongest-safe treatment.

## Next falsification target

The next useful research question is not “which scalar maps to 0.15 / 0.25 / 0.50 / 0.75?”

It is:

> Can any existing evidence reliably distinguish `HOLD` from `NATURAL_MILD` *before* visual treatment review without creating GOOD false corrections?

`BROADOPENING1A` is the best current candidate for that narrower role. Its magnitude must remain a ranking diagnostic until severe historical paired telemetry or an independent prospective cohort supports more.
