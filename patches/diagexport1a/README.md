# M9Cam 2.93 DIAGEXPORT1A

Parent: merged 2.92 (`ed3aa5cd9971c2819ab52deb0e2b94d3bdc61f96`). Malcolm's 16 October diagnostic manifest recovered 3,203 old files referencing 139,299,120 bytes. The manifest export took 20.26 seconds. The supplied current capture saved JPEG and DNG successfully; its rendering took 3.61 seconds with no render queue wait. It is not a controlled JPEG-only performance baseline.

The active spool used Android's document provider first for every public file, including directory resolution and filename lookup. The existing legacy writer already tried the direct filesystem first, but the spool did not use it. Provider lookup is a plausible contributor; the supplied timings do not prove where the 20.26 seconds was spent.

This patch makes both spool manifests and individual diagnostic files try direct filesystem output first. Android scoped-storage rejection or any I/O failure falls back to the existing document-provider path. A partial direct write or close failure restarts the fallback from the beginning of the private source. Private files remain until a complete export succeeds. Large reports still stream in 64 KiB chunks.

Resume also added 250 ms to each successive ordinary recovered file's scheduled time. Roughly 3,000 ordinary reports therefore imposed over 12 minutes of scheduling delay even on fast storage. All recovered ordinary files now become eligible after the same existing 12-second startup delay; the existing single background worker performs them sequentially. Fresh PRIMARY and shutter-trace workers remain separate. Visibility, diagnostic preference, trace coalescing, recovery, and retry policy are retained. No backlog reset or new deletion policy is introduced.

New telemetry identifies successful direct/fallback writes, failures, cumulative opening/transfer durations, and last observed operation durations. Concurrent worker totals are not a capture latency breakdown. The file containing a snapshot is not yet counted as a successful export of itself.

Scope: `M9DiagnosticBurstSpool.java`, new pure-Java `M9DiagnosticPublicWriter1A.java`, and version metadata in `app/build.gradle`. All image rendering, exposure, capture, JPEG/DNG payload generation, native sources, assets, UI, and existing Android tests are byte-identical to 2.92. Packaging restores all 27 accepted native libraries and verifies all 285 assets against the signed 2.92 installer.

Host verification compiles the real production classes. It exercises a 3,203-file recovered backlog, fresh PRIMARY delivery, a 12 MB trace, replacement during a blocked fallback, retention/retry, lifecycle/preferences, scoped-storage rejection, partial writes, close failures, disabled fallback, exact bytes, and bounded stream chunks. Filesystem/executors are real; Android provider calls and JSON serialization are stubbed. This proves control flow and preservation, not phone speed.

Commands:

```
python3 patches/diagexport1a/assemble.py DEST --parent VERIFIED_292
python3 patches/diagexport1a/verify_source.py VERIFIED_292 DEST
python3 patches/diagexport1a/host_test.py DEST --output HOST_RESULTS
```

Phone acceptance: install over 2.92; keep diagnostics off until ready. Enable Save diagnostic files, leave Extended M9 colour diagnostics off, select JPEG-only, and take one M9 photo. Keep the app visible for about 30 seconds, then attach its PRIMARY JSON and newest burst manifest if available. Existing old exports may still appear while draining. Check `publicDirectWrites`/`publicSafFallbackWrites`, opening times, and pending counts before requesting a larger performance run. No claim of a phone speed improvement is made until tested.
