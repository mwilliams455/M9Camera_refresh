# M9Cam 2.94 DIAGSAF1B

Parent: unmerged 2.93, commit `71fb49531667d98be22a9b6ce164a34bdf0046de` (PR112). This is a stacked diagnostic export follow-up; neither change is phone-accepted yet.

The 09:03:23 phone report saved JPEG-only successfully. Rendering took 4.003 seconds and render queue wait was 2 ms. Direct diagnostic output failed six times; three completed SAF writes accumulated 16.724 seconds opening and 20.3 ms transferring. The last opening was 2.732 seconds versus 0.434 ms transferring. There were 3,234 pending individual reports at this early snapshot. Totals span concurrent workers and are not shutter latency. The attached PRIMARY report's own export is not included. The earlier 20.26-second manifest and this capture are not a controlled speed comparison. The photograph has no obvious gross corruption at the supplied display size; no matched quality comparison is available.

The existing `DocumentFile.findFile` path lists the children and queries their names separately. It also resolves the parent and deletes/recreates existing files on every open. This patch routes **only diagnostic spool output** through `DiagnosticSafWriter1B`:

- One child query requests document ID, display name and MIME type together. It still scans rows; it does not claim constant work regardless of folder size.
- At most four granted parent handles are cached. Filename results are never cached. Provider IDs remain opaque and are used with the granted tree URI; no vendor or document-ID format is assumed.
- Existing diagnostic files open with explicit `wt` truncation. Missing files are created. There is no delete or directory cleanup operation.
- Missing grants, null/incomplete cursors, missing columns, provider exceptions and failed opens invalidate the cached parent and fail the attempt. Existing spool retention/retry then resolves the grant again. This deliberately avoids treating an unavailable listing as an empty directory.
- Per-phase resolution, lookup, creation and opening metrics are recorded under `diagnosticSidecarSpool.publicSafDetails`. Counts describe opener attempts, not fully written files. Last phase timings can come from different concurrent operations. Existing public-writer completion/transfer metrics remain available.

The direct-first transport, private spool preservation, lifecycle/preferences, separate fresh PRIMARY and trace workers, and recovery scheduling from 2.93 are retained. The general storage helper methods used for other output are unchanged. No image renderer, exposure, camera capture, JPEG/DNG generation, native source, asset or UI changes are made. Parent directory handles are process-local and clear on initialization or an opening failure; an externally moved directory whose handle remains valid may continue to be addressed until invalidation/reinitialization.

Production scope is four files: app version metadata, the spool's diagnostic opener/telemetry wiring, diagnostic initialization/access methods in SimpleStorageHelper, and the new helper. Exact reconstruction and reverse restoration are verified. Packaging preserves the 27 accepted native libraries and 285 assets from signed 2.92 (also byte-identical in 2.93).

Verification:

```
python patches/diagsaf1b/assemble.py DEST --parent VERIFIED_293
python patches/diagsaf1b/verify_source.py VERIFIED_293 DEST
python patches/diagsaf1b/saf_host_test.py DEST --output PROVIDER_RESULTS
python patches/diagsaf1b/host_test.py DEST --output SPOOL_RESULTS
```

The new provider harness compiles the actual production helper and checks a 3,203-entry directory, opaque IDs, exact shortening, fresh lookup after deletion, bounded parent caching, outside-root rejection, seven provider failure modes, retry and directory collisions. The existing real-files/executors spool harness checks recovery, replacement, exact bytes and preservation. Android provider behavior is simulated in both host harnesses. Android compilation, existing regression suites and full-source CodeQL run separately in CI. No phone speed claim follows from these tests.

Phone acceptance: install over 2.93; enable Save diagnostic files, Extended M9 colour diagnostics off, JPEG-only. Take one photo, keep the app visible for about 30 seconds, and send its PRIMARY JSON (plus newest burst manifest if convenient). Inspect `publicSafDetails.revision`, phase timings, public successful write counts and pending reports. Do not clear app data or discard the backlog to make the measurement look better. Rendering performance profiling resumes after export is verified.

API/source references:
- https://developer.android.com/reference/androidx/documentfile/provider/DocumentFile (overhead and opaque IDs)
- https://developer.android.com/reference/android/provider/DocumentsContract (projected child queries and tree-scoped URIs)
- https://developer.android.com/reference/android/content/ContentResolver (output modes)
- https://android.googlesource.com/platform/frameworks/support/+/8b97716/v4/java/android/support/v4/provider/DocumentFile.java (findFile traversal)
