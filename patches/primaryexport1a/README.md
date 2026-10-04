# M9PRIMARYEXPORT1A — priority PRIMARY sidecar export

Parent: **1.83 / M9NOISECANCEL1A QUIETCHROMA**.

The high-ISO cat test initially looked like a missing
`*_M9_PRIMARY.json`. The burst manifest changes that diagnosis.

For the nearby 20:12 capture, the PRIMARY payload had already been successfully
**private-staged** with role `primary_timing`; it was about 409 KiB. At bundle
time the spool had **46 individual exports pending**, including multi-megabyte
shutter traces, and reported zero private-stage and zero individual-export
failures. The user-facing file could therefore appear to be missing even though
the PRIMARY had already been generated and durably staged.

M9SPOOLSTREAM1A currently puts every individual sidecar onto one delayed
single-thread exporter. A small PRIMARY can wait behind several multi-megabyte
shutter traces.

## PRIMARYEXPORT1A

Keep the existing private-first durability exactly as-is, but give the
`primary_timing` role its own bounded single-thread exporter:

- PRIMARY public-export delay: **250 ms**
- all other diagnostics: existing **12,000 ms**
- restart recovery also routes pending PRIMARY entries to the priority exporter
- files are still streamed from the private stage with the existing 64 KiB
  buffer
- public export failure still retains the private payload/manifest for retry

The burst remains a bounded manifest. PRIMARY bytes are not duplicated into the
bundle or held in Java heap.

## Frozen photography

No renderer, RAW, JPEG, DNG, Auto exposure, TC20, tone, colour, tungsten,
sharpness or NOISECANCEL1A logic changes.

Version: **1.84-m9primaryexport1a-noisecancel1a-tg1**.
