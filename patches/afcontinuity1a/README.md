# AFCONTINUITY1A — 2.73

Addresses AF-01/AF-02 from the lifecycle audit on the exact 2.72 parent. Both M9 and Monochrom still requests use shared focus preparation. Preview recovery preserves mode/regions/manual distance and uses one capability-gated continuous-AF CANCEL, followed by IDLE repeats even if the command fails. AUTO/MACRO locks and manual infinity survive. Session initialization and explicit manual-panel exit restore preferences separately. Generic repeating rebuilds clear AF triggers; one-shot rebuilds clear them in finally.

30 parameterized controller/request-boundary cases cover both profiles. They use real Robolectric request builders and observe builder values at session submission because the shadow does not copy builder metadata into built native requests. Profile exposure configuration is stubbed in these focus tests. Source verification checks both still call sites and explicit reset wiring. This is not a HAL/lens or full capture pipeline simulation. Android CI and phone validation pending.

The 2.72 tracker remains unchanged and default off. AF-03 through AF-06 (capture terminal cleanup, stale callback ownership, tap/shutter arbitration, stale passive phase) remain pending. SL firmware tracking stays blocked.

Reconstruct: `python patches/afcontinuity1a/assemble.py /fresh/path [--parent /exact/2.72/source]`. Verify: `python patches/afcontinuity1a/verify_source.py /exact/2.72/source /exact/2.73/source`. Package: `python patches/afcontinuity1a/package.py SOURCE CI_APK VERIFIED_2.72_APK BUILD_TOOLS OUTPUT`. All 27 native libraries and 285 assets must remain byte-identical to delivered 2.72.
