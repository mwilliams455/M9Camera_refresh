# M9PRIMARYEXPORT1B — fresh PRIMARY first

Parent: **1.84 / M9PRIMARYEXPORT1A + NOISECANCEL1A**.

Phone validation of 1.84 proved that PRIMARY generation was working: the current
capture's PRIMARY was privately staged with role `primary_timing`, but the burst
still showed **88 PRIMARY entries pending** and **771 recovered diagnostics**.

PRIMARYEXPORT1A separated PRIMARY from shutter-trace traffic, but recovered
PRIMARYs and newly captured PRIMARYs still shared one single-thread exporter.
A stale or slow recovered destination could therefore head-of-line block the
current capture.

## 1B policy

- fresh/current-session PRIMARY: dedicated `M9DiagPrimaryFreshIO` worker,
  eligible after **100 ms**;
- recovered/previous-session PRIMARY: separate
  `M9DiagPrimaryBackfillIO` worker, eligible from **1000 ms** onward;
- ordinary diagnostics remain on the existing 12-second exporter;
- both PRIMARY paths still stream from the durable private stage;
- export failure keeps the private payload and manifest for retry;
- restart recovery remains metadata-only and does not load payloads into heap.

This makes current PRIMARY delivery independent of the historical backlog.

## Frozen photography

No renderer, RAW, JPEG, DNG, Auto exposure, TC20, tone, colour, tungsten,
sharpness, preview, or NOISECANCEL1A logic changes.

Version: **1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1**.
