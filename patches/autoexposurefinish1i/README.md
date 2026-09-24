# AUTOEXPOSUREFINISH1I — FASTACQUIRE1B SAFE075

Parent: **1.81 / AUTOEXPOSUREFINISH1H FIELDOWNERSHIP1A FASTACQUIRE1A**.

1.81 closed the woodland classification dead zone and accelerated large,
confident exposure corrections to +0.50 EV per fresh rendered-meter sample.
Phone testing indicated that Auto could be made faster still, but only if the
additional speed did not create a new overexposure risk.

## SAFE075 policy

1I adds a third positive-acquisition tier:

- normal fine movement: **+0.25 EV**;
- fast acquisition: **+0.50 EV**;
- guarded severe acquisition: **+0.75 EV**.

The +0.75 EV tier is deliberately narrow. It is allowed only when:

- the rendered sample is no more than **250 ms old**;
- there is at least **1.25 EV** remaining between the held Auto value and the
  already-computed rendered target;
- **no protected open anchor** is present;
- and the scene is either:
  - profoundly whole-scene starved (median <=20, centre median <=30,
    centre Q25 <=14, dark fraction >=0.65), or
  - a very confident/severe coherent 4x6 backlit body
    (confidence >=0.50 and starvation severity >=0.75).

The step remains mathematically bounded by the same target and positive-headroom
limit used by 1.81:

    result = min(target, current + selected_step)

and the target itself is already clamped to the rendered positive safety limit.

This means SAFE075 cannot intentionally step beyond the exposure that the
existing bracket judged safe. The stricter sample-age and starvation
requirements are additional protection against a scene changing between meter
samples.

## Expected convergence

A genuinely severe +1.75 EV request can now converge approximately:

    0 -> +0.75 -> +1.25 -> +1.75

instead of:

    0 -> +0.50 -> +1.00 -> +1.50 -> +1.75

The second step deliberately falls back to +0.50 EV once less than 1.25 EV
remains. This is slower than two consecutive +0.75 EV jumps, but preserves a
larger safety margin against a scene change while still removing one acquisition
cycle.

Less severe scenes continue to use +0.50 or +0.25 EV steps.

## Preserved safeguards

1I does not change:

- the final whole-scene or backlight exposure targets;
- 1H FIELDOWNERSHIP1A;
- 1G protected-open-anchor thresholds or caps;
- body lock / target lock;
- highlight and headroom budgets;
- immediate hard-safety exposure release;
- slower two-confirmation downward hysteresis;
- TC20, tone curve, saturation, tungsten, detail or source calibration;
- JPEG/DNG/native rendering or preview shader.

Ordinary protected-anchor scenes therefore still cannot be accelerated past
their existing +0.25 EV total allowance, and severe protected-anchor scenes
remain bounded to +0.50 EV.

Version: **1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1**.
