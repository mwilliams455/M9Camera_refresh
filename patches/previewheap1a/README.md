# M9PREVIEWHEAP1A

This is a diagnostic heap-safety repair on top of M9PREVIEWSTABILITY1A.

The live root-cause collector previously retained a complete JSON copy of all
three Camera2 tone-map curves for every preview capture result. That evidence
was useful during the earlier shutter-trace investigation, but it is too large
for a continuously running production viewfinder.

PREVIEWHEAP1A keeps the exact per-frame scalar metadata timeline and timestamp
join while changing only diagnostic context storage:

- full per-frame tone-map curve arrays are no longer copied or retained;
- CCM plus tone-curve point counts are retained as compact context;
- compact context is refreshed at 2 Hz and the immutable String is shared by
  intervening rows;
- if this optional diagnostic collector itself encounters OutOfMemoryError, it
  clears its retained history and returns rather than taking down the camera.

The 1800-row / 30-second scalar metadata window remains. Snapshot/range APIs
remain compatible with the shutter-trace collector. Output now explicitly
marks the full tone-curve payload as omitted.

Frozen by source-inventory verification:
Auto Exposure 1B, JPEG/DNG rendering, native colour/reconstruction, preview
shader, preview meter/evidence scheduling, neutral-reference TC20, shutter
draw-lock, and all capture-request logic.

This branch contains source and tests only; no private device logs or
photo-derived evidence are published.
