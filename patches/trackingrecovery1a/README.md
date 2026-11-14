# M9Cam 3.14 TRACKINGRECOVERY1A

Parent: signed 3.13 TRACKINGDEFAULT1A candidate, APK SHA-256
`167393ccfdc25c5d0c232a6012b213b8e5cf1b094ee1a35e540c75faf2e7623c`.
3.13 is still a candidate; the accepted main baseline remains 3.12.

## Reproduced defects

These are production-policy reproductions with synthetic detector observations,
not diagnoses of a phone recording or evidence of measured optical improvement.
The earlier recorded person switches were intentional user taps.

With **Persistent subject identity (experimental)** enabled:

1. After loss, one matching observation, another missing/ambiguous/rejected
   observation, and one later match incorrectly count as two consecutive
   recovery confirmations. The old counter survives the interruption.
2. A fresh matching observation can bypass the existing 1,150 ms recovery
   deadline because that deadline was checked only when a match was missing.
   The worker result can be accepted before the UI timeout retires the target.

The regression sequence produces 12 failed assertions in 67 checks on the
unchanged 3.13 policy. All 67 pass with this correction; the inherited 34
semantic-anchor, 20 identity and 13 appearance checks also pass locally.

## Correction

Every missing, ambiguous, rejected, stale or invalid-time observation clears the
partial identity-recovery run. Two new coherent fresh observations are needed.
The original hold deadline is enforced before accepting a recovery result;
late results cannot revive an expired selection. A new tap can select again.
Duplicate/older frames never add confirmations, and old-session observations
cannot affect the current session. The inclusive deadline boundary is retained.

Only `SubjectAnchorPolicy.java` and app version metadata change in assembled
production source. Historical overlays remain intact. Identity OFF retains the
existing behaviour. Default settings, predictive AF, ordinary patch tracking,
human/animal Eye AF, Camera2 requests, target presentation, rendering and assets
are unchanged. No additional models or inference work are introduced.

## Validation and phone check

The dedicated workflow reconstructs and verifies 3.13 first, applies this narrow
patch, runs candidate recovery/identity/anchor tests and inherited Android focus,
lifecycle, tap, shutter and profile regressions, and packages against the exact
signed 3.13 parent. It verifies certificate, 16 KiB alignment and unchanged 37
native libraries and 301 assets. Build results are recorded separately.

Install the candidate over the existing app without clearing settings. In
**Wide / Continuous Picture AF**, enable **Focus tracking**, **Subject-aware
tracking**, and **Persistent subject identity (experimental)** under Capture
settings. Test with predictive AF OFF first to isolate recovery. Tap one person
with a distinctively coloured top, briefly obscure them, then let them reappear.
The indicator should hold while uncertain and recover only after consistent
observations; after a longer loss, retap. Include actual saved photos to assess
focus. Repeat one ordinary capture with identity OFF and in Monochrome.

Retain as an unmerged candidate until phone feedback. No optical accuracy or
general subject re-identification claim follows from host or Android tests.
