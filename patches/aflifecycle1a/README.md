# AFLIFECYCLE1A — M9Cam 2.74

Continuation of 2.73 AFCONTINUITY1A. Addresses ordinary still capture terminal cleanup (AF-03) and shared session/callback ownership (AF-04) for M9 and Monochrom.

A capture attempt owns AF preparation, request submission and RAW handoff. Submission exceptions, aborts, missing AF/results/RAW and session closure retire that attempt once, release input frames, and reopen the owning camera through existing recovery. Preview/still callbacks and delayed completion cannot mutate a replacement camera. A dedicated still session transfers ownership with a bounded configuration deadline. Capture deadlines include the requested integration/readout duration.

No renderer, native binary, exposure/WB policy or tracking algorithm changes. Continuous Picture AF and manual infinity remain covered by the inherited 2.73 tests. Tracking remains parked/default off. Tap/shutter handover (AF-05) and stale tap passive settling (AF-06) are still pending. These tests do not establish HAL focus accuracy or explain the earlier image/exposure symptoms.

## Reproduce

```sh
python3 patches/aflifecycle1a/assemble.py /absolute/new/PhotonCamera_274
python3 patches/aflifecycle1a/verify_source.py /absolute/PhotonCamera_273 /absolute/PhotonCamera_274
```

The assembler pins the complete parent and candidate source fingerprints. Android CI builds the app and runs the new lifecycle cases plus inherited regressions. Package the CI APK with `package.py SOURCE BUILT_APK VERIFIED_273_APK BUILD_TOOLS OUTPUT_DIR`; all 27 native libraries and 285 assets must remain byte-identical to 2.73. Phone validation remains pending.
