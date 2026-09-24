# AUTOEXPOSUREFINISH1D — M9 character highlight guard + live-target hysteresis

Child of the stable 1.76 adaptive-backlight build.

The uploaded first phone examples showed two things:
1. adaptive backlight exposure works, but a few frames open far enough to lose the
   dense M9 character;
2. near an Auto threshold the viewfinder can appear to toggle EV back and forth.

This patch changes only M9AutoExposure2D.

## Modest M9 highlight guard

The existing 1C catastrophic backlight caps remain. 1D adds a tighter *soft*
character ceiling before them.

It primarily watches the central region because the subject often occupies it,
while the bright window/sky is deliberately allowed to clip in the surround.

The soft ceiling is severity-aware but bounded approximately to:
- central channel clipping: 7.5%–12%;
- central near-white luma: 20%–28%;
- full-frame channel clipping: 30% absolute ceiling.

A severe backlit scene can still reach around +2 EV if its central highlights
remain dense. The guard therefore does not recreate the old +0.5 EV problem.

## Viewfinder target stability

Backlight classification now has hysteresis:
- engage at confidence >= 0.22;
- remain engaged until confidence <= 0.12.

When a lower Auto target appears but the current exposure is still highlight-safe,
one sample is held and a second fresh confirming sample is required before
stepping down 0.25 EV. This prevents a borderline scene from bouncing between
neighbouring exposure steps.

Highlight/headroom safety is different: if the current EV exceeds the newly safe
limit, release is still immediate.

## Frozen

- 1C adaptive backlight target ranges;
- whole-dark / accepted-night scene-key policy;
- ordinary-scene strict highlight behavior;
- user EV and manual ISO/shutter ownership;
- JPEG/DNG/native renderer and colour;
- WYSIWYG shader and neutral-reference TC20;
- shutter draw-lock;
- 1.75 streaming-spool crash repair.

This remains global capture exposure only: no HDR, local shadows, local relighting
or JPEG-side exposure compensation.
