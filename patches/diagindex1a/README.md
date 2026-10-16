# M9Cam 2.95 DIAGINDEX1A

Parent: 2.94 commit `967529317fcad47750aedeb4f96b18e9f5904c97` (unmerged PR113, stacked on PR112). No diagnostic export candidate has phone acceptance yet.

## Phone evidence

The supplied 10:50:32 PRIMARY report confirms that 2.94's single-query route was active and JPEG-only saved successfully. There were 20 completed SAF exports, no recorded SAF failures, and 3,217 pending individual reports. The directory lookup counters recorded 283,566 rows visited across 22 queries, 86.918 seconds cumulative lookup time and a last lookup of 6.999 seconds. Last parent resolution was 0.006 ms, creation 13.174 ms and stream opening 1.650 ms. The last completed public opener was 4.080 seconds, with 3.883 ms transferring. Per-phase last values may refer to different concurrent attempts; cumulative values are not capture latency or a per-file average. The report's own export is not included in its snapshot.

This locates the remaining bottleneck in repeated directory traversal. 2.94 reduced provider call count but still scanned the folder for each export. The rendered JPEG took 4.533 seconds with a 1 ms queue wait; the changed indoor scene cannot establish a rendering-performance regression against the previous outdoor photograph.

## Change

`DiagnosticSafWriter1B` now keeps a process-local directory index and advertises `M9DIAGINDEX1A_BOUNDED`. Each cold directory scan returns names/opaque IDs once. Subsequent newly created documents are added to the index. Exporters sharing a folder coalesce the cold scan under that folder's lock; no global cache lock is held across provider I/O. Output payload streaming remains outside the index lock.

Every existing cached document is queried individually to verify its exact name and ID before opening with `wt`. An external rename/deletion triggers at most one immediate index refresh, then the attempt fails safely if the directory keeps changing. Missing or incomplete provider cursors, revoked grants, failed opens and provider exceptions discard the cached directory; the existing private spool retains the payload for recovery/retry. Private payload cleanup still occurs only after complete export success.

A complete cached index can become stale if another process creates the same filename. The provider may then allocate a suffixed name. Newly created documents are individually checked before any payload is written. On a name mismatch, only that attempt's newly allocated, unwritten document is removed; the index is refreshed and the intended existing name is resolved. If this cleanup fails, the attempt fails and private data remains. Existing user files are not deleted, and no backlog purge is added.

The cache retains at most four directories. Each index is capped at 32,768 records and 4,194,304 combined filename/ID characters. These are metadata bounds, not a claimed exact Java-heap size; active evicted operations may briefly retain their own index. If a cap is reached, the index is marked incomplete: cache misses use an exact full-directory lookup, preserving correctness at the cost of speed. Counters expose overflows, fallbacks, entries and characters. Ambiguous duplicate names and directory collisions are rejected.

Capture snapshots read only counters and volatile cache sizes; they never wait for an index scan. New IndexWait and Validate timings distinguish cold-scan contention and per-document checks. `lastLookupMs` can retain the time of an old cold scan after later exports become fast; inspect lookup query counts versus completed writes and `publicLastSafOpenMs`, not that field alone.

Production scope is three files: the diagnostic helper, the spool's policy label, and version metadata. Existing Android tests are unchanged from 2.94, including its corrected storage mock. Rendering, exposure, capture, JPEG/DNG generation, general storage methods, native sources, assets and UI remain unchanged. Packaging preserves the accepted signed 2.92 native libraries and assets, also byte-identical in 2.93/2.94. Parent handle caching retains the 2.94 limitation that an externally moved directory with a still-valid handle may continue to be addressed until invalidation/reinitialization.

## Verification

```
python patches/diagindex1a/assemble.py DEST --parent VERIFIED_294
python patches/diagindex1a/verify_source.py VERIFIED_294 DEST
python patches/diagindex1a/saf_host_test.py DEST --output PROVIDER_RESULTS
python patches/diagindex1a/host_test.py DEST --output SPOOL_RESULTS
```

The real production helper is compiled against provider API doubles. A 20,000-file directory plus 3,229 queued exports uses one child-directory scan, followed by individual document validations. Checks also cover shortening, opaque IDs, external rename/deletion/create, empty collision cleanup and cleanup failure, duplicate names, directory collisions, missing grants, eight provider failure modes, bounded cache/character overflow, concurrent cold-scan coalescing and nonblocking snapshots. The 9,924 assertions include repeated per-operation cursor/mode checks; this is a control-flow test, not an Android performance benchmark.

The existing spool/transport host harness passes 3,458 assertions with real files/executors for preservation, retry, trace replacement, lifecycle/preferences, fresh report delivery, bounded streaming and large backlog recovery. Android provider calls remain stubbed. CI reconstructs the pinned chain, builds Android, runs the 269-test regression gate and full-source CodeQL, then packages and independently reopens the signed installer.

## Phone check

Install over 2.94 without clearing app data. With diagnostic saving enabled, Extended M9 colour diagnostics off and JPEG-only selected, keep the app visible for about 30 seconds, take a photo and leave it visible another 10 seconds. Send its PRIMARY JSON. Check the new revision, directory-query count relative to completed exports, cache overflows, per-document validation/opening times and pending reports. A cold scan may still take seconds once per directory; sustained export throughput must improve before acceptance. If most of the backlog remains, use the existing measurement to identify why rather than asking for repeated equivalent photos. Keep PR112, PR113 and this follow-up unmerged pending phone acceptance.

API references:
- https://developer.android.com/reference/android/provider/DocumentsContract
- https://developer.android.com/reference/android/content/ContentResolver
- https://android.googlesource.com/platform/frameworks/base/+/988b22c44f51/core/java/com/android/internal/content/FileSystemProvider.java (createDocument allocates a unique filename)
