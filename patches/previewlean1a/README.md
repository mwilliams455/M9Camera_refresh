# M9PREVIEWLEAN1A

Isolation build after 1.74 still failed at approximately six seconds.

The uploaded app log did not contain the new 1.74 session, so this branch does
not claim a new crash stack. Instead it removes legacy diagnostic retention that
is not required for normal M9 Modern operation.

Normal M9 Modern now disables:
- the 30-second per-frame root-cause Camera2 metadata recorder;
- the 64x64 x 9 shutter-trace preview pixel history;
- retention of complete reported Camera2 tone-curve arrays inside each live
  M9GpuPreview2A.Frame. Point counts and the existing diagnostic key remain.

These are diagnostic-only removals. The actual controlled Camera2 tone curve is
still read and inverted to build the live inverse texture; only its later retained
copy for diagnostics is removed.

Frozen:
- AUTOEXPOSUREFINISH1B policy and all thresholds;
- neutral-reference TC20 prediction and smoothing;
- the live shader and exposure simulation;
- shutter-to-last-GL-drawn-plan authority;
- JPEG/DNG/native rendering and colour;
- Auto GPU meter and paired/TC20 evidence needed by the live exposure pipeline.

Purpose: determine whether the six-second failure originates from legacy
diagnostic retention or from the core live preview path. Device validation is
required. A fresh all-buffer logcat from this exact version remains the preferred
evidence if it still fails.
