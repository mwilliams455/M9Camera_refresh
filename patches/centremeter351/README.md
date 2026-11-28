# M9Cam 3.51 CENTREMETER — centre-weighted metering and steadier preview exposure

Parent: **3.50-amazesimd** (27350). Candidate: **3.51-centremeter** (27351). Test build. It
changes how the exposure adjusts, not colour or tone, and no native library changes.

## Why

The M9 profile took its reference exposure from the phone's own whole-frame auto-exposure.
The M9 placement logic then added +0.25 to +0.75 EV steps on top. A screen recording showed:
- a near 2-stop dive within 0.4 s as a bright window came into view, followed by a
  stepwise climb back by the M9 layer;
- quarter-stop ticks while the camera was almost still, as the placement target flipped
  between two neighbouring 0.25-EV steps.

The Leica M9 meters centre-weighted and does not keep re-adjusting while you hold still.

## Changes (switch: M9 settings → Capture → **Centre-weighted metering**, default on)

1. **Centre-weighted reference metering.** The M9 profile now uses PhotonCamera's existing
   centre-weighted AE regions: nested areas of 70%, 45% and 20% of the frame, weighted
   200/300/500, or one 60% area when the camera reports fewer than 3 AE regions. An
   explicitly chosen standard metering mode still wins. Monochrom is unchanged.
   - M9 tap-metering and AE lock now keep the same centre-weighted reference underneath,
     instead of switching it to whole-frame.
   - Still captures use the same regions as the preview.
2. **Steady gate on placement (`M9PlacementSteadyGate1A`).** When the placement controller
   proposes a single 0.25-EV move towards a target no more than one step away, that move is
   applied only after the same direction has been proposed continuously for 1 s. Flicker
   between neighbouring steps therefore never moves the exposure. These always apply at
   once, as before:
   - moves towards targets half a stop or more away;
   - highlight safety releases;
   - highlight recovery;
   - the first acquisition after start-up or a tap.

With the switch off, both changes are disabled and 3.50 behaviour returns.

## Expected differences

- Bright edges such as windows, lamps and sky no longer drag the whole preview down.
- A centred subject in front of a bright window is exposed for the subject, so the window
  may clip sooner, as on an M9. The existing highlight-retention limits still cap the
  M9 lift.
- Small framing changes no longer make the preview tick by a quarter stop.

## Diagnostics

- The render JSON has `centreMetering351`: the AE regions the still requested and the
  regions the camera reported back. The reported regions show whether the phone honours
  AE regions.
- The exposure-plan JSON has `steadyGateEnabled` and `steadyGate`, which records whether
  the last move was held, the reason, and the pending direction and time.

## Evidence

- `M9PlacementSteadyGateTest` (6 tests) covers:
  - a single step held until it lasts 1 s, both up and down;
  - neighbouring-step flicker never moving the exposure;
  - a direction change restarting the hold;
  - the controller's own wait keeping the timer while settling clears it;
  - large and exempt moves passing straight through.
- `M9CentreMeteringTest` (3 tests) covers:
  - centre-weighted as the M9 default;
  - explicit modes, Monochrom and the switch being off keeping their metering;
  - the setting defaulting on, and keeping the previous behaviour when no settings
    context exists, which preserves the existing placement tests.
- All changed Java files compile against 3.50 with no new errors.
- CI checks that every native library is section-identical to a 3.50 rebuild at the same
  path.
