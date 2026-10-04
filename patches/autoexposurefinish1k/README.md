# M9AUTOEXPOSUREFINISH1K — BGQUAL1A + HIGHLIGHTRET1A

This is a capture-exposure change only. It keeps the M9 renderer frozen.

## Why

The clean 26 September dark-bedding / bright-wall test proved that FINISH1J could
find a real coherent dark component yet grant the full +2.5 EV backlight range
without any absolute bright-background evidence. The result made the subject very
readable, but pushed the wall much closer to white and produced a long ~340 ms
capture at ISO 3200.

For that frame the current body diagnostic reported approximately:

- background Q90: 73
- background bright-field fraction: 0
- selected backlight request: +2.5 EV

That is strong *contrast* evidence, but weak evidence that the scene is genuinely
backlit by a bright source.

## BGQUAL1A

A qualified dark body may still receive up to +1.0 EV from starvation/contrast
alone. Authority above +1.0 EV is progressively unlocked by absolute evidence from
the neutral-reference meter:

- non-body background Q90
- non-body bright-field fraction
- outer near-white fraction
- outer clipping fraction

The score is quantised back onto the existing 0.25-EV search lattice.

For the 26 September regression frame, the score is zero, so the +2.5 EV request
would be capped at +1.0 EV. Genuine window/sky backlight can still unlock the
higher range.

## HIGHLIGHTRET1A

This is **not HDR**. There is no local tone map, local exposure mask, multi-frame
merge, shadow reconstruction, or post-capture relighting.

It is a second global capture-exposure ceiling. The bracket is scanned for
*new* highlight damage relative to the neutral-reference frame. Exposure stops
before two previously non-bright 4x6 fields become broadly near-white, before two
fields acquire substantial new clipping, or before comparable global highlight
growth becomes excessive.

Already-bright or already-clipped windows are grandfathered by measuring growth
from baseline. That preserves the existing ability to sacrifice some background
when the subject is genuinely backlit.

On the 26 September frame, this independent guard would stop at +2.25 EV because
the +2.5 EV bracket suddenly drives two fields above 55% near-white. BGQUAL1A is
the tighter constraint there, so +1.0 EV wins.

## Frozen

Renderer, PERF3I colour path, SAT2 M04/M05, curve02, TC20/TONEBOUND050, TG1,
sharpness/noise, DNG, spool reset, and performance paths are unchanged.
