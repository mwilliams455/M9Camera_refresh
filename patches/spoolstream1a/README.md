# M9SPOOLSTREAM1A

Root-cause repair for the repeatable ~6 second no-shutter crash.

Fresh all-buffer logcat from 1.74 proves:
- the process identifies as 1.74 M9PREVIEWHEAP1A;
- Java heap reaches the 512 MB growth limit within seconds;
- final Camera2/binder allocations fail at only 16-88 bytes;
- the previous root-cause collector reduction therefore was insufficient.

Source audit found that M9DiagnosticBurstSpool restart recovery materialized every
persisted `.stage` payload with `Files.readAllBytes()`, retained those payload
byte arrays in pending maps, then three seconds later duplicated the data again
while building one nested JSON burst bundle. Old large diagnostic stages survive
app updates, so this can refill the heap even when the current session has not
taken a photograph.

M9SPOOLSTREAM1A changes diagnostic transport only:
- recovered entries retain path + size metadata, never payload byte arrays;
- newly staged caller byte arrays are written immediately and not retained;
- the 3-second burst is a small manifest only;
- complete individual sidecars are streamed with a 64 KiB buffer after the
  existing compatibility delay;
- old private staged diagnostics remain intact until their individual stream
  export succeeds.

Frozen:
Auto Exposure 1B, JPEG/DNG/native renderer, controlled OES preview transform,
preview shader, Auto meter, neutral-reference TC20, shutter draw lock, and all
capture-request photographic behavior.

First device validation should be an idle viewfinder for >30 seconds before any
capture. If it survives, pan for another minute, then take one photograph.
