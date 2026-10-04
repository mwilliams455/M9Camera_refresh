# M9PREVIEWSTABILITY1A

Child of the exact 1.72 M9PREVIEWTC20NEUTRAL1A assembly.

This is a preview/runtime stability patch, not a photographic change.

Changes:
- serialize the Auto GPU meter and paired/TC20 GPU evidence so both PBO/fence
  readbacks cannot be outstanding at once;
- retain the same 250 ms eligibility cadence, but give Auto evidence priority
  when both probes become due on the same frame;
- replace the TC20 weighted-median boxed Integer sort with one persistent
  per-thread 12-bit weighted histogram;
- guard the two M9 HUD exposure-pair call sites against CameraFragment teardown,
  closing the NullPointerException previously captured in device exit evidence.

Frozen:
- AUTOEXPOSUREFINISH1B policy and thresholds;
- JPEG/DNG/still renderer and native colour path;
- 1.72 neutral-reference TC20 behavior, -0.5..0 EV authority, 0.125 EV slew and
  0.04 EV deadband;
- shutter-to-last-GL-drawn-plan authority;
- preview shader/colour/tone implementation.

The currently reported 1.72 panning crash is not claimed reproduced by the
older uploaded exit files. Device validation remains required. The purpose of
this candidate is to remove two concrete live-preview stressors and a proven
HUD lifecycle crash while preserving photographic behavior.
