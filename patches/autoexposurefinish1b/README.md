# AUTOEXPOSUREFINISH1B — target-based scene key and backlight placement

This child applies only after the released AUTOEXPOSUREFINISH1A assembly. It changes
only the rendered Auto policy and build identity. Reconstruction, colour transforms,
SAT2, curve02, BT.601 4:2:2, TG1, TC20, JPEG/DNG writing, resolution, viewfinder
shader and the 1E stability work remain unchanged.

## Why 1B exists

A fixed +0.5 EV backlight assist is not sufficient. The useful question is:

> How far below a deliberately low-key M9-like placement is the scene or subject?

The answer can be +0.5 EV in one composition and substantially more in another.
The rendered bracket therefore chooses the amount; the policy no longer treats
backlight as one fixed additive boost.

The second problem is that bright-window/sky scenes can need subject exposure even
when the ordinary highlight guard predicts additional clipping. A global-exposure
M9 compromise may legitimately sacrifice some background highlight detail. 1B
allows that only after strong backlight qualification and while protecting the
central subject from clipping.

## Low-key scene preservation

Dark is not automatically underexposed.

An intentionally low-key scene, including night photography, is left alone when
the central/body tones are already adequately placed even if the global histogram
remains dark. Whole-scene assistance therefore requires the global scene *and* its
central body to be starved.

This avoids the smartphone failure mode of converting night into a bright daytime-
looking exposure.

The low-key targets are visibility floors, not middle-grey normalization:

- whole-scene weighted median target: code 46;
- central-body target: code 54;
- central lower-quartile target: code 22.

These values deliberately preserve dense M9-like shadows.

## Backlit subject placement

The centre is described by both its median and lower quartile. The lower quartile
prevents bright sky, grass or a window inside the centre rectangle from hiding a
dark foreground body.

Backlight confidence also uses the 90th percentile of the surrounding region, so a
materially bright blue sky can qualify even when it is not near-white.

The backlit-body visibility target is:

- centre median: code 56;
- centre lower quartile: code 22.

The first safe simulated step reaching that target is selected. If the target is
not reached, the final safe simulated step is retained and the diagnostic records
that the search/headroom boundary was reached.

## Exposure search range

The neutral-reference rendered meter now searches 11 gains:

0, +0.25, +0.50, ... +2.50 EV

+2.5 EV is a search ceiling, not a default or preferred exposure. Ordinary scenes
will generally stop much earlier. The wider range exists so severe foreground
starvation can be measured instead of silently capped at +0.5 EV.

Positive rise remains limited to +0.25 EV per fresh meter sample and a reused sample
cannot ratchet exposure. Reduction is immediate.

## Highlight policy

Ordinary scenes retain the strict 1A processed-preview budget.

Genuinely starved whole scenes use a bounded low-key highlight allowance, so one
lamp or specular cannot prevent useful exposure of the entire scene.

Backlight uses a separate, wider background-loss rule. The central rectangle can
itself contain bright background behind the subject, so the policy protects it
from catastrophic clipping rather than treating every new bright central pixel as
subject clipping. Outer/background clipping can rise substantially more, while
absolute central, outer and full-frame limits remain bounded.

This intentionally permits some sky/window loss when the alternative is an
unreadably dark subject. It is still one global capture exposure. No HDR, local
relighting, highlight reconstruction or tone-map compensation is introduced.

## Ownership

User EV continues to hold the displayed Auto baseline. Manual ISO/shutter disable
automatic scene placement. Tripod and other ineligible states remain excluded via
the AUTOEXPOSUREFINISH1A eligibility join. Missing, stale or foreign rendered
evidence cannot justify new positive automatic exposure.

## Validation

The synthetic tests cover ordinary highlight behavior, missing/stale/foreign
samples, manual ownership, genuinely dark scenes requiring more than +0.5 EV,
extremely dark scenes reaching the +2.5 EV search boundary, low-key/night-like
scenes remaining neutral when the body is already adequately placed, moderate and
severe backlight selecting different amounts, substantial background sacrifice
with subject protection, destructive background loss, central clipping veto, and
the new centre-Q25 / outer-Q90 meter geometry.

Synthetic tests establish policy behavior only. Phone validation remains the
photographic acceptance gate.
