# AUTOEXPOSUREFINISH1F — multi-field body / target temporal lock

Child of the stable 1.78 multi-field body build.

1.78 improved the truck test substantially: the coherent subject/body came through
while the bright window was still allowed to blow and the lower foreground remained
dense. The remaining phone video showed a different problem: at fixed ISO 50 the
HUD moved approximately 1/50 -> 1/60 -> 1/71 -> 1/85. Those are near-exact
quarter-stop steps, matching the Auto policy cadence rather than random Camera2 AE.

The reason is that 1.78 latches only "backlight yes/no". It recalculates the winning
4x6 connected body on every neutral-reference sample. Small field-noise changes can
therefore move the body boundary, recompute the relative readability target, and
make the viewfinder walk through neighbouring 0.25-EV targets.

## 1F body lock

Once a 4x6 coherent body engages with confidence >=0.22, 1F freezes:

- the selected field mask;
- its initial readability target median;
- its initial readability target Q25;
- its initial starvation severity used by the M9 guard.

For following samples, that same mask is re-measured against the new neutral
reference. A newly proposed component that overlaps at least 50% of the current
body is treated as the same subject and does not replace the lock.

A disjoint component can replace the locked body only when:
- it is materially confident; and
- it persists for two fresh rendered-meter samples.

If the old body itself becomes implausible, it is not used for positive exposure
while reacquisition is pending. Two fresh misses are required before the lock is
released entirely. This provides inertia without carrying a stale subject across
a genuine scene change.

## Exposure / photographic policy unchanged

1F does not alter:
- the 1.78 4x6 body-selection geometry;
- relative body readability targets;
- M9-character body ceiling;
- background sacrifice / full-frame clipping limits;
- +0.25 EV positive slew;
- 1.77 lower-target two-sample hysteresis;
- whole-dark / accepted-night behavior;
- ordinary highlight policy;
- JPEG/DNG/native renderer or colour;
- WYSIWYG preview shader / neutral TC20;
- shutter draw-lock;
- 1.75 streaming-spool stability repair.

## Protected open-anchor guard

Phone portraits from 1.78 exposed a different generalization problem: a coherent
dark clothing/upholstery region can win the body search even when a separate,
textured midtone region is already well exposed.

1F therefore also protects a coherent already-open anchor. This is semantic-free:
no face/skin/AI recognition. It requires at least two connected fields with
inner-frame support, median roughly 90..215, Q25 >=55, useful tonal spread, and
low near-white/clipping fractions. The q90/bright/clip limits deliberately reject
windows and specular backgrounds.

When such an anchor exists, unrelated dark material is not promoted into an
exposure-deficient subject. The truck/window case remains eligible because the
window is too near-white/clipped to qualify as an open anchor.

The goal is both temporal and photographic: a static scene should stop
re-deciding what the subject is every meter sample, and Auto should not brighten
an already-good portrait merely because dark clothing occupies much of the frame.
