# M9Cam 2.66 EXPOSURESETTLE1A

Draft candidate on 2.65 ANCHORSETTLE1A, commit `78a0669eec8c81f1de0f08fd1f2d9cbc63164f76`, PR #83. The user reports 2.65 still pumps with changing TV content. Main remains unchanged; 2.66 requires phone validation.

## Evidence and scope

The 082643 trace shows a 0.673-EV reduction in combined Auto plus preview tone gain over 0.805 seconds. Both sampled frames use ISO 198 and 10 ms exposure; the incoming crop's green median stays 35 while the displayed median falls from 38 to 23. Throughout this trace the anchor mask is zero and both anchor/background allowances are nonbinding. The earlier fixes therefore do not address this instance.

Three behaviors contribute: subject/whole-scene ownership alternation changes placement; the highlight allowance later falls from +0.75 to +0.50 to +0.25 EV; and preview tone gain varies with fresh estimates and abruptly resets when metadata pairing fails. The source and one complete shutter bracket confirm a 16-field dark component is rejected by the existing 14-field subject maximum, falling back to whole-scene placement. These spatial rules are unchanged here.

Only one full Auto bracket was retained. It limits lift to +1 EV because step +1.25 creates regional channel-clip growth in fields 11 and 15. We cannot identify the fields behind the later cuts from the old scalar-only history. The sampled input crop is not proof that every region was unchanged. Real clipping cuts remain immediate; this candidate does not promise to eliminate every brightness change.

## Behavior

`M9ExposureRise1A` gives settled Auto placement and preview tone the same rule for increases: at least four fresh, increasing probe timestamps spanning 750 ms must all support the increase. Only the minimum supported level is approved. Duplicates and out-of-order probes cannot vote; a gap longer than 1.2 seconds breaks confirmation. Returning to the current level cancels a pending increase. Decreases are passed through to the existing caller policy.

Auto keeps its initial acquisition behavior. After reaching a target, or after any hard highlight cut, subsequent increases require this confirmation and use at most 0.25 EV per fresh probe. This applies to the final placement request across scene-owner changes, not only to recovery after a highlight cut. Existing hard clipping cuts and ordinary two-probe quarter-stop descent are byte-identical. Manual, owner, mode, tap, unavailable-evidence and reference-bridge boundaries reset or interrupt the new state consistently with the existing controller.

Preview tone uses the same fresh-evidence rule for every increase and retains its existing 0.125-EV slew, 0.04-EV deadband and +/-0.5-EV bounds. A change in Auto or user EV interrupts pending tone-rise confirmation, so tone must acquire fresh sustained support after placement moves. Valid darker tone requests retain the existing immediate bounded step.

A short metadata mismatch holds the last qualified tone gain for at most one second from the last trusted probe. This requires valid, fresh same-camera/mode evidence, both source contracts ready and not continuity-held, and reference energy within 0.25 EV of the trusted value. It never treats mismatched evidence as a new vote. Expiry, stale/invalid sources and owner changes return to unity. Both positive and negative tone are held, preventing a negative correction from suddenly brightening the preview during a brief gap.

This deliberately slows brightening after a pan or real light change, and dynamic scenes can stay at a more conservative exposure/tone level. Stable scenes converge to the existing targets within the existing tone deadband. Preview tone remains an estimate of the unchanged saved-render correction; this needs WYSIWYG checking on the phone, especially during transitions. There is no HDR, stacking or local tone operation.

## Diagnostics and preserved paths

History revision `M9METERHISTORY1C` appends raw placement target and rise-confirmation fields to Auto, and Auto EV, reference energy and rise confirmations to tone. Each Auto row also owns deep copies of the neutral, last-safe and first-rejected highlight summaries, including all 24 fields, the stop reason and body/scene qualification context. At the search ceiling the first-rejected value is null. The existing 128-row rings bound retention, and serialization remains on the existing trace worker. No extra pixel sampling or GL operations are introduced.

Six scoped files differ from 2.65: Auto, preview evidence policy, history, two small pure-Java helpers and app version metadata. The other 1,331 scoped files match. Spatial detection, raw headroom/targets, tap policy, background/anchor qualification, TC20 pixel mathematics, GL probe work, hardware metering, AF, WB, colour/tone shaders, saved renderers, RAW/JPEG queues and Monochrom are unchanged. Continuous Picture AF remains selected by the existing code.

## Verification

The exact reconstructed source passes **4,875 candidate host assertions**. The 2.65 parent separately passes 4,094 inherited assertions with its original expected timings. Candidate tests retain all inherited static headroom, boundary and capture-policy checks; four timing tests are copied with explicit new expectations:

- `SettlingTest`: a brief ordinary rebound now waits for confirmation.
- `RecoveryTest`: at 200-ms probe spacing, recovery starts on the fifth probe, the first to span 750 ms.
- `SustainedRecoveryTest`: at 250 ms, recovery from +0.5 to +2 EV follows `[0.5, 0.5, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2]`. Repeated three-probe permissive bursts stay at +0.5. Hard cuts remain immediate.
- `RecordedAnchorTest`: disappearance still qualifies after four probes; the resulting rise additionally needs sustained final-placement support, reaching +0.5 on probe seven. Appearance and hard-cut checks are unchanged.

New tests cover shared timing boundaries, combined Auto/tone requests, bounded metadata holding, owner/energy/manual boundaries, deep-copy history serialization and the unmodified 082643 shutter bracket. The actual bracket retains +1 EV placement and reports the exact regional clip-growth stop at +1.25 EV.

The 40-row tone-only replay preserves gain through all four recorded metadata-gap rows and respects the existing 0.125-EV maximum step. It uses recorded parent Auto output as an external input and synthetic stable warm-up to the first observed tone state. It is not a full closed-loop replay; preceding and subsequent full Auto brackets are unavailable. `FIXTURE_PROVENANCE.json` and `TONE_REPLAY.json` document these limits.

Exact fingerprints, reverse-patch restoration and reconstruction checks pass. Android build, signature, 16-KiB alignment and compiled menu checks pass. Packaging preserves all 27 native libraries and 285 assets byte-for-byte from the shipped 2.65 APK. Deliver the packaged candidate, not raw Gradle output.

## Reproduce

```bash
python3 patches/exposuresettle1a/assemble.py /absolute/path/PhotonCamera_266
python3 patches/exposuresettle1a/host_test.py /absolute/path/PhotonCamera_265 /absolute/path/PhotonCamera_266 --json-jar /absolute/path/json-20250517.jar --output /absolute/path/host266
python3 patches/exposuresettle1a/verify_source.py /absolute/path/PhotonCamera_265 /absolute/path/PhotonCamera_266
python3 patches/exposuresettle1a/build.py /absolute/path/PhotonCamera_266 --sdk /absolute/path/android-sdk --output /absolute/path/build266
python3 patches/exposuresettle1a/package.py /absolute/path/PhotonCamera_266 /absolute/path/build266/app/outputs/apk/debug/M9Cam_2.66_EXPOSURESETTLE1A-debug.apk /absolute/path/M9Cam_2.65_ANCHORSETTLE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables266
```

The assembler optionally accepts `--parent` with the exact complete 2.65 tree; otherwise it reconstructs the pinned recovery chain. Host tests require `org.json:json:20250517`, SHA-256 `3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796`. The control APK must have SHA-256 `16917dc93105ef0924716a1b4ce7ef8e46670504bc599fa5019db173139ff789`.

## Phone check

Install over 2.65. Use the same room/TV framing, Auto ISO/shutter, EV 0 and AE-L off. Hold steady for 20 seconds, then pan away and back to check settling speed. Take a photo during any remaining jump and leave the app open for trace export. Return the shutter trace and a short recording. Check the saved JPEG against the settled preview; if normally used, also check RAW+JPEG once.

`M9Cam_2.66_EXPOSURESETTLE1A.apk`: 119,601,973 bytes, SHA-256:

```text
53b27a9bb4b0977b57bc8003880087c482974ae3ea7c631e0093af13877da393
```
