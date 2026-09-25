# M9PRIMARYRECOVERY1A

Parent: **1.83 / M9NOISECANCEL1A QUIETCHROMA**.

A high-ISO phone capture successfully produced its JPEG and DNG but no matching
`*_M9_PRIMARY.json`. A later capture produced PRIMARY normally, and the
diagnostic spool reported no individual-export failures. The current PRIMARY
writer freezes the complete timing JSON to immutable bytes, then performs one
asynchronous public SAF write. If that write fails, the exception is logged and
the bytes are discarded.

PRIMARYRECOVERY1A closes only that diagnostic persistence gap.

## Policy

The normal PRIMARY path is unchanged:

1. the final timing/renderer JSON is frozen to immutable UTF-8 bytes;
2. `M9PrimaryTimingIO` attempts the existing public SAF write;
3. on success, nothing else happens.

Only if scheduling the timing writer fails, or if that public persistence throws,
the exact already-frozen bytes are handed to the existing
`M9SPOOLSTREAM1A` durable private spool with role **`primary_timing`**.

The spool already provides:

- immediate private-file persistence;
- a durable manifest;
- restart recovery;
- eventual individual public export while the app is visible.

The fallback uses the same intended public path
`<capture stem>_M9_PRIMARY.json`. It does not retain RAW/image objects and does
not modify the frozen PRIMARY payload.

## Frozen photography

No photographic code changes. In particular this does not alter:

- 1.83 quiet-chroma noise cancellation;
- 1.82 Auto exposure;
- TC20/tone/colour/tungsten;
- detail/sharpness;
- JPEG or DNG pixels;
- preview or shutter behavior;
- render queue/DNG queue ownership.

Version: **1.84-m9primaryrecovery1a-noisecancel1a-tg1**.
