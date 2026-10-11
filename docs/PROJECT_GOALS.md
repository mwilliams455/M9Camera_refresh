# M9 / Monochrom project goals

Updated 11 October 2026 following Malcolm's direction. This is the current project work order; historical handoffs retain their original status.

## Current priority: recurring Monochrom exposure readiness

Latest phone feedback (11 October, 14:58 Europe/London): Malcolm still receives the message after delivery of 2.80. Treat readiness as unresolved despite the passing automated tests. Obtain the matching `MONO_EXPOSURE_READINESS_*.json` from the rejected shutter before selecting another device-specific correction; no such record accompanied this report or was found in the available files. No new build or exposure-policy change is justified by the toast alone.

Recording 52650.mp4 on 2.79 shows Monochrom Motion reporting six photos saved, then rejecting another shutter with the exposure-preview warning. The save backlog has cleared before rejection. This does not independently establish save completeness, a measured speedup or the exact metadata trigger. Candidate 2.80 MONOPLANWAIT1B corrects two source defects: colour-context exceptions discarding otherwise valid physical exposure metadata, and the final retry deadline skipping a fresh selection. It preserves the metadata age limits, exposure allocator and one-second retry budget. Diagnostics-enabled rejected shutters stage one small readiness record through the existing spool; there is no continuous export. Source verification, all 94 focused Android tests and signed-package checks passed. All 27 native libraries and 285 assets are identical to 2.79. Phone validation pending; PR #98 is a draft and is not merged. See [candidate details](../patches/monoplanwait1b/README.md).

## Capture and processing performance

Malcolm accepted the 2.78 startup focus-placement correction and authorised continuing with capture/processing performance. The first bounded candidate, 2.79 MONOSAVEPIPE1A, separates Monochrom rendering from final EXIF/DNG publication waits and wakes durable DNG publication after staging. The RAW limit remains three; a separate lightweight completion queue is bounded to one active plus two waiting, with synchronous fallback. M9 rendering and all photographic transforms are unchanged. Source verification, all 24 host scenarios, all 28 focused Android tests and signed-package checks passed. All 27 native libraries and 285 assets remain byte-identical to 2.78. PR #97 is a draft; phone performance/save-completeness validation remains pending. See [candidate details](../patches/monosavepipe1a/README.md).

Next evidence: quick successive Monochrom photographs using the normal output setting, confirming save completeness and whether backlog clears sooner. Do not claim a measured speedup from source inspection or host tests. Further M9 optimisation should follow actual phase timings.

## Autofocus lifecycle corrections

The first source audit is complete: [AF lifecycle audit](AF_LIFECYCLE_AUDIT_20261011.md). It records six findings and four bounded Java control-flow reproductions. AF-01/AF-02 corrections are implemented in draft 2.73 AFCONTINUITY1A: shared still-focus preparation and IDLE preview recovery, with explicit settings restoration at initialization/manual reset. Android build and all 101 regression tests passed, including 30 new focus cases. The signed 2.73 installer passed packaging checks; phone validation remains pending. Draft 2.74 AFLIFECYCLE1A now implements capture terminal cleanup and shared session/callback ownership (AF-03/04); Android CI passed all 145 regression cases and the signed installer passed packaging checks. Malcolm subsequently validated quick tap/capture in both profiles and three captures while focus was settling on 2.74. Draft 2.75 AFTAPHANDOVER1A implements tap/shutter handover, TouchFocus disposal and passive-settle eligibility (AF-05/06); Android CI passed all 181 regression cases and the signed installer passed packaging checks; the 2.75 M9 focus-switching/capture check subsequently passed. Monochrom saved photographs but intermittently refused shutters with exposure-preview-not-ready errors; app-resume behaviour remains unconfirmed. The six original audit findings now have source corrections, with verification and broader device evidence tracked separately. The next correction, 2.76 MONOPLANWAIT1A, addresses immediate rejection/restart when a Monochrom exposure plan is temporarily missing, with bounded retries and clean pre-submission release. Android CI passed all 199 tests and the signed installer passed packaging checks. Malcolm subsequently confirmed the 2.76 readiness fix works; PR #94 remains a draft. The next UI follow-up, 2.77 UISETTINGS1A, replaces the M9-specific queue warning and retires the flashing legacy settings popup observed in recording 52551.mp4. Android CI passed 20 UI regression tests, and the signed installer passed packaging and compiled-UI checks. Phone UI validation is pending; PR #95 remains a draft.


The 2.78 FOCUSPOINT1A follow-up addresses Malcolm's startup Monochrom tap-location report (recording 52573.mp4). Focus now shares a bounded screen-to-viewfinder coordinate conversion, and the circle retains its measured size and frame anchor through re-layout and re-tapping. Camera2 crop mapping and AF sequencing remain unchanged. Source verification passed; Android CI passed all 63 focused tests and the signed installer passed packaging checks. Malcolm confirmed “This works” on 11 October after testing 2.78; count the reported startup focus-placement issue as phone-validated. Broader lens/lifecycle coverage remains separate. This is a focus-coordinate UI correction, not new tracking work. PR #96 remains a draft.

Audit scope: the exact 2.72 FOCUSTRACK1A source, including inherited autofocus behaviour from merged 2.71. Check request ownership and transitions across camera open/close, tap focus, continuous-picture AF, manual focus, capture completion/failure, pause/resume, lens/zoom/profile/mode changes, and stale asynchronous callbacks. Distinguish confirmed code defects from device-dependent behaviour and gaps in test coverage.

Preserve Continuous Picture AF for stills. Keep M9/Monochrom rendering, exposure policy and AE/AWB controls outside tracking ownership. Firmware decryption is not a prerequisite for this audit.

The experimental 2.72 patch tracker is parked as a baseline. Malcolm's initial phone feedback was “not bad for a first pass”; this is not complete lifecycle or accuracy validation. PR #90 remains a draft and this goal does not authorize its merge.

## Blocked: SL-series firmware-derived focus tracking

Goal: investigate and adapt the SL-series subject detection, tracking modes and AF behaviour controls for the shared Android camera, across supported devices and lenses. Initial interest includes human eye/face/body tracking, adaptive tracking regions and subject-specific response profiles.

**Status: blocked by unresolved SL-series camera firmware decryption/protection.** The firmware has proved difficult to decrypt. RESEARCH1J in `mwilliams455/SL3Camera` validates the SL3-P 4.2.1 container but leaves the camera's protection scheme, keys and protected-section decoder unidentified. No AF model or camera tracking implementation has been recovered. The independently recovered lens component is not camera firmware decryption.

Unblock gate: obtain a readable camera-side loader/protection implementation demonstrably connected to the UPD format, then validate a decoder against known content identities. Readable firmware must still be assessed for model/runtime, sensor and lens-control portability; decryption alone does not establish that Leica's AF can run on Android.

This is a recorded future project goal, not an active decryption task or a claim of SL-equivalent autofocus. No further blind key screening or lens-peripheral work is scheduled as part of the current audit.

References:
- [Experimental tracking PR #90](https://github.com/mwilliams455/M9Camera_refresh/pull/90)
- [SL3Camera research status](https://github.com/mwilliams455/SL3Camera/blob/main/docs/RESEARCH_STATUS.md)
- [SL3Camera RESEARCH1J handoff](https://github.com/mwilliams455/SL3Camera/blob/main/docs/RESEARCH1J_HANDOFF.md)
