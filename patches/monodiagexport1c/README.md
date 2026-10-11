# 2.81 MONODIAGEXPORT1C

Parent: 2.80 at `857bcc587d085b5b050ad77facf120cbc4419c5b`. Draft diagnostic-delivery correction. The recurring Monochrom shutter rejection remains unresolved; this candidate does not change exposure policy.

Malcolm confirms the rejection record requested after 2.80 is not present. The two uploaded successful-photo diagnostics use `DCIM/PhotonCamera/Raw`; they contain valid exposure pairs but cannot identify a refused shutter. Source inspection found that 2.80 targets `DCIM/Camera` instead, uses the delayed general exporter, and can discard the entire record if an optional Camera2 metadata getter throws. These are reproducible delivery weaknesses, not a proven account of the phone's missing file.

This correction:

- Sends one record per terminal rejection to the established Raw diagnostics folder through the existing priority exporter.
- Recovers private 2.80 readiness records into that folder, preserving filenames and payloads. Other diagnostic roles retain their destinations.
- Records the non-ordinary rejection path too. Metadata, mode or characteristics failures retain the basic rejection record.
- Keeps one immutable, small record in the controller and embeds it in the next successful photo's existing LIVEPAIR/PRIMARY diagnostics. Attachment requires the same camera and session and an age of at most 120 seconds.
- Adds the observed reason code to the warning when diagnostics are enabled, so reporting does not depend on finding a file. Disabled diagnostics retain the original warning and create no record.

No per-frame/retry export or extra image buffer is introduced. M9 capture, metadata freshness, exposure allocation, the one-second readiness budget, rendering and save queues are unchanged. Accepted startup focus placement and blocked SL-series tracking remain unchanged.

## Verification

Exact reconstruction and reverse-patch verification pass: six scoped files change, including version and three test files; 1,353 scoped files are unchanged. Android build and all 104 focused tests pass (zero failures, errors or skips). CI run 38146778173 built source commit `0aaeb1efd2a3c564458e261807c586fe131200e8`; see CI_VERIFICATION.json. The eight new regression cases cover the added failure/export/fallback paths.

Signed-package verification passes for version 2.81 / code 27281, the accepted certificate and 16 KiB alignment. All 27 native libraries and 285 assets are byte-identical to 2.80. Installer SHA-256: `41fc2d8b2c8fc239e39e3f7f2b23f824957a44c4a09910383184eca7071fbf69`. See PACKAGED_VERIFICATION.json. [Draft PR #99](https://github.com/mwilliams455/M9Camera_refresh/pull/99) is not merged.

Focused tests cover real private spool persistence, failed old-folder delivery, recovery into the permitted folder, unrelated-role preservation, diagnostics-off, metadata getter exceptions, storage exceptions, once-only cleanup, bounded attachment, and successful-photo diagnostic association. These tests do not identify the original phone rejection trigger.

## Phone evidence

Install the candidate over 2.80 and reopen the app with Monochrom diagnostics enabled. Any retained 2.80 rejection record can now recover to `DCIM/PhotonCamera/Raw`. If the warning recurs, report the bracketed reason code or send the new readiness file / next successful photo's PRIMARY diagnostic. A successful photo must be within two minutes in the same camera session for the embedded fallback. Screen recording is not required.
