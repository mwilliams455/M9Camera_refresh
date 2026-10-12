# AFCONTINUITY1A — 2.73

Addresses AF-01/AF-02 from the lifecycle audit on the exact 2.72 parent. Both M9 and Monochrom still requests use shared focus preparation. Preview recovery preserves mode/regions/manual distance and uses one capability-gated continuous-AF CANCEL, followed by IDLE repeats even if the command fails. AUTO/MACRO locks and manual infinity survive. Session initialization and explicit manual-panel exit restore preferences separately. Generic repeating rebuilds clear AF triggers; one-shot rebuilds clear them in finally.

30 parameterized controller/request-boundary cases cover both profiles. They use real Robolectric request builders and observe builder values at session submission because the shadow does not copy builder metadata into built native requests. Profile exposure configuration is stubbed in these focus tests. Source verification checks both still call sites and explicit reset wiring. This is not a HAL/lens or full capture pipeline simulation. Android CI passed all 101 tests (30 new and 71 inherited), with zero failures/errors/skips. Phone validation remains pending.

The 2.72 tracker remains unchanged and default off. AF-03 through AF-06 (capture terminal cleanup, stale callback ownership, tap/shutter arbitration, stale passive phase) remain pending. SL firmware tracking stays blocked.

Reconstruct: `python patches/afcontinuity1a/assemble.py /fresh/path [--parent /exact/2.72/source]`. Verify: `python patches/afcontinuity1a/verify_source.py /exact/2.72/source /exact/2.73/source`. Package: `python patches/afcontinuity1a/package.py SOURCE CI_APK VERIFIED_2.72_APK BUILD_TOOLS OUTPUT`. All 27 native libraries and 285 assets must remain byte-identical to delivered 2.72.

## Delivered installer

`M9Cam_2.73_AFCONTINUITY1A.apk` — version `2.73-afcontinuity1a`, code `27273`, 119,618,357 bytes. SHA-256: `c1c5b81e783770ba4e925ffd9da7ac31ea7e1b0763669aff0e2c7f8ce42f177d`. Signing certificate matches the delivered baseline. All 27 native libraries and 285 assets remain byte-identical to 2.72; 16 KiB ZIP/Monochrom ELF checks passed.

Build: [run 38117358090](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38117358090), source commit `0525ad04dbb6f4108145f5719b2b42c215069344`. See `BUILD_VERIFICATION.json`, `SOURCE_VERIFICATION.json` and `PACKAGED_VERIFICATION.json`. The raw CI APK retains the parent's output filename; its compiled manifest and the delivered installer correctly identify 2.73.

Phone checks: repeated M9/Monochrom captures with Continuous Picture AF; AUTO/MACRO focus retention; manual near and infinity; tap focus followed by capture; lens switching and pause/resume. Do not infer a fix for image softness, exposure pumping or the screen-recorder/shutter issue solely from these source/tests.
