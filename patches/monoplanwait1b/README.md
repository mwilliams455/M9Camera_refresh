# 2.80 MONOPLANWAIT1B

Parent: 2.79 MONOSAVEPIPE1A at `1602744eb248f639de654d0432428d857e674770`. Draft correction; Android build and signed-package verification passed. Phone validation pending.

Recording 52650.mp4 shows Monochrom Motion mode reporting six photos saved at about 18.5 seconds, then “Exposure preview is not ready” at about 19.5 seconds. The processing backlog has cleared before that rejection. This establishes a recurring readiness failure, but does not identify which metadata/plan condition caused that phone event.

Two definite source defects are corrected:

- A colour-context reconstruction exception discarded otherwise valid physical sensor exposure metadata. The registry now retains the real physical result and its exact timestamps while disabling colour reconstruction for that frame. Missing physical results, non-neutral AE, invalid sensor exposure, camera identity and the 250 ms metadata freshness limit remain enforced. The exposure allocator and 1.5-second plan validity are unchanged.
- The final readiness timer rejected without selecting a plan once more. The existing selection now runs at the deadline; a valid plan proceeds, while an absent plan rejects against the same one-second budget. Session, handler, profile and submitted-capture ownership guards remain.

With Monochrom diagnostics enabled, a terminal pre-submission rejection stages one small `MONO_EXPOSURE_READINESS_*.json` through the existing diagnostic spool, even though no photograph was captured. It records metadata validity, selection reason, mode and timing without image data. There is no per-frame or per-retry export, and diagnostics-off does not produce files. Evidence failure cannot interrupt shutter cleanup.

## Verification

`verify_source.py` checks all scoped files and reverse restoration to 2.79. Five files change (including version and two test files); the remaining 1,353 scoped files are identical. M9 still capture, exposure allocation/store, renderers, save queues, native code and assets are unchanged.

Android CI run 38144765233 passed all 94 focused tests: 12 real-registry/allocator metadata tests, 23 shutter-readiness tests, 44 still-capture lifecycle cases, 9 RAW gain cases and 6 profile capture cases. There are zero failures, errors or skips; the empty AfContinuityTest suite contributes zero tests. Coverage includes colour exceptions, exact physical metadata, Motion and Photo, freshness boundaries, invalid/missing/foreign observations, final-deadline admission, once-only diagnostics, disabled diagnostics, diagnostic failure and next-shutter recovery. These tests do not prove the recording's precise trigger.

Signed-package verification passed with version 2.80 / code 27280, the accepted certificate and 16 KiB ZIP/native alignment. All 27 native libraries and 285 assets are byte-identical to 2.79. Installer SHA-256: `8bfbf236dad5ad93e8febe9c1a2abfe7aad01ed492fecb5488d2ede6bebc2b0a`. See CI_VERIFICATION.json and PACKAGED_VERIFICATION.json. [Draft PR #98](https://github.com/mwilliams455/M9Camera_refresh/pull/98) is not merged.

## Focused phone check

Repeat a short sequence of quick Monochrom Motion photographs, letting the save count finish. Check whether an accepted shutter still produces the exposure-preview warning. If it does and diagnostics are enabled, retain the matching `MONO_EXPOSURE_READINESS_*.json`; a successful photograph or simultaneous screen recording is not required for this record. The accepted 2.78 focus-placement check does not need repeating.
