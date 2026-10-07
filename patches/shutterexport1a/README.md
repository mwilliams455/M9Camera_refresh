# M9Cam 2.62 SHUTTEREXPORT1A

Parent: 2.61 PREVIEWBRIDGE1A, commit `87a62f9a1a51dd12fb3510df921e8cfe88c17728`, draft PR #79. This candidate fixes diagnostic delivery. It does not claim to fix the remaining brightness pumping.

## Evidence

The three burst manifests supplied on 7 October list shutter traces for captures at 17:24:18 and 17:26:28. Private payloads contain 7,746,989 bytes and, for successive versions of the later trace, 9,358,761 and 12,013,236 bytes. `payloadInline` is false: these manifests are indexes, not trace data.

Telemetry shows 1,709 recovered entries referencing 1,642,252,456 bytes, 1,714–1,722 pending individual exports, only four individual writes, and no recorded stage/export failures. The app was visible. Manifest writes themselves took approximately 10–26 seconds. The supplied LIVEPAIR is dated 5 October and cannot diagnose the current capture.

Source inspection explains the delivery problem: shutter traces used the ordinary single-thread exporter, behind recovered sidecars with a 12-second initial delay and 250-ms per-entry staggering. A slow historical destination could occupy that worker. The separate PRIMARY exporter did not cover shutter traces. The indexes confirm internal creation, but do not identify which old export was blocking or the cause of preview pumping.

## Change

Shutter traces now use a dedicated single-thread exporter with one recurring task. Each pass chooses the newest eligible trace by staged time, then sequence. The existing per-path pending map coalesces repeated updates rather than creating one task per snapshot. Recovery includes already staged traces, newest first, without putting historical ordinary sidecars ahead of them.

The pump runs at one-second intervals while the app is visible and diagnostic saving is enabled. Failed writes retain their private payload and recovery manifest and receive a ten-second retry delay; other eligible traces can continue. Disabling diagnostic saving or leaving the app cancels scheduled trace work. An already running storage call can finish, matching existing transport behaviour.

There is one trace writer, including across pause/resume. Claiming an entry uses the same per-path map lock as staging/recovery. An in-flight private payload survives until its stream closes if a newer snapshot replaces it during a slow destination open. The newest snapshot then exports; an old export cannot remove the newer pending entry. Completed/superseded private payloads are reclaimed after their active stream finishes.

Existing SAF/direct fallback and 64-KiB streaming are unchanged. No additional backlog purge is introduced; the old reset marker and recovery are unchanged. Ordinary and PRIMARY exporters remain intact. New telemetry identifies pending trace count, successful/failed exports, last exported path, active work and scheduled task count.

## Verification

The host suite compiles the complete production spool with real files, scheduled executors and controlled Android storage/context/logging/JSON stubs. It passes 225 assertions:

- Three traces recover beside 1,709 ordinary entries while a historical ordinary export is deliberately blocked. The newest 12-MB trace exports first and matches byte-for-byte; older traces also recover.
- Sixty updates during a blocked trace destination open preserve the active payload, coalesce pending updates, avoid concurrent writers across pause/resume, and leave the newest bytes after two exports.
- Both public routes fail; payload and restart manifest survive, another trace progresses, and retry succeeds without a new capture or resume.
- Hidden/disabled behaviour, re-enabling diagnostics and the fresh PRIMARY exporter pass.

Only `M9DiagnosticBurstSpool.java` and version metadata differ from 2.61. All other 1,330 scoped files match; reversing the patch restores the exact parent. All 1,332 reconstructed scoped files match the build source. Continuous Picture AF, exposure, WB, colour, tone, rendering, photo queues and existing crash fixes are unchanged.

The Android build passed all 60 tasks in 67.77 seconds. Packaging verifies all 27 native libraries and 285 assets are identical to 2.61, the signing certificate matches, both settings menus remain intact, and 16-KiB alignment is retained. The phone's actual storage provider remains untested.

APK: `M9Cam_2.62_SHUTTEREXPORT1A.apk`, 119,601,973 bytes. SHA-256:

```text
117f24e3b23df15fea48d37fee5bdef3a6a622e528e166c5828f7fd028b835cf
```

## Recover existing phone traces

Install as an update over 2.61, preserving app data. Keep Save diagnostic files enabled, reopen the camera and keep it in the foreground for roughly 30–60 seconds. Look in `DCIM/Camera` for `M9_SHUTTERTRACE_20261007_172628_428_31186781418542.json` or `M9_SHUTTERTRACE_20261007_172418_456_31056809392393.json`. A new capture should not be required to recover these internally staged traces. If still unavailable, a newly exported burst manifest includes trace-specific delivery telemetry.

The next exposure investigation should use the recovered trace to distinguish sensor exposure changes, rendered probe acceptance, reference-bridge activity and preview correction. Current evidence does not justify another exposure-policy change.

## Reconstruct, test, build and package

```bash
python3 patches/shutterexport1a/assemble.py /absolute/path/PhotonCamera_262
python3 patches/shutterexport1a/host_test.py /absolute/path/PhotonCamera_262 --output /absolute/path/host262
python3 patches/shutterexport1a/verify_source.py /absolute/path/PhotonCamera_261 /absolute/path/PhotonCamera_262
python3 patches/shutterexport1a/build.py /absolute/path/PhotonCamera_262 --sdk /absolute/path/android-sdk --output /absolute/path/build262
python3 patches/shutterexport1a/package.py /absolute/path/PhotonCamera_262 /absolute/path/build262/app/outputs/apk/debug/M9Cam_2.62_SHUTTEREXPORT1A-debug.apk /absolute/path/M9Cam_2.61_PREVIEWBRIDGE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables262
```

The assembler optionally accepts `--parent /absolute/path/verified_PhotonCamera_261`; otherwise it follows the existing recovery chain. The packager requires the exact 2.61 APK SHA-256 `3cf264151a241595e1dc16535fe05511fd2ddd877acb2aa81fa228fe6d193921` and retains its native libraries and assets. Deliver the packaged APK, not raw Gradle output. Main remains unchanged pending phone validation.
