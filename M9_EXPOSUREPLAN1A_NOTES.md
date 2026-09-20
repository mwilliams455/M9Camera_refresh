# M9EXPOSUREPLAN1A — exposure ownership reset

Base: GL1U `f5ce9888f62e3f6dced298a0edaf537005fc7d5b`, pinned Photon upstream `f0e6425d2509fb8ab834d5d3af593183038b778c`.

Status: source implementation and host tests complete; Android/device validation tracked in the PR. This is an experimental build, not a confirmed solution to all preview/JPEG mismatches.

## Problem addressed

GL1U obtained the displayed/captured exposure from `GenerateExpoPair(-1)`, which bypasses the inherited scene correction. Small deliberate exposure offsets could then be cancelled by TC20 re-metering the exposed RAW. Manual controls also changed the hardware input used as the next automatic baseline. GL1R added display compression from the intended exposure, producing another response against an increased EV.

## Changes

- One immutable exposure plan per preview observation, shared by HUD, GL exposure simulation, still request and render. It records observed hardware exposure, neutral allocated reference, auto correction, user EV/manual settings, intended pair and observation identity.
- In M9 non-ZSL PHOTO, preview hardware AE stays on with zero compensation. User dial EV is converted from Camera2 compensation steps to stops and added to the existing settings EV. User ISO and shutter are applied to the plan/capture, while the live feed stays a metering reference.
- The existing bounded regional MFM proxy now participates in the live plan. Nonzero EV does not turn off its auto baseline. Manual ISO/shutter and tripod retain the previous auto-assist bypass. This remains a Xiaomi preview-Y research proxy, not a claim of exact Leica metering.
- TC20 derives its gain from measured RAW statistics divided by the actual-capture/reference exposure ratio. Exposed pixels retain that ratio. Neutral unoffset captures keep the old gain calculation; TONEBOUND050, target color and curve02 remain. The plan-tagged production route holds the old post-JPEG edge replacement so it cannot independently overwrite exposure intent.
- GL tone classification uses the neutral reference ratio. Exposure simulation still uses the intended ratio. No new shader curve or color asset is introduced.
- Capture validates plan age, camera, mode and controls. If a control change invalidates the plan during autofocus, capture waits for the next valid preview plan, for up to one second, then releases the UI with an error. Closing the camera invalidates pending waits. An inherited autofocus-timeout fallthrough that could request two captures is also closed.
- LIVEPAIR records the plan. Render tone diagnostics record intent scale, application and pre-correction statistics. Planning does not publish mutable capture diagnostics or modify burst history.

## Scope preserved

Single RAW; no HDR; JPEG+DNG; 12MP output; GL1T continuous-preview capture; GL1U sidecar transport; native color core; SAT2/curve02 and M9 target assets. Manifest hashes enforce these source/assets boundaries. Changed production files are listed in `patches/m9cam-m9exposureplan1a-manifest.json`.

## Reproducible verification

The workflow replays GL1U source steps, applies the hash-checked overlay, runs host tests and builds Android debug with JDK17. It checks packaged DEX markers and the existing shader, records APK SHA256, and uploads an explicitly named APK artifact.

```
python3 patches/apply-m9cam-m9exposureplan1a.py /path/to/assembled/GL1U
python3 patches/tests/m9exposureplan1a/run.py /path/to/assembled/PhotonCamera
```

The host harness compiles the real planner, allocator, MFM, motion policy and manual-control code with minimal fake hardware APIs. It tests the old 1/3-stop cancellation, new response in uniform/backlit synthetic grids, EV step conversion, auto-baseline continuity, manual pairs, physical clamps, actual-vs-requested render exposure, plan invalidation, immutability and capture-history isolation. It does not run JNI, GPU, Camera2 timing or claim image-quality validation.

## Focused device checks

Keep framing/light steady for each series. Test one ordinary indoor scene and one dark subject against a bright window. At each scene shoot Auto EV0, -1/3, +1/3, -1 and +1; let AE settle first. Record the viewfinder and retain corresponding JPEG, DNG, LIVEPAIR, PRIMARY and exposure/render sidecars. Then try explicit ISO and shutter changes, resetting both to Auto between tests. Try a shutter press immediately after moving EV and after switching lenses.

Expected: auto scene assist can be nonzero in backlight; EV changes keep the same auto baseline for an unchanged scene; preview and JPEG brighten/darken in the selected direction; small EV changes survive; planned and requested exposure agree; actual sensor differences are visible in metadata; no shutter-time black flash or stopped preview. Compare a neutral indoor frame with the preferred earlier rendering for tone/color regressions.

## Known limits / next decision

Processed OES preview still has the inherited empirical color/tone fit and can clip differently from single RAW. Matching the exposure plan does not prove matching scene reproduction. GL submission is recorded honestly; a presented GPU frame is not timestamp-acknowledged. Preview exposure simulation retains its inherited +/-4EV limit, with a diagnostic flag. Normalizing scalar RAW statistics cannot reconstruct clipped highlights or scene changes after the plan. No post-RAW boost calibration has been invented.

Evaluate this build before another curve adjustment. If exposure responds correctly but preview/JPEG tone remains inconsistent, investigate processed-preview/source-domain parity with the paired data rather than retuning EV or appending another rescue curve.
