# M9Cam 2.59 PREVIEWSETTLE1A

Parent: 2.58 PREVIEWPAIR1A, commit `fc4e53099c939e93be3bbe4fd3686ec9c5698a8e`, draft PR #76. This candidate keeps the 2.56 rendering improvement and the 2.57/2.58 preview scheduling and metadata-pairing changes.

## Evidence and scope

The supplied `50666.mp4` recording shows steadier held compositions than the earlier backlit clip. The earlier repeated severe dark resets were not apparent in the reviewed held views. Exposure and white balance still adjust after reframing. Flashing red highlight warnings must be distinguished from whole-image exposure changes. The HUD reaches ISO 1600, above the earlier ISO-1200 workaround. A screen recording cannot establish which internal controller caused each change or prove preview/JPEG parity.

Source review found an avoidable exposure-settling delay: the ordinary lower-target branch reconfirmed the same target before every quarter-stop reduction. Even after two fresh samples had agreed on that target, the confirmation counter returned to zero after each step.

This candidate keeps the first two-sample confirmation, then allows each fresh, valid meter sample to continue down toward that same confirmed target, at the existing maximum 0.25 EV per sample. A different target restarts confirmation using the existing 0.125-EV tolerance. Reaching the target or rising exposure ends the transition. The counter is bounded to two. Invalid/stale evidence and manual user EV clear a pending confirmation; existing manual-ISO/shutter, eligibility, owner and tap-epoch resets remain.

Immediate highlight/headroom release remains immediate. Target selection, low-key placement, highlight budgets, positive acquisition, sample cadence, freshness checks, ISO/shutter allocation and AE-L are unchanged. This is a timing refinement, not a new exposure or metering mode.

No source defect was established for the observed white-balance settling. AWB, source colour reconstruction, tungsten guard, matrices and curves are unchanged. No additional colour smoothing or fixed WB offset is introduced.

The saved JPEG/DNG processing code is unchanged. The existing WYSIWYG shutter authority still follows the displayed exposure plan, so a shot taken during the transition may use a different exposure than 2.58 at that instant. Final exposure targets remain unchanged; this does not promise identical pixels for every capture timing.

## Verification

`host_test.py` compiles the full production `M9AutoExposure2D` and `M9TapMeter1A` classes. Only JSON serialization is stubbed. Both parent and candidate run the inherited policy, highlight-grandfathering and subject-headroom suites, plus new transition tests for Photo and Motion.

- Candidate: 1,472 assertions/checks pass: 125 inherited policy, 4 grandfathering, 1,015 subject-headroom and 328 transition checks. Parent control passes its corresponding 1,460 checks.
- A stable 0.75-to-0 EV synthetic transition takes four fresh samples instead of six. Its trace changes from `[0.75, 0.50, 0.50, 0.25, 0.25, 0]` to `[0.75, 0.50, 0.25, 0]`.
- The first ordinary quarter-stop adjustment remains identical. Alternating lower targets are rejected, duplicate reads cannot advance twice, new targets reconfirm, and the transition remains monotonic and bounded without overshoot.
- Highlight safety, stale/missing/mismatched evidence, owner/mode changes, manual exposure, EV, eligibility, tap epoch and reset boundaries are exercised. Positive acquisition and settled policy expectations pass unchanged.
- These are synthetic host samples, not phone timing measurements or full image-rendering comparisons.
- Source verification permits only `M9AutoExposure2D.java` and app version metadata to differ. Reversing those edits restores the exact parent; 1,330 other scoped files remain unchanged. All 1,332 scoped files in a fresh reconstruction match the build source.

Full Android debug build passed (60 tasks; Gradle 8.11.1, JDK 17.0.20.1+1). The packaged APK preserves all 27 native libraries and 285 assets byte-for-byte from 2.58; signature, version, compiled settings and 16 KiB alignment checks passed.

APK: `M9Cam_2.59_PREVIEWSETTLE1A.apk`, 119,585,589 bytes. SHA-256:

```text
bfd74d0f3a042896aa3aa14078a37dfad9ee9e2b25d295cc6d45c85d2a7c5e0e
```

Machine-readable reports accompany the patch. Phone validation remains pending.

## Reconstruct, test, build and package

From this repository root:

```bash
python3 patches/previewsettle1a/assemble.py /absolute/path/PhotonCamera_259
python3 patches/previewsettle1a/host_test.py /absolute/path/PhotonCamera_258 /absolute/path/PhotonCamera_259 --output /absolute/path/host259
python3 patches/previewsettle1a/verify_source.py /absolute/path/PhotonCamera_258 /absolute/path/PhotonCamera_259
python3 patches/previewsettle1a/build.py /absolute/path/PhotonCamera_259 --sdk /absolute/path/android-sdk --output /absolute/path/build259
python3 patches/previewsettle1a/package.py /absolute/path/PhotonCamera_259 /absolute/path/build259/app/outputs/apk/debug/M9Cam_2.59_PREVIEWSETTLE1A-debug.apk /absolute/path/M9Cam_2.58_PREVIEWPAIR1A.apk /absolute/path/android-sdk/build-tools/35.0.0 /absolute/path/deliverables259
```

The assembler optionally accepts `--parent /absolute/path/verified_PhotonCamera_258`. Otherwise it follows the pinned source recovery chain. Use JDK 17 and the parent's SDK/NDK/build-tool versions; add `--offline` only with dependencies already available. Package against 2.58 APK SHA-256 `5bfb698902fae69e8c986d7bbca3f98ab042eea1d95b52ea52c06e7156c32275`. The packaging script preserves all 27 accepted native libraries and 285 assets, checks the signature, version, compiled settings and 16 KiB alignment. The packaged APK is the deliverable, not the raw Gradle APK.

## Phone check

Use M9 Photo, Auto ISO/shutter, EV 0, AE-L off and your usual ISO ceiling. Repeat the flowers/window movement, holding each composition for several seconds. Look for a more continuous settle after reframing and no renewed exposure oscillation. Check Motion mode too. If flashing red masks make the brightness difficult to judge, temporarily disable the existing highlight-warning display aid; that is not a required exposure setting.

Compare a saved capture with the settled preview. Check user EV and AE-L still work normally. If brightness resets or prolonged hunting remain, retain existing M9 diagnostics and a short clip from the same run. WB may still visibly adjust because this candidate does not change AWB.

This is a draft candidate stacked on 2.58. Main is not merged by this change.
