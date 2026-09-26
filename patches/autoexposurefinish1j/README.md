# M9AUTOEXPOSUREFINISH1J — BODYLOCKRELEASE1A

This overlay changes one Auto-exposure hysteresis rule on top of the validated
1.96 COLORPERFROLLBACK1A renderer.

## Problem

The 4x6 body lock intentionally preserves a coherent subject across small meter
noise and field-boundary movement. In FINISH1I, however, an old latched mask could
remain locally plausible even when the current full-frame body detector returned
no coherent body. That path reset the miss counter, so the old mask could persist
indefinitely and make exposure depend on scene history.

## Rule

- A current valid body candidate clears the absence counter.
- One fresh current-detector miss is tolerated and the old mask is held.
- A second consecutive fresh miss releases the body lock.
- Re-evaluating the same meter sample does not advance the counter.
- Existing two-sample hysteresis for switching to a disjoint body is unchanged.

The neutral-reference rendered meter remains the authority. No local exposure,
HDR, face detection, renderer, TC20, SAT2, curve02, BT.601, TG1, DNG or sharpness
change is introduced.

The device test should verify that leaving a genuine backlit subject for an
ordinary scene no longer leaves a positive body-lift request latched from the
previous composition, while a single noisy meter frame does not cause flicker.
