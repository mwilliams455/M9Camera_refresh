# M9Cam 2.61 PREVIEWBRIDGE1A

Parent: 2.60 PREVIEWRECOVER1A, commit `d309662ccaed319174dcd3f05e0e4be0c1145a12`, draft PR #78. This is a test candidate stacked on that branch. Continuous Picture remains selected; autofocus behaviour is unchanged.

## Problem and evidence

The supplied `50797.mp4` shows repeated whole-preview brightness changes in a nearly steady woodland composition, especially around 4–14 seconds. The 6.75 and 7.25 second frames differ substantially despite both displaying `AF-C · LOCK`. That HUD text means focused or locked, so it is not proof of an actual focus lock. The recording establishes instability but does not separate sensor AE changes from the M9 correction, or prove that every swing has one cause.

The production Auto controller accepts a rendered meter probe only while the current neutral reference energy remains within 0.25 EV of that probe's reference. A larger reference change immediately replaced the accepted positive correction with zero. In a synthetic mapped scene, a 0.30 EV reference increase discarded a previously accepted +1.75 EV correction. Repeated valid/mismatched readings then cycled between +0.75 EV and zero, although the synthetic scene evidence was unchanged.

## Change

A fresh accepted probe now records an exposure anchor. If the latest probe fails only the reference-energy comparison, the controller can bridge that short mismatch while all of these conditions hold:

- Same camera/mode, intact statistics and the original timestamp-pairing/age guards.
- The probe is no older than the trusted anchor; no future or out-of-order sample is accepted.
- At most 500 ms since the accepted probe was submitted, and at most 0.5 EV reference movement from its accepted reference.
- A positive accepted correction still exists and the legacy policy is not requesting negative correction.
- Transporting the accepted exposure to the new reference leaves a positive correction.

For an eligible gap, the temporary correction is the lesser of the accepted correction and the correction needed to keep the accepted absolute exposure energy. It therefore adds no exposure beyond the validated anchor. A falling reference does not gain extra correction to compensate; this is intentionally conservative. The accepted controller baseline is not overwritten by this temporary result, avoiding a repeated-gap ratchet. Duplicate callbacks never renew the deadline or count as fresh evidence. Pending lower-target and recovery confirmations are broken; a protective recovery guard remains armed.

Fresh valid probes always retain the existing target selection, highlight limits and immediate protective reductions. Larger changes, elapsed deadlines, stale/malformed/foreign/unpaired samples and disabled metering retain the existing immediate fallback. Camera/mode changes, manual controls, Auto ineligibility, tap epoch changes and explicit resets clear the anchor.

This is a bounded exposure continuity change, not a new metering target. For up to half a second during a small reference mismatch, it may retain a brighter exposure than 2.60's immediate zero-correction fallback. It does not hold through a fresh valid highlight warning. The saved capture still follows the displayed exposure plan, so capture exposure during that interval can differ from 2.60. Identical pixels at every shutter timing are not promised.

Colour, WB, tone curves, shaders, TC20 prediction, saved JPEG/DNG rendering, native libraries, assets, Monochrom, frame pairing, probe cadence, ISO/shutter allocation, AE-L, AF and save/crash fixes are unchanged.

## Verification

`host_test.py` runs the complete production Auto and tap classes with JSON serialization stubbed. The candidate passes 2,414 assertions: 125 policy, 4 highlight-grandfathering, 1,015 subject headroom, 328 downward settling, 300 protective recovery and 642 new reference-transition checks. The parent passes its 2,262 comparison assertions, including assertions that reproduce its collapse.

The reproduction now changes a +1.75 EV correction at reference energy 1.0 to +1.45 EV at reference energy `2^0.30`: the product remains `2^1.75`, eliminating that synthetic brightness jump. Repeated transitions do not lower the accepted baseline. Tests cover the deadline, duplicate reads, changed reference within the gap, both drift directions, half-stop boundary, insufficient anchor energy, fresh highlight restrictions and the rejection/reset boundaries above in Photo and Motion.

Only `M9AutoExposure2D.java` and `app/build.gradle` differ. All other 1,330 scoped files match 2.60. Source verification confirms the original sample matcher, statistics, valid-sample decisions, subject qualification and highlight policy are unchanged. Reversing the patch restores the exact parent. Fresh reconstruction matches all 1,332 scoped files.

These are controller tests, not a replay of phone metadata. Device validation remains required; this candidate addresses a demonstrated source failure without claiming that it explains every fluctuation in the recording.

The full Android build passed (60 tasks, 2m 24s), followed by a successful final incremental verification. Package checks passed: all 27 native libraries and 285 assets match 2.60 byte-for-byte, the signing identity and both compiled settings menus verify, and 16 KiB alignment is retained.

APK: `M9Cam_2.61_PREVIEWBRIDGE1A.apk`, 119585589 bytes. SHA-256:

```text
3cf264151a241595e1dc16535fe05511fd2ddd877acb2aa81fa228fe6d193921
```

## Reconstruct, test, build and package

From the repository root with JDK 17 and the existing Android SDK:

```bash
python3 patches/previewbridge1a/assemble.py /absolute/path/PhotonCamera_261
python3 patches/previewbridge1a/host_test.py /absolute/path/PhotonCamera_260 /absolute/path/PhotonCamera_261 --output /absolute/path/host261
python3 patches/previewbridge1a/verify_source.py /absolute/path/PhotonCamera_260 /absolute/path/PhotonCamera_261
python3 patches/previewbridge1a/build.py /absolute/path/PhotonCamera_261 --sdk /absolute/path/android-sdk --output /absolute/path/build261
python3 patches/previewbridge1a/package.py /absolute/path/PhotonCamera_261 /absolute/path/build261/app/outputs/apk/debug/M9Cam_2.61_PREVIEWBRIDGE1A-debug.apk /absolute/path/M9Cam_2.60_PREVIEWRECOVER1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables261
```

The assembler optionally accepts `--parent /absolute/path/verified_PhotonCamera_260`. Otherwise it follows the existing recovery chain. The packager requires the exact 2.60 APK SHA-256 `e1837fedaff643d2878165e6ab252dffd6c26163fc23431f948d388a2d90576d` and retains its native libraries and assets. Deliver the packaged APK, not the raw Gradle output. Build and package results are recorded alongside these instructions.

## Phone comparison

Keep Continuous Picture, M9 Photo, Auto ISO/shutter, EV 0 and AE-L off. Hold a scene with dark foliage and bright sky for about 15 seconds, then pan toward the ground and return. Compare whole-image brightness cycling with 2.60; the flashing red clipping overlay is a separate display aid. Take a photo during the held view and compare the settled preview with the saved image. Also check that a move into a genuinely bright scene still reduces exposure promptly.

If pumping remains, send the short recording and an existing `M9_SHUTTERTRACE_*.json` from the same run. The exposure-plan diagnostics now include `referenceTransitionHeld` and `referenceBridgeRevision`, allowing this specific mechanism to be distinguished from changing hardware AE, fresh target changes or another preview stage.

Main is unchanged pending phone evaluation.
