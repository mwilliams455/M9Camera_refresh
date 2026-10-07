# M9Cam 2.63 PREVIEWRECOVER1B

Parent: 2.62 SHUTTEREXPORT1A, commit `36cf2726c96cf2b03afd7f2016d6565d85b21cb2`, draft PR #80. Candidate for sustained, conservative recovery after an M9 exposure limit reduces the accepted correction.

## Recovered phone evidence

The user supplied `M9_SHUTTERTRACE_20261007_172628_428_31186781418542.json`. It contains 90 pre-shutter and 348 post-shutter hardware metadata records, three pre-shutter and 45 post-shutter GPU crop samples, plus actual surface draw snapshots.

At 6.537 seconds after shutter, applied M9 correction is +2 EV. At 6.802 seconds it is +0.5 EV: a 1.5-stop reduction in 266 ms. Hardware exposure is 1/100 second throughout, with ISO 57 to 56 (only -0.0255 EV). The central incoming OES crop median remains 32, while the display-render crop median changes 69 to 21; the reference-render median changes 15 to 14. These are 8-bit code values, not linear-light EV measurements.

Between 5.9 and 7.4 seconds, all captured focus distances are 0.2038835 dioptres, AF state is 2, lens state is stationary and request AF trigger is IDLE. This pulse is therefore associated with the app's exposure correction while focus is steady. The source contract stays ready. Actual surface snapshots around 5.95 and 6.84 seconds corroborate the +2 to +0.5 correction with unity preview tone gain.

Recovery then progresses through +0.5, +0.75 and +1.5 EV, followed by another reduction. In 2.62, the recovery guard is cleared immediately after its first confirmed quarter-stop rise. The next fresh probe can once again use the fast 0.5/0.75-EV acquisition step. A complete-controller synthetic test reproduces +0.5, +0.75, +1.5, +2.0 after a safety cut.

Only one complete Auto bracket/decision is recorded at shutter. There, `sampleValid` is true, reference bridging is false, and bright-background qualification caps a requested +1.75 at +1 EV. The exact binding cap at the later 6.8-second reduction is not recorded. This patch addresses the demonstrated rapid rebound; it does not claim to identify every source of limit variation or every preview fluctuation. The synthetic tests are not a replay of unavailable per-frame brackets.

A separate AF observation remains for follow-up: all 90 pre-shutter requests report CANCEL, whereas the post-shutter requests are overwhelmingly IDLE. That merits an initialization/lifecycle audit, but the largest recorded brightness pulse occurs with IDLE and a stationary lens. No AF behaviour is changed in this candidate.

## Change

The existing two-fresh-probe confirmation for the first post-cut rise is retained. Every subsequent rise remains limited to 0.25 EV per fresh probe until the target has been reached and at least four fresh probes have agreed within 0.125 EV over at least 750 ms. Repeated callbacks and elapsed wall time alone cannot complete this condition. New target changes restart the stability window. Non-rising targets break the rising confirmation; a new headroom cut re-arms the whole guard immediately. A bridged reference gap breaks the recovery confirmation/stability window while preserving the armed guard. Existing manual/ownership/reset/invalidation boundaries clear it as before.

The current target and all current headroom/highlight limits remain authoritative. Protective reductions are immediate. Initial acquisition before any cut is unchanged. A stable scene reaches the same final target; transient captures during the slower recovery follow the lower displayed plan and can therefore differ from 2.62.

Two diagnostic omissions are also corrected. Crop history previously reconstructed a Draw with its default unity tone gain, even when the actual draw used a different gain. It now retains the gain passed by MainRenderer alongside each pending crop. Draw snapshots also include the existing Auto reason string. No extra probe, pixel buffer, bracket serialization, shader command or TC20 decision is introduced.

## Verification

Complete production Auto/tap classes pass 2,852 assertions: 2,414 inherited policy, highlight, subject-headroom, settling, reference-bridge and initial-recovery assertions, plus 438 sustained-recovery assertions. The 2.62 comparison passes its 2,814 assertions, including reproduction of the old fast rebound.

At 250-ms probe spacing, the candidate trajectory is `[0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.0]`; parent is `[0.5, 0.75, 1.5, 2.0, 2.0, 2.0, 2.0, 2.0]`. Ten repeated three-probe permissive bursts reach +1.0 rather than +1.5 EV before the same immediate +0.5-EV protective reduction. Tests cover both existing supported exposure modes without changing their selected AF mode, duplicate reads, short sample intervals versus elapsed time, stable release, and bridge gaps.

Five files differ: Auto recovery, diagnostic draw/crop gain plumbing, MainRenderer's diagnostic argument, and version metadata. All other 1,327 scoped files match 2.62. Reverse patch and fresh reconstruction match exactly. Source checks verify the original statistics/sample matcher, classification, targets, caps and later tap policy; MainRenderer differs only in passing the already computed tone gain to diagnostics. Continuous Picture AF, WB, colour, tone, shaders, JPEG/DNG rendering, Monochrom, native code, assets, photo queues and the 2.62 trace exporter are unchanged.

Android build: all 60 tasks passed in 63.99 seconds. Signed APK checks pass, including matching certificate, both settings menus, 16-KiB alignment, and all 27 native libraries / 285 assets byte-identical to 2.62. Phone validation remains required.

APK: `M9Cam_2.63_PREVIEWRECOVER1B.apk`, 119,601,973 bytes. SHA-256:

```text
ef9bae5c9b506996645c11069169a2159c4b2726463dbe00bb124562242725a4
```

## Phone check

Keep Continuous Picture, M9 Photo, Auto ISO/shutter, EV 0 and AE-L off. Hold foliage against bright sky for 15 seconds, then pan down and return. Check whether bright/dark rebound is calmer and whether a genuinely brighter scene still receives an immediate protective reduction. Take a photo during any remaining pulse, leave the app open to export, and send its trace. Diagnostic saving may add overhead; this build retains the 2.62 exporter. Main remains unchanged pending evaluation.

## Reconstruct, test, build and package

```bash
python3 patches/previewrecover1b/assemble.py /absolute/path/PhotonCamera_263
python3 patches/previewrecover1b/host_test.py /absolute/path/PhotonCamera_262 /absolute/path/PhotonCamera_263 --output /absolute/path/host263
python3 patches/previewrecover1b/verify_source.py /absolute/path/PhotonCamera_262 /absolute/path/PhotonCamera_263
python3 patches/previewrecover1b/analyze_trace.py /absolute/path/M9_SHUTTERTRACE_20261007_172628_428_31186781418542.json /absolute/path/TRACE_ANALYSIS.json
python3 patches/previewrecover1b/build.py /absolute/path/PhotonCamera_263 --sdk /absolute/path/android-sdk --output /absolute/path/build263
python3 patches/previewrecover1b/package.py /absolute/path/PhotonCamera_263 /absolute/path/build263/app/outputs/apk/debug/M9Cam_2.63_PREVIEWRECOVER1B-debug.apk /absolute/path/M9Cam_2.62_SHUTTEREXPORT1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables263
```

The assembler optionally accepts `--parent /absolute/path/verified_PhotonCamera_262`. Otherwise it follows the existing source-recovery chain. The packager requires exact 2.62 SHA-256 `117f24e3b23df15fea48d37fee5bdef3a6a622e528e166c5828f7fd028b835cf` and preserves its native libraries and assets. Deliver the packaged APK, not the raw Gradle output.
