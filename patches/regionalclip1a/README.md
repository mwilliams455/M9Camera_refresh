# M9Cam 2.67 REGIONALCLIP1A

Candidate on 2.66 EXPOSURESETTLE1A, commit `444c246a5e2f714aa88e4a820f0a12c8b4091f42`, draft PR #84. Main remains unchanged pending phone validation.

## Problem and evidence

The matching 09:48:22 TV-room trace records Auto moving between +0.25, +0.50 and +0.75 EV while preview tone remains at unity. During the steady section, reference exposure changes by about 0.031 EV. All eight downward Auto steps report regional channel-clip growth. The renderer records the corresponding exposure-scale changes. The trace does not establish a conflict with centre metering or that diagnostic export causes the pumping.

The 32x24 probe is divided into 24 regions containing 30 or 36 pixels. At +4.188 seconds, +0.50 EV is accepted with two clipped pixels in field 10. At +4.409 seconds, three clipped pixels cross its 8% threshold, becoming the second rejected region and cutting Auto to +0.25 EV. A gate-level replay of the exact shipped Java method confirms that restoring just that regional statistic removes the rejection. Other statistics also changed between these frames; this establishes predicate sensitivity, not the physical cause of the changed sample.

The earlier settling policy delays rises but deliberately passes highlight cuts immediately. It therefore cannot prevent a borderline region from repeatedly releasing and reapplying the same limit.

## Change

`M9RegionalClipQualification1A` retains one 24-bit clipping mask per exposure step. A field enters at the existing thresholds, without delay. After entry, it releases only when its clipped fraction or its incremental clipped fraction clears the respective threshold by **more than one sampled pixel**. Pixel counts come from the existing probe geometry, including the unequal field widths.

Crossing the neutral baseline's 4% exemption or its luma-q90 exemption alone cannot clear an already-triggered channel-clipping field. This prevents those classification switches from declaring restored RGB detail. At least two retained fields limit the exposure step, as in the existing regional rule. The new cap is combined with the existing raw highlight cap by taking the minimum; it cannot weaken an existing safety limit.

The existing qualified-body rule can still defer background channel clipping during useful subject progress. Its subject fields remain protected. Global clipping and near-white rules remain active and unchanged. The existing exposure rise confirmation, quarter-stop slew, immediate hard cuts, scene targets and tap policy are unchanged.

Only fresh increasing probe timestamps update masks. Duplicate/out-of-order probes cannot release them. State resets after a gap over 1.2 seconds and at invalid evidence, owner, mode, tap-epoch, manual-exposure and Auto-ineligible boundaries. There is no new timer on exposure recovery.

This is deliberately conservative near a clipping boundary. A scene may remain darker until measured clipping clears the release margin. It still requires phone testing for settling after a pan, changing light and preview/JPEG agreement.

## Diagnostics and scope

`M9METERHISTORY1D` retains the raw highlight bracket and adds the independently qualified regional cap, source probe timestamp, and entry/clear/held masks for all 11 steps. Snapshots own their arrays and remain bounded by the existing 128-row history. This does not generate additional trace files or change the exporter.

Four scoped files differ: Auto, the new helper, history and app version metadata. The other 1,334 scoped files are identical. Probe resolution, GL readback, tone math, hardware metering, AF, WB, colour, shaders, saved renderers, Monochrom, image queues and diagnostic export are unchanged. No HDR or stacking is introduced.

## Verification

- All **4,875 inherited 2.66 host assertions** pass unchanged on both parent and candidate.
- **284 new candidate assertions** cover quantized gate entry, actual field geometry, persistent borderline measurements, baseline exemptions, duplicate/out-of-order samples, gaps, resets, body deferral, subject protection, genuine clearance and immutable exported masks.
- In the isolated controller regression, 2.66 produces eight cuts and eight rises; 2.67 produces one initial cut and no subsequent rise/cut cycle. Genuinely clear evidence releases the cap and normal brightening resumes.
- The complete, unmodified shutter bracket retains +0.75 EV on both versions.
- Exact source fingerprints, reverse-patch restoration and an independent reconstruction pass. Android assembly passes all 60 tasks. Packaging preserves all 27 native libraries and 285 assets byte-for-byte from 2.66, retains the update signing certificate and 16-KiB alignment, and verifies both settings menus.

The temporal regression uses the recorded base/+0.50-EV pairs with explicitly synthetic missing bracket steps and repeated timing. It is **not** a complete replay of the recording or proof of a device fix. `FIXTURE_PROVENANCE.json` records those limits. No embedded room images are published.

## Reproduce

```bash
python3 patches/regionalclip1a/assemble.py /absolute/path/PhotonCamera_267 --parent /absolute/path/PhotonCamera_266
python3 patches/regionalclip1a/host_test.py /absolute/path/PhotonCamera_266 /absolute/path/PhotonCamera_267 --json-jar /absolute/path/json-20250517.jar --output /absolute/path/host267
python3 patches/regionalclip1a/verify_source.py /absolute/path/PhotonCamera_266 /absolute/path/PhotonCamera_267
python3 patches/regionalclip1a/build.py /absolute/path/PhotonCamera_267 --sdk /absolute/path/android-sdk --output /absolute/path/build267
python3 patches/regionalclip1a/package.py /absolute/path/PhotonCamera_267 /absolute/path/build267/app/outputs/apk/debug/M9Cam_2.67_REGIONALCLIP1A-debug.apk /absolute/path/M9Cam_2.66_EXPOSURESETTLE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables267
```

Omit `--parent` to reconstruct the complete pinned source chain. Use JDK 17, Android platform 36, build-tools 35.0.0, NDK 27.0.12077973 and CMake 3.22.1. The host JSON dependency is `org.json:json:20250517`, SHA-256 `3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796`. Packaging requires the exact shipped 2.66 APK, SHA-256 `53b27a9bb4b0977b57bc8003880087c482974ae3ea7c631e0093af13877da393`.

## Phone check

Install as an update over 2.66. With Auto ISO/shutter, EV 0 and AE-L off, hold the same TV/window framing for 20 seconds, then pan away and back to check recovery. Take a photo during any remaining jump and leave the app open for trace export. Compare the settled preview with the saved JPEG. A short recording and the matching shutter trace will distinguish clipping that remains from any other cause.

`M9Cam_2.67_REGIONALCLIP1A.apk`: 119,601,973 bytes; SHA-256 `13b5d3001276f636b5327705a035e153d6209f28aa4fdf94a3b62770aba1f6a2`.
