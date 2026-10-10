# M9Cam 2.64 BACKGROUNDSETTLE1A

Draft candidate based on 2.63 PREVIEWRECOVER1B, commit `36f57c9d0013d2b1eb34a94d9121d939fc517005`, PR #81. Phone validation is pending. The user reports that 2.63 still changes brightness in the static room with a changing television.

## Evidence and scope

The October 8 shutter trace records an Auto reduction from +1.75 to +1.0 EV between 1.9567 and 2.7385 seconds after shutter. Sensor exposure energy changes only +0.00142 EV; incoming and neutral-reference centre medians stay 52 and 35, while the displayed median changes from 122 to 77. Actual preview tone gain is the same at both endpoints. The reason at the intervening sampled decisions identifies background qualification. This supports an app placement change, rather than a hardware centre-metering disagreement, for that interval.

Only the shutter has a complete Auto bracket. There the qualified body's background cap is +1.75 EV. All 19 neutral-reference clipped samples are in one TV field. The background score is 0.51326, dominated by the outer clipped fraction. Reducing that count synthetically to 18 lowers the raw cap to +1.5 EV; 11 clips lowers it to +1.0 EV without changing the centre/body statistics. The old controller treats that semantic cap as an immediate protective cut.

`RecordedRoomFixture.java` contains the actual numerical shutter bracket. Its temporal variants are explicitly synthetic, not a replay of missing later brackets. Tests seed the recorded latched body (mask 8627136, target 44/15, severity 1) because the earlier probes that established it are unavailable. There is no claim that TV clipping explains every phone pulse.

A separate recorded interval also has an independent TC20 gain change. This candidate instruments that controller without changing its mathematics, freshness checks, reset-to-unity policy or slew. The next trace can distinguish a fresh changed tone target from stale/foreign evidence.

## Behaviour

A new body initially uses its current raw background allowance. Subsequent changes require four consecutive fresh probes on the same side of that allowance, agreeing within 0.25 EV, over at least 750 ms. An opposing vote or a window wider than one step restarts confirmation. The accepted value is the smallest change supported by the whole window. Duplicate or out-of-order reads cannot vote. Reference gaps break confirmation; longer gaps, body/owner resets, manual exposure and ineligible Auto clear or restart it as appropriate.

Raw highlight retention, headroom and existing open-anchor limits remain immediate. Only the background evidence allowance is separated from the hard ceiling. A background-only lower target uses the existing two-probe confirmation and 0.25-EV descent. While settling, applied exposure can temporarily exceed the newly qualified semantic allowance, but it cannot exceed current hard protection. Existing 2.63 post-cut recovery remains intact. Initial acquisition and eventual exposure in a stable scene retain the previous policy.

Captures follow the displayed exposure plan, so captures taken during a held background fluctuation can differ from 2.63. This is global exposure placement, with no new local tone operation, HDR or stacking.

Two independently bounded scalar histories retain up to 128 Auto and 128 tone rows. Auto records raw/qualified caps, hard limits, requests, result, body evidence, reference energy and provenance. Tone records requested/target/applied EV, tail guard, median and freshness/reset reason. No new pixel sampling, GL commands or file writes run on the producer threads. The existing trace worker copies and serializes the rings into `preMeterDecisions`, `postMeterDecisions` and preserved `initialPostMeterDecisions`.

## Verification

The full production Auto/tap classes pass 3,622 host assertions: 2,852 inherited assertions, 202 recorded-room scenario checks, 555 temporal qualification checks and 13 bounded-history/serialization checks. PHOTO and MOTION are exercised. Host history serialization uses `org.json:json:20250517`; its SHA-256 is recorded in `HOST_VERIFICATION.json`. This is not an Android device or photographic-quality test.

With the clipping sequence 18, 11, 14, 19 repeated at 250-ms intervals, the old controller produces `[1.5, 1, 1, 1.25, 1.5, 1, 1, 1.25]`; this candidate holds `[1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75]`. Sustained lower qualification gives `[1.75, 1.75, 1.75, 1.75, 1.5, 1.25, 1, 1, 1, 1]`. Genuine regional highlight-loss cases still cut immediately.

Six scoped files differ from fully reconstructed 2.63: Auto, two new small helpers, diagnostic additions to PreviewEvidence/ShutterTrace, and app version metadata. The other 1,328 scoped files match. Source guards preserve the neutral probe, statistics, spatial body selection, raw caps, tone calculations, GL sampling, AF, sensor metering, WB, colour, saved renderers, Monochrom, native source, assets and capture/export queues.

The initial local baseline had two stale RAW-output files. A complete unmodified reconstruction restored their exact historical hashes and matched all other files; the shipped 2.63 APK also defines the expected methods. No new RAW behaviour was introduced. `BASELINE_RECOVERY.json` records the recovery. The new assembler checks a complete parent/source fingerprint, including unchanged files, to reject a stale `--parent` tree.

Build and package results are in `BUILD_VERIFICATION.json` and `PACKAGED_VERIFICATION.json`. Deliver the packaged APK, never the raw Gradle output. Packaging retains all 27 native libraries and 285 assets from the exact 2.63 APK, checks its signing identity and 16-KiB alignment, and verifies both compiled settings menus.

## Reconstruct, test, build and package

```bash
python3 patches/backgroundsettle1a/assemble.py /absolute/path/PhotonCamera_264
python3 patches/backgroundsettle1a/host_test.py /absolute/path/PhotonCamera_263 /absolute/path/PhotonCamera_264 --json-jar /absolute/path/json-20250517.jar --output /absolute/path/host264
python3 patches/backgroundsettle1a/verify_source.py /absolute/path/PhotonCamera_263 /absolute/path/PhotonCamera_264
python3 patches/backgroundsettle1a/build.py /absolute/path/PhotonCamera_264 --sdk /absolute/path/android-sdk --output /absolute/path/build264
python3 patches/backgroundsettle1a/package.py /absolute/path/PhotonCamera_264 /absolute/path/build264/app/outputs/apk/debug/M9Cam_2.64_BACKGROUNDSETTLE1A-debug.apk /absolute/path/M9Cam_2.63_PREVIEWRECOVER1B.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables264
```

The assembler accepts `--parent` only for a complete source tree matching the pinned 2.63 fingerprint. Without that option it reconstructs the full chain. Host tests can omit `--json-jar` for the policy tests with JSON stubs; real history serialization checks require the jar. The control APK must have SHA-256 `ef9bae5c9b506996645c11069169a2159c4b2726463dbe00bb124562242725a4`.

## Phone check

Install over 2.63. Use M9 Photo, Auto ISO/shutter, EV 0, AE-L off and existing Continuous Picture AF. Hold the same room/TV composition for 15–20 seconds, then pan away and return. Check whether brief TV changes still pump exposure and whether a sustained scene change settles normally. Take a photo during any remaining fluctuation, leave the app open for trace export and return the new shutter trace plus a short recording. Test RAW+JPEG once if that is a normal save mode. Main remains unchanged pending phone validation.

Packaged candidate: `M9Cam_2.64_BACKGROUNDSETTLE1A.apk`, 119601973 bytes. SHA-256:

```text
467f61b73d11fe9235559d93c538a9f9da4248536e8ad5182bef5aaead246949
```
