# M9BACKLIGHTROLLBACK1A — FINISH1J control

This is a **diagnostic rollback build**, not a new final exposure policy.

The 26 September 09:28 dog/window capture proves the current 2.00 pipeline
successfully classified severe backlight and delivered the requested capture
energy, but the finished subject remained much darker than the live bracket
predicted.

For a clean A/B test this overlay restores the exact
`M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A` policy while preserving every
non-Auto component from the current 2.00 stack.

Removed only from the Auto policy:

- FINISH1K `BGQUAL1A`
- FINISH1K `HIGHLIGHTRET1A`
- FINISH1L `OPENANCHORBAL1A`

Preserved:

- BODYLOCKRELEASE1A and the 4x6 multi-field body architecture
- current renderer, TC20/TONEBOUND050, SAT2, curve02, TG1
- current colour and noise paths
- current DNG/JPEG ownership, crash fixes, spool reset and performance stack

On the supplied 09:28 diagnostics, FINISH1J would remove the 1.25 EV
HIGHLIGHTRET ceiling. The underlying body search itself requested 1.50 EV, so
this control should differ by only about +0.25 EV for an equivalent scene. That
is intentional: if the subject remains too dark, it proves the regression is
not primarily the new highlight-retention cap and we should fix the live
backlight/body prediction rather than simply keep rolling back.
