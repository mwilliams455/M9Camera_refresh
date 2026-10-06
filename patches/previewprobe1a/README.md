# M9Cam 2.57 — PREVIEWPROBE1A

Phone-test candidate based on 2.56 SHADINGPERF1A, commit `15fcb07fae6e2aa6ca4149dc2e190731a72379bc`. The user reports faster rendering and good saved images, but M9 viewfinder flicker/lag while exposure settles. This change addresses a reproducible preview probe starvation fault. It is not yet a confirmed diagnosis of every part of the phone symptom.

## Fault and change

The renderer serialises two GPU readbacks: an Auto exposure bracket and paired preview brightness evidence. Both use a 250 ms submission interval. Auto is offered first. Previously, when its fence completed after that interval, Auto could immediately submit again on the same frame. During sustained slow frames or readbacks, the brightness probe never got a turn.

`M9PreviewMeter2D.sample()` now remembers whether it entered with a pending fence. It polls that fence as before, then yields the rest of that completion frame instead of immediately resubmitting. The existing renderer scheduler can submit the brightness probe once Auto is idle. A still-pending fence continues to block the other probe. No additional concurrent readback or blocking wait is introduced.

Only this probe file and app version metadata change. Auto/tap policy, metering fields, tone prediction arithmetic, freshness/source guards, shaders, saved JPEG/DNG renderers, Monochrom, queues, diagnostics and recent crash fixes are byte-identical to 2.56. At slow frame rates, fair scheduling necessarily gives Auto fewer submissions than the previously monopolising probe; this is not a measured reduction in exposure settling time.

## Regression evidence

`host_test.py` compiles the complete production Auto probe, brightness probe and TC20 math, plus the unchanged scheduling block extracted from `MainRenderer`. Android clock, GL fence/readback and metadata inputs are deterministic adapters. Exposure-policy calculations are stubbed because this test concerns scheduling, not AE convergence. Display gain is observed in production order, before that frame's probe submissions.

Across 80 synthetic draws per case:

| Case | 2.56 Auto / brightness submissions | 2.57 Auto / brightness submissions |
| --- | ---: | ---: |
| 33 ms frames | 10 / 10 | 10 / 10 |
| 100 ms frames | 27 / 27 | 27 / 27 |
| 250 ms frames | 80 / 0 | 40 / 40 |
| 350 ms frames | 80 / 0 | 40 / 40 |
| 100 ms frames, 300 ms GPU latency | 27 / 0 | 14 / 13 |
| Manual EV | 0 / 80 | 0 / 80 |

The harness also checks a single readback in flight, nonblocking waits, stalled-fence and map-failure cleanup, single-sample slew, camera/mode identity, held-source positive-gain rejection, and stale-evidence reset. The parent performs 602 assertions and the candidate 645. See `HOST_VERIFICATION.json`.

**Known limit:** at 350 ms frame intervals and the simulated 300 ms readback latency, the unchanged freshness guards still produce unity-gain resets after a brightness lift. Fair scheduling removes starvation, but does not prove flicker is eliminated under all slow-preview conditions. No stale-evidence retention or additional smoothing is added. Real GPU timing, scene movement and phone AE convergence remain untested.

`SOURCE_VERIFICATION.json` checks exact reversal of the scheduling change and 1,329 other scoped files unchanged. Reassembly is compared with the build source. `PACKAGED_VERIFICATION.json` records the APK signature, identity, 16 KiB packaging alignment and byte preservation of the parent's 27 native libraries and 285 assets.

The full Android debug build passed: 60 tasks executed with Gradle 8.11.1, AGP 8.10.1 and SDK 36. See `BUILD_VERIFICATION.json`. No Android instrumentation or phone test was run.

## Recover and build

```bash
python3 M9Camera_refresh/patches/previewprobe1a/assemble.py PhotonCamera_257
# Or add --parent /path/to/verified/PhotonCamera_256.
python3 M9Camera_refresh/patches/previewprobe1a/verify_source.py PhotonCamera_256 PhotonCamera_257
python3 M9Camera_refresh/patches/previewprobe1a/host_test.py PhotonCamera_256 PhotonCamera_257 --output probe_tests
python3 M9Camera_refresh/patches/previewprobe1a/build.py PhotonCamera_257 --sdk /path/to/android-sdk --output build257
python3 M9Camera_refresh/patches/previewprobe1a/package.py PhotonCamera_257 build257/app/outputs/apk/debug/M9Cam_2.57_PREVIEWPROBE1A-debug.apk /path/to/M9Cam_2.56_SHADINGPERF1A.apk /path/to/android-sdk/build-tools/35.0.0 deliverables257
```

Use the packaging step to retain the accepted sharpness libraries missing from a fresh Gradle APK. The source chain and signing identity are inherited from 2.56.

## Phone comparison

Install over 2.56. In M9 Photo with Auto ISO/shutter, EV 0 and usual diagnostics settings, move between a bright and dim area, then hold still. Compare repeated brightness jumps and time to settle, including a dim scene where preview slows. Also check tap metering, AE lock and a nonzero EV. Saved-image quality should retain the 2.56 processing. Report whether flicker improves, remains or worsens; if it persists, capture a short screen recording and contemporaneous diagnostics/logcat before making broader control-loop changes.

Main remains 2.55. This candidate includes the unmerged 2.56 shading improvement and is pending phone validation.
