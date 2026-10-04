# AUTOEXPOSUREFINISH1G — SOFTANCHOR1A middle ground

Parent: **1.79 / AUTOEXPOSUREFINISH1F**.

The initial 1.79 body-lock build improved the difficult truck/window case but
could open portraits too far when coherent dark clothing or upholstery occupied a
large part of the 4x6 rendered meter.

The late 1.79 protected-open-anchor change solved that portrait failure by
hard-vetoing the coherent dark-body path whenever a separate, already-open,
textured midtone anchor was present. Phone testing then showed the opposite
failure: the portrait became much better, but the truck/window scene became too
conservative.

## 1G policy

1G keeps the 1F protected-open-anchor detector, but changes its authority.

A protected open anchor no longer invalidates the coherent dark-body candidate.
Instead it limits the amount of additional positive Auto placement:

- ordinary protected-anchor scene: **+0.25 EV maximum**;
- severe protected-anchor backlight: **+0.50 EV maximum**;
- no protected anchor: existing 1.79 / 1F body-placement behavior remains
  unchanged.

The severe branch is still semantic-free. It requires:

- a valid coherent dark body;
- body starvation severity >= 0.70;
- body/background Q90 contrast >= 100 code values; and
- strong bright-background evidence from the rendered neutral probe
  (outer near-white, outer clipping, or substantial full-frame near-white).

This is intentionally a middle ground rather than a new exposure model.

## Unchanged

1G does not alter:

- the 4x6 rendered multi-field topology;
- relative body readability targets;
- 1F body-mask / target temporal lock;
- 1.77 lower-target two-sample hysteresis;
- +0.25 EV positive slew cadence;
- M9-character highlight ceiling;
- background-sacrifice headroom logic;
- whole-dark and accepted-low-key behavior;
- JPEG/DNG/native rendering;
- colour, tungsten, detail, shading or tone;
- WYSIWYG preview shader / neutral TC20;
- shutter draw-lock;
- streaming diagnostic spool.

## Diagnostics

The Auto sidecar now records:

- `protectedOpenAnchorMask`;
- `protectedOpenAnchorFieldCount`;
- `protectedOpenAnchorPolicy = soft_positive_lift_cap`;
- `protectedOpenAnchorSevereBacklight`;
- `protectedOpenAnchorLiftCapEv`;
- `effectivePositiveLimitEv`.

The validation target is specifically the pair of observed failures:

1. keep the portrait denser than initial 1.79; and
2. recover some truck/window readability relative to the hard-guarded build
   without returning to the full initial-1.79 lift.

Version: **1.80-m9autoexposurefinish1g-softanchor1a-tg1**.
