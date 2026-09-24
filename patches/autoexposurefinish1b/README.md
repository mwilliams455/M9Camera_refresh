# AUTOEXPOSUREFINISH1B — target-based M9-like scene placement

This child applies only after the released AUTOEXPOSUREFINISH1A assembly. It changes
only the rendered Auto policy and build identity. Reconstruction, colour transforms,
SAT2, curve02, BT.601 4:2:2, TG1, TC20, JPEG/DNG writing, resolution, viewfinder
shader and the 1E stability work remain unchanged.

## Why 1B exists

A fixed +0.5 EV backlight assist is not sufficient. The photographic question is
not "is this a backlit scene?" alone, but "how far below a deliberately low-key
M9-like placement is the subject or scene?"

1A also retained the ordinary processed-preview highlight veto for every positive
step. In severe backlight this can identify a dark subject correctly and then
forbid any useful correction because the bright window/sky is already near clipping.

## Target-based amount

The GPU meter now simulates nine neutral-reference gains from 0 through +2.0 EV in
0.25-EV steps. The search ceiling is a safety/diagnostic bound, not a prescribed
boost.

Whole-scene darkness keeps the existing qualifying shape (base median below 40 and
dark fraction at least 55%) and chooses the first safe simulated step reaching a
weighted rendered median of 60. Code 60 is intentionally low-key and is not
middle-grey normalization.

Backlit-subject placement measures both centre median and centre lower quartile.
The lower quartile prevents bright grass/sky inside the central rectangle from
hiding a dark foreground body. The first safe step is chosen that reaches centre
median 60 and centre Q25 30. A hard centre-median ceiling of 72 stops the search
from chasing an intrinsically black object indefinitely.

Older diagnostic research independently treated centre values around 54–62 as the
range where subject-body adequacy becomes strong. 1B therefore uses 60 as a
conservative rendered visibility target rather than inventing a bright smartphone
mid-grey target.

## Highlight trade-off

Ordinary scenes retain the exact 1A strict budget: no more than +1.5 percentage
points new processed clipping or +4 percentage points new >=224 bright pixels.

High-confidence backlight or severe whole-frame darkness uses a separate bounded
loss budget. The allowance grows only with evidence that the centre/scene is
collapsed. It is still capped by both incremental and absolute processed clipping
and bright-population limits. This deliberately allows some background window/sky
loss where necessary to expose the subject; it does not reconstruct those
highlights, use HDR, or apply a local lift.

Backlight geometry now also records the fraction of the surround at luma >=160.
This catches blue sky and other materially bright backgrounds before they become
near-white.

## Temporal and ownership behavior

Positive exposure still rises by no more than +0.25 EV per fresh meter sample and
cannot ratchet on a reused sample. Reduction remains immediate. User EV holds the
displayed Auto baseline; manual ISO/shutter disable automatic scene placement;
tripod/other ineligible states remain excluded by the 1A eligibility join.

Diagnostics explicitly report when the scene or subject target is still unmet at
the +2.0 EV search boundary. That evidence determines whether a later build needs a
wider search instead of assuming +2 EV is universally sufficient.

## Host evidence

The candidate test compiles the exact production policy and currently exercises 41
assertions. Synthetic cases include:

- ordinary-scene strict highlight behavior;
- missing/stale/foreign samples and manual/EV ownership;
- dark scenes selecting +1.25 EV and using the full +2.0 EV search when necessary;
- severe darkness allowing bounded lamp/specular loss;
- backlight selecting +1.25 EV despite the ordinary strict guard rejecting step 1;
- severe backlight requesting at least +1.5 EV;
- lower-quartile subject protection, 160-code bright-surround detection and hard
  centre ceiling;
- catastrophic background loss still stopping the search;
- exact centre median/Q25 and surround meter geometry.

Phone validation remains the photographic acceptance gate.
