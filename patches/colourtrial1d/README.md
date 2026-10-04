# COLOURTRIAL1D — render memory and crash evidence

Based on the released COLOURTRIAL1C. Version 1.66-m9colourtrial1d-tg1, code 26686.

The reported phone crashes do not yet have a fatal stack or confirmed OS exit reason.
This is a memory-pressure repair and diagnostic build, not a claim that all crashes
have been reproduced or resolved.

Changes:
- Keep the pinned AMaZE algorithm and global 128px tile grid. Allocate RGB float
  destinations for 256 rows at a time. Read the original full input/halos. Preserve
  the original RAW no-Sharp MHC 16px physical border. Release corrected RAW once
  the AMaZE input has been populated.
- Prepare the selected quarter-strength pre-SAT chroma correction in the existing
  camera buffer, after the final camera-domain audit/meter read. Retain two rows
  of uncorrected transformed halo. A borrowed JNI buffer remains valid until the
  owning OpenCV Mat is explicitly released after all synchronous render calls.
- Reject dimensions below 64 rather than allowing unsafe upstream border reads
  on tiny frames. This does not affect full-size phone rendering.
- Persist render-stage checkpoints with Java/native allocation statistics and a
  compact Android process state summary. Chain the original uncaught handler.
- On startup, collect up to eight Android process-exit records, including up to
  two bounded trace streams. Native tombstones are base64 protobuf, not text.
  Capture the previous checkpoint before a new render can overwrite it. Export
  the report after storage is ready into the existing diagnostic burst system,
  and include a compact report in the ordinary log. Reported RSS/PSS are Android
  samples, not exact memory at death. A checkpoint alone is not proof of a crash.

Photographic policy retained: complete pinned AMaZE, no final Sharp, quarter RAW
proposal, quarter pre-SAT chroma correction, same Auto highlight headroom, SAT2,
TG1, curve02, source/target matrices, HSM, JPEG quality/encoding and resolution.

Gates: 80 old/new camera comparisons across CFA, tile boundaries and 1/8 workers;
25 in-place Q14 comparisons including 12MP; real Java/JNI tests including 72
SAT/rotation/thread/Bitmap transports; ASAN/UBSAN; isolated 12MP before/after hash
and peak-RSS comparison. Host parity does not establish Android crash resolution.
Private device logs and photographic evidence are not part of this repository.

Android references:
- https://developer.android.com/reference/android/app/ApplicationExitInfo
- https://developer.android.com/reference/android/app/ActivityManager#setProcessStateSummary(byte[])
