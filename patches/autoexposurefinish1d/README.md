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

The soft guard is now background-aware. Central highlight pressure has no
authority while the body is still deeply starved. It only starts participating
once the rendered centre reaches at least median 58 and Q25 28.

After that point it limits *additional* central clipping/near-white growth rather
than assuming an already-clipped central window belongs to the subject. An
independent "too open" condition (centre median >=100 and Q25 >=42 plus meaningful
highlight pressure) prevents scene normalization. Full-frame clipping still has a
30% absolute ceiling.

A severe backlit scene can therefore still gain exposure behind a blown window,
while an already-open subject is stopped before the M9 contrast character washes out.

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
