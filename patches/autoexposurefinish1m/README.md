# M9AUTOEXPOSUREFINISH1M — HIGHLIGHTGRANDFATHER1A

## Why this exists

The 26 September FINISH1J rollback phone test reached the full **+2.5 EV**
backlight request and visibly overexposed the window. That proves the unrestricted
rollback is not a final policy.

Replaying the same 11-step meter bracket against HIGHLIGHTRET1A exposed the
opposite problem: it would stop after **+0.25 EV**, because two fields first
crossed the clip-growth threshold at +0.50 EV.

Those two fields were not new highlight structure. At the neutral reference they
already had:

- field 5: q90 = **233**, bright fraction = **1/6**
- field 17: q90 = **237**, bright fraction = **1/6**

So the old field counter contradicted its own intended rule that a pre-existing
bright window should be grandfathered.

## Change

A field is now treated as pre-existing highlight structure for the *field-level*
incremental growth counters when its neutral-reference q90 is **>= 220**.

220 is not a fitted EV value. It is a domain boundary: q90 is already within four
8-bit code values of the existing >=224 near-white population threshold.

The following remain unchanged and active:

- global clip-growth guard
- global bright-population growth guard
- genuinely emerging field protection below q90 220
- BGQUAL1A
- OPENANCHORBAL1A
- body lock/release
- M9 low-key/body targets
- single global capture exposure only; **no HDR**

## Frozen phone-bracket replay

For the supplied 12:18 backlit-window bracket:

- FINISH1J requested/applied: **+2.50 EV**
- HIGHLIGHTRET1A counterfactual: **+0.25 EV**
- FINISH1M HIGHLIGHTGRANDFATHER1A: **+1.50 EV**

The +1.50 result is produced because the already-bright q90 233/237 window fields
are ignored by the *incremental field* counters, but later q90 104/185 fields
begin clipping and still stop the search.

This is a narrow correction to highlight accounting, not a new exposure look.
Phone validation is still required on both the toy/window scene and the original
dog/window scene.
