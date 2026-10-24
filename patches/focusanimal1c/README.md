# FOCUSANIMAL1C — pet-preview sampling recovery (3.01)

## Captured phone evidence (24 October 2026)

The supplied 14.0-second screen recording `61806.mp4` shows the user's cat clearly visible in the M9/Motion 1×/24mm viewfinder, AF-C LOCK/SCAN, but never an acquired Cat AF box. The new **experimental status badge gives definitive upstream failure evidence**: `Pet AF: preview allocation failed`, observed multiple times. On first startup `Pet AF: scanning` appears briefly and then the error persists.

**This rules out low cat/dog classifier confidence as the observed immediate failure.** The 3.00 code publishes that single error string only when a `RuntimeException` or `OutOfMemoryError` is thrown inside its bitmap allocation / `PixelCopy.request` try block. The handler then sets `unsupported=true` for the session. It never retries unless the camera/lens/profile generation resets. The recording alone cannot distinguish the exception type nor whether the throw was specifically bitmap creation or PixelCopy submission, because 3.00 grouped them in one catch and did not log the exception.

## Correction

1. **Keep existing human-eye AF and M9/Mono imaging unchanged.** New branch is stacked on exact 3.00 Pet AF source; models, native libs, all assets and signed app certificate are unchanged.
2. Split the broad error handler into three cases:
   - `Bitmap.createBitmap` transient `RuntimeException`: report `Pet AF: bitmap <type> retry <ms>`; retry after bounded backoff.
   - Synchronous `PixelCopy.request` failure or asynchronous PixelCopy error: report `copy_request` / `copy_callback` stage and exact exception class / Android result code. Retry after bounded backoff, without poisoning the whole AF session.
   - Genuine `OutOfMemoryError` creating the bitmap: stop optional Pet AF for that camera session and show an explicit memory error (do not retry OOM).
3. `PetPreviewRetryPolicy` begins at 250 ms, then 500, 1000, capped at 2000 ms. A successful copied frame clears the error streak. Session changes reset the policy.
4. Continue enforcing single-flight Bitmap/worker/Camera2 ownership, session token, stale-position 900 ms AF-action gate, pet class whitelist and three coherent detections before automatic autofocus.
5. Do not alter MediaPipe detection thresholds again until a **real** preview frame reaches model inference and a genuine class/score result is visible.

## Verification

`PetPreviewRetryPolicyHostTest` checks initial sample readiness, transient failures at all retry intervals, repeated errors without permanent latching, clearing on success and reset on lens/session change. The inherited cat/dog policy, model latency and human-eye admission checks still run, followed by Android autofocus/capture tests and signed APK packaging. The installer must match the 3.00 signing certificate and retain all 31 parent native libraries and 300 original assets byte-for-byte.

## Phone test for 3.01

Install directly over 3.00 without clearing settings. Keep **Cat / Dog AF** enabled and AF-C. Reproduce the same cat scene in Motion and Photo. A transient `copy_request` error may occur briefly but should retry and proceed to model output; if `Pet AF: copy_request IllegalArgumentException retry 2000ms` persists, the remaining problem is invalid/supplier-specific PixelCopy request geometry and the exact exception class and stage are now known. If the badge reaches `boxes=...`, the detector is functioning and subsequent class scores / temporal confirmation identify the next blocker.

No optical pet AF accuracy claim is made until on-device verification. Keep draft PR, unmerged.
