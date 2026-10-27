# M9Cam 3.08 AFTRACKING4A — opt-in bounded AF region prediction

Parent: signed user-accepted M9Cam 3.07 AFTRACKING3B (SHA-256 `cc7f73e416e4292fdd56b8f62b14e198509a9fac5f1da869b006aafa4b00ce30`). Do not merge main until user device acceptance. Both M9 and Monochrome share the existing tracker and new control.

## Improvements

- **Tracking switch dependency corrected:** Turning ON Subject-aware tracking or Predictive AF-C automatically turns ON Focus tracking. Turning OFF Focus tracking explicitly disables its dependent modes. Loading existing 3.07 settings no longer discards enabled dependent modes; camera startup also repairs old subject-aware-ON/parent-OFF configurations. Settings show accurate switch positions.
- **Opt-in predictive Camera2 AF region, OFF by default:** The existing `FocusTrackingController` still uses the same recognized person/cat/dog subject or 3.06 arbitrary-patch tracker; overlay stays on the last measured target position. The separately tracked Camera2 AF-region centre may lead the observed 2-D trajectory by up to **140 ms**, bounded to **4.5% of the viewfinder per axis**. It never commands lens distance, triggers an AF scan, changes AE/AWB, or predicts scene depth.
- The predictor rejects old (>480 ms), duplicated, reversed, invalid, discontinuous or abnormal-velocity observations; changes from patch to subject reset motion history. Entering `HOLD` or `PENDING` immediately clears the velocity. New taps, lens/session changes, loss and screen transitions reset the prediction epoch. The inherited 3.05 Camera2 AF update gate still controls request frequency.
- The new preference is behind **Settings → Capture → Predictive AF-C (experimental)**; disabling it preserves the accepted 3.07 AF-coordinate path exactly. No new models or native libraries. Existing colour, RAW/DNG/JPEG, exposure, WB, M9/Mono rendering, human-eye/pet AF, and 3.07 identity tracker remain unchanged.

## Validation

- Pure-Java host assertions cover low-level motion, stationary jitter, rapidly moving targets, sudden false matches, hold/resume, source switches, stale/duplicate/incorrect epoch, frame cadence, normalized bounds, and switch dependency truth table.
- Android CI compiles both profiles; runs inherited human/animal/patch/AF lifecycle and shutter tests; separately signs APK using exact signed 3.07 and verifies all 37 inherited native libraries and 301 assets byte-for-byte.
- **Phone gate:** Test first with predictive OFF and Subject-aware ON to verify inherited 3.07. Then predictive ON and move one chosen person sideways and toward/away, pause then resume, briefly occlude, retap, switch lenses/M9-Mono, and take in-motion still photographs. Confirm tracking box stays at measured position, AF reported focus transitions remain plausible and captured detail is sharp. Do not mistake a tracking box or Camera2 focused state for optical sharpness.

**Limitations:** 2-D motion lead is only an AF-region timing heuristic, not depth, phase detect, subject reidentification, firmware Hasselblad AF-T code, or guaranteed predictive lens actuation. This does not address person-ID swaps in a crowd or independent autofocus HAL failures.
