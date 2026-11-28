# M9Cam 3.52 SETTLEMETER — settle, then meter

Parent: **3.51-centremeter** (27351). Candidate: **3.52-settlemeter** (27352). Test build. It
changes when the preview exposure adjusts, not colour or tone, and no native library changes.

## Why

Screen recordings of 3.51 with centre-weighted metering on and off showed the same pattern.
While the phone panned past a bright area, the exposure dived 2.8–4.0 EV and then took
2.7–4.0 s to climb back in visible steps. Centre weighting did not change that.

| Recording | Steady frame-to-frame change | Steady jumps | Biggest dive | 80% recovery |
|---|---|---|---|---|
| 3.51 centre metering on | 0.018 EV | 5.9 per 10 s | 2.8 EV | 4.0 s |
| 3.51 centre metering off | 0.021 EV | 4.9 per 10 s | 4.0 EV | 2.7 s |

An M9 is metered when the photographer stops and holds the camera to the eye, not while it
swings around.

## Changes (switch: M9 settings → Capture → **Settle, then meter**, default on)

1. **Hold while moving (`M9MotionHold1A`).** The gyroscope's angular speed, smoothed over
   40 ms, decides when the camera is moving:
   - **moving:** above 12°/s for 50 ms;
   - **settled:** below 4°/s for 300 ms;
   - between those speeds the state does not change.

   While moving, the M9 layer holds the exposure that was on screen through the existing
   AE-lock projection: an automatic hold, not a user AE-L. The preview simulates the held
   exposure while the phone's own AE keeps measuring underneath.
   - A pan longer than 2.5 s releases for 350 ms so the exposure can follow a scene that
     has really changed.
   - There is no hold during manual exposure or ISO, M9 tap-metering, user AE-L or a
     bracket, or when gyroscope samples are missing or more than 200 ms old.
2. **Meter in one step on settle (`M9AutoExposure2D.settleAfterHold`).** When the hold
   ends, the next fresh metering sample goes straight to the placement target in one move
   instead of 0.25–0.75-EV slews. Highlight-safety limits still apply.
3. **Ease on screen (`M9DisplayEase1A`).** A change of 0.2 EV or more in the displayed
   exposure eases in over 300 ms, so the one-step move is a fade rather than a jump.
   - This applies only to the final viewfinder brightness, so metering probes and
     captured files are unaffected.
4. **Defaults.**
   - The 1-s steady gate from 3.51 for single quarter-stop moves now follows this switch.
   - Centre-weighted metering now defaults to **off**, because the recordings showed no
     benefit; it remains available.

With the switch off, metering is continuous as in 3.51 with centre metering off.

## Diagnostics

- The render JSON has `settleMeter352`, recorded at the shutter: whether the camera was
  moving, the hold reason, the gyroscope speed, the current and last hold durations, and the
  hold count.
- The exposure-plan JSON adds `settleMeterRevision`, `settleAcquirePending` and
  `settleAcquireApplied`.

## Evidence

- `M9MotionHoldTest` (6 tests) covers:
  - pan and settle;
  - tremor and single spikes not counting as moving;
  - the band between the two speeds;
  - the long-pan refresh;
  - not-allowed and stale gyroscope cases;
  - the diagnostics.
- `M9DisplayEaseTest` (5 tests) covers:
  - a step gliding from the old brightness to the new one;
  - small changes not being eased;
  - a new step midway starting from what is on screen;
  - the 4-stop limit;
  - the disabled and unknown-exposure cases.
- `M9SettleMeterTest` (2 tests): the switch defaults on and follows the stored value, and
  the shutter-time state is kept for the photo's diagnostics.
- `M9AeLockAutomaticTest` (4 tests) covers:
  - the automatic hold keeping the shown exposure without counting as AE-L;
  - pressing AE-L during a hold keeping that exposure as the user's lock;
  - the automatic hold never replacing or releasing a user AE-L;
  - control changes ending the hold, and a manual shutter time being refused.
- `M9AeLockTest` (8 existing tests) still passes and is now in the CI registry.
- All changed Java files compile against 3.51 with no new errors.
- CI checks that every native library is section-identical to a 3.51 rebuild at the same
  path.
