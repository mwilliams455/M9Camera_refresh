# M9Cam 2.65 ANCHORSETTLE1A

Draft candidate on 2.64 BACKGROUNDSETTLE1A, commit `3e471d95860e0434ec1db051ee902782fd98fb70`, PR #82. Phone acceptance is pending; main remains unchanged.

## Why this change

The 075534 shutter trace contains two immediate Auto reductions from +0.75 to +0.25 EV when the open-anchor cap activates. The qualified background allowance stays unchanged during both cuts. The preceding/current sensor references differ by only +0.040 and +0.050 EV respectively. An open anchor means a coherent textured region is already bright enough; it is a scene-placement classification, not a measurement of newly clipped detail. It was still included in the immediate clipping ceiling after 2.64 separated the background allowance.

The TV also changes the light reflected onto the blinds. Across the trace, hardware exposure varies about 0.78 stop and fresh TC20 tone gain varies up to 0.34 stop. This candidate targets the demonstrated abrupt anchor cuts, not all exposure movement. Only one complete Auto bracket is available, so the tests do not claim to replay every frame of the recording. `RECORDED_EVIDENCE.json` records the two cuts and the analysis limits.

## Behaviour

The raw anchor detector, its 0.25/0.50/0.75-EV cap tiers, body targets and clipping calculations are unchanged. The anchor allowance is now applied after the hard clipping ceiling is captured. Changing the allowance requires four fresh, monotonic probes over at least 750 ms, agreeing within one quarter stop. Appearance and tier changes must retain at least two common anchor fields throughout confirmation. Disjoint regions cannot confirm one another. Disappearance also needs confirmation so a brief lost detection cannot release the cap immediately.

A new body or initial scene uses its current allowance immediately. Owner, mode, tap, manual controls, ineligible Auto and unavailable-evidence boundaries clear state. A short reference bridge breaks pending votes while retaining the allowance; gaps longer than 1.2 seconds cannot complete an old window. Duplicate callbacks and out-of-order probes do not vote.

A confirmed semantic decrease uses the existing two-probe lower-target confirmation and quarter-stop descent. Current hard headroom/highlight limits still cut immediately, and existing post-cut recovery is unchanged. Captures follow the displayed exposure plan, so a capture during a transient anchor classification can have a different exposure from 2.64. Sustained scenes retain the previous eventual placement.

The existing scalar history now includes raw and qualified anchor masks, the qualified cap, confirmation count and qualification reason. History revision is `M9METERHISTORY1B`; existing fields retain their meanings. No new pixel sampling, GL work or trace worker is added. Hardware metering, AF, TC20 mathematics, colour, tone shaders, RAW/JPEG export and Monochrom remain unchanged. There is no HDR or stacking.

## Verification

The complete production Auto/tap classes pass **4,111 host assertions**, including the inherited recovery/background tests, recorded-anchor integration cases, spatial/temporal boundaries and real JSON history serialization.

`RecordedAnchorFixture.java` preserves the actual 11-step shutter bracket. Tests explicitly restore its recorded body latch (mask 1840, targets 45/22, severity 0.856528) because the preceding full probes are unavailable. Its synthetic no-anchor variant changes only base field 15's median from 92 to 89, crossing the existing detector threshold. The temporal sequence is synthetic.

With two anchor probes followed by two no-anchor probes, repeated at 250-ms intervals:

- 2.64: `[0.25, 0.25, 0.25, 0.50]`, repeated.
- 2.65: `[0.50, 0.50, 0.50, 0.50]`, repeated.

Sustained appearance gives `[0.50, 0.50, 0.50, 0.50, 0.25, 0.25, ...]`; sustained absence gives `[0.25, 0.25, 0.25, 0.50, 0.50, ...]`. A separate test seeds the trace's preceding held +0.75 EV: the parent immediately drops to +0.25; this candidate initially holds +0.75, then takes a quarter-stop step as the lower body target confirms. Real highlight-loss cases still cut immediately. Both PHOTO and MOTION are exercised. This is host verification, not phone or photographic-quality acceptance.

Four scoped files differ from 2.64: Auto, one new small helper, four appended history columns and app version metadata. The other 1,331 scoped files match. The acquisition/slew/clipping-cut/recovery block is byte-identical, as are spatial classification and raw headroom calculations. Exact fingerprints and reverse-patch restoration are checked; the assembler rejects an incorrect parent tree.

Android build and package checks pass. Packaging preserves all 27 native libraries and 285 assets from the exact 2.64 APK, verifies the signing identity, 16-KiB alignment and both compiled settings menus. Deliver the packaged APK, not raw Gradle output.

## Reproduce

```bash
python3 patches/anchorsettle1a/assemble.py /absolute/path/PhotonCamera_265
python3 patches/anchorsettle1a/host_test.py /absolute/path/PhotonCamera_264 /absolute/path/PhotonCamera_265 --json-jar /absolute/path/json-20250517.jar --output /absolute/path/host265
python3 patches/anchorsettle1a/verify_source.py /absolute/path/PhotonCamera_264 /absolute/path/PhotonCamera_265
python3 patches/anchorsettle1a/build.py /absolute/path/PhotonCamera_265 --sdk /absolute/path/android-sdk --output /absolute/path/build265
python3 patches/anchorsettle1a/package.py /absolute/path/PhotonCamera_265 /absolute/path/build265/app/outputs/apk/debug/M9Cam_2.65_ANCHORSETTLE1A-debug.apk /absolute/path/M9Cam_2.64_BACKGROUNDSETTLE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables265
```

The assembler optionally accepts `--parent` with the exact complete 2.64 tree. Otherwise it reconstructs the pinned chain. Host tests require `org.json:json:20250517`, SHA-256 `3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796`. The control APK must have SHA-256 `467f61b73d11fe9235559d93c538a9f9da4248536e8ad5182bef5aaead246949`.

## Phone check

Install over 2.64. Repeat the same room/TV framing with Auto ISO/shutter, EV 0 and AE-L off. Keep the phone steady for 20 seconds, then pan away and return. Check for abrupt whole-frame cuts while allowing gradual responses to actual light changes. Take a photo during any remaining jump, leave the app open for trace export, and return the shutter trace plus a short recording. Existing Continuous Picture AF stays selected. If normally used, check RAW+JPEG once.

Packaged candidate: `M9Cam_2.65_ANCHORSETTLE1A.apk`, 119,601,973 bytes. SHA-256:

```text
16917dc93105ef0924716a1b4ce7ef8e46670504bc599fa5019db173139ff789
```
