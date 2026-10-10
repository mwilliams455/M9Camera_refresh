# M9Cam 2.60 PREVIEWRECOVER1A

Parent: 2.59 PREVIEWSETTLE1A, commit `cced095b9134255fa7883584a7ba186a77d81a70`, draft PR #77. This candidate retains the preceding rendering, probe scheduling, frame pairing and confirmed downward-settling improvements.

## Evidence and change

The supplied outdoor recording shows a broadly similar settled rendition to the saved JPEG, with dark grass and a dense blue sky. Different framing and capture timing prevent an exact preview/JPEG comparison. Noticeable brightness swings remain around 25–28 seconds as the camera pans near the sun. These are separate from the flashing red highlight warning. The recording alone does not identify the responsible internal controller.

Source review found an asymmetric response that can reproduce repeated rebounds: a positive headroom limit below the held exposure causes an immediate protective reduction, but the very next permissive probe may restore as much as 0.75 EV. Alternating restrictive and permissive probes therefore repeatedly lower and raise exposure.

PREVIEWRECOVER1A retains the immediate reduction and all existing highlight limits. After a protective reduction, the first fresh probe requesting brighter exposure is held. A second consecutive fresh probe requesting a rise permits a first step bounded by 0.25 EV and by the lower of those two requested targets. Subsequent sustained recovery follows the existing acquisition rules. A non-rising target breaks the pending confirmation; another protective reduction arms recovery again. Duplicate reads never count as fresh evidence.

Owner, mode, manual ISO/shutter, manual EV, ineligible Auto, tap epoch, surface reset and invalid/stale evidence clear the recovery state. This is a narrow temporal guard following a protective reduction, not a new metering mode or new exposure target. Ordinary initial acquisition and the 2.59 lower-target refinement remain intact. A sustained real scene change pays one additional meter-sample confirmation after a protective cut and uses a smaller first recovery step.

No WB, colour, tone-curve, shader, saved JPEG/DNG renderer, native code, assets, Monochrom, ISO/shutter allocation, AE-L, frame pairing, probe cadence or queue change is made. The WYSIWYG shutter still follows the displayed plan; a capture during recovery can use a different exposure at that instant. Identical capture pixels at every timing are not promised.

## Verification

`host_test.py` compiles the complete production Auto and tap classes; only JSON serialization is stubbed. Both versions run the inherited policy, highlight, subject-headroom and 2.59 transition suites, plus the new Photo/Motion recovery scenarios.

- Parent: 1,768 checks. Candidate: 1,772 checks (125 policy, 4 highlight-grandfathering, 1,015 subject headroom, 328 downward transitions, 300 recovery).
- In a synthetic mapped backlit scene, the parent repeatedly rebounds from +0.5 to +1.25 EV after each permissive probe. The candidate remains at +0.5 EV while permissive and restrictive probes alternate. Both reach the same +1.75 EV target when safe evidence persists.
- A simple synthetic recovery to +0.75 EV changes from `[0.25, 0.5, 0.75]` to `[0, 0.25, 0.5, 0.75]` after a protective cut. This is meter-sample behavior, not measured phone latency.
- Tests cover duplicate reads, interruption by restrictive/non-rising evidence, changing recovery targets, sustained recovery, renewed immediate protection, ordinary acquisition and the state boundaries listed above.
- Only `M9AutoExposure2D.java` and app version metadata change. All other 1,330 scoped source/asset files match 2.59. Reversing the patch restores the exact parent. Fresh reconstruction is checked against the build tree.

Host tests demonstrate the controller weakness and candidate behavior; they do not prove it caused every observed phone transition. Phone validation is required.

Full Android build passed (60 tasks, 6m 31s). Package checks passed: all 27 native libraries and 285 assets match 2.59 byte-for-byte, signing identity matches, both settings menus verify, and 16 KiB alignment is retained.

APK: `M9Cam_2.60_PREVIEWRECOVER1A.apk`, 119585589 bytes. SHA-256:

```text
e1837fedaff643d2878165e6ab252dffd6c26163fc23431f948d388a2d90576d
```

## Reconstruct, test, build and package

From the repository root, using the parent's JDK 17 / Android toolchain:

```bash
python3 patches/previewrecover1a/assemble.py /absolute/path/PhotonCamera_260
python3 patches/previewrecover1a/host_test.py /absolute/path/PhotonCamera_259 /absolute/path/PhotonCamera_260 --output /absolute/path/host260
python3 patches/previewrecover1a/verify_source.py /absolute/path/PhotonCamera_259 /absolute/path/PhotonCamera_260
python3 patches/previewrecover1a/build.py /absolute/path/PhotonCamera_260 --sdk /absolute/path/android-sdk --output /absolute/path/build260
python3 patches/previewrecover1a/package.py /absolute/path/PhotonCamera_260 /absolute/path/build260/app/outputs/apk/debug/M9Cam_2.60_PREVIEWRECOVER1A-debug.apk /absolute/path/M9Cam_2.59_PREVIEWSETTLE1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables260
```

The assembler optionally accepts `--parent /absolute/path/verified_PhotonCamera_259`; otherwise it follows the pinned recovery chain. The packager requires the exact 2.59 APK SHA-256 `bfd74d0f3a042896aa3aa14078a37dfad9ee9e2b25d295cc6d45c85d2a7c5e0e`, preserves its 27 native libraries and 285 assets, and checks signing identity, version, compiled settings and 16 KiB alignment. Deliver the packaged APK, not the raw Gradle output. Machine-readable build/package reports record final verification.

## Phone comparison

Use M9 Photo, Auto ISO/shutter, EV 0 and AE-L off, with the usual ISO ceiling. Repeat the outdoor pan so the sun approaches and leaves the frame edge; hold each composition for several seconds. Compare brightness swings against 2.59. Check an indoor/window transition too, including whether recovery feels unnecessarily hesitant. Repeat in Motion if used.

Check that the settled preview and a same-framing saved JPEG still agree. The highlight-warning display aid may be disabled temporarily to make whole-image brightness easier to judge. If swings remain, a short recording with existing M9 diagnostics from the same run is the next evidence needed; do not assume this candidate resolves them from host tests alone.

This is a draft candidate stacked on 2.59. Main is unchanged.
