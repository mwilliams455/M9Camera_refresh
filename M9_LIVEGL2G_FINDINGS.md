# GL2G: preserve exposure when Motion reaches its ISO budget

Baseline: GL2F, commit `8924075352ae9123a8eccc897d2d86f72f92bf23`.
Candidate: `research/m9livegl2g-exposureenergy`. Phone validation is pending.

## Evidence

The 15 Ultra recording shows scene brightness jumping while the surrounding UI stays stable. For example, a stationary wall ROI drops around 2.38 s and recovers around 2.68 s. The shutter/ISO HUD shows the *planned still pair*, not the physical AE preview pair; it must not be used to diagnose lighting flicker as if it were preview sensor timing.

Three supplied GL2F capture snapshots on camera ID 2 have source readiness true, curve agreement true, maximum curve error 0.0064929128 (threshold 3/255), user EV 0, and rendered Auto EV 0. The two DIAGNOSTICS_BURST files are capture sidecar bundles, not a continuous frame trace. These snapshots argue against persistent fallback or Auto lift as the cause, but cannot exclude transient curve rejection or other frame transitions between samples.

| Sample | Observed AE | Requested RAW | Reported RAW | Actual/request energy |
| --- | --- | --- | --- | --- |
| Photo | ISO 2132, 20 ms | ISO 983, 43.377416 ms | Same | 1.0 |
| Motion, high ISO | ISO 1743, 20 ms | ISO 12800, 2.466657 ms | ISO 3200, same time | 0.25 (−2 EV) |
| Motion, moderate ISO | ISO 1821, 20 ms | ISO 4361, 8.350338 ms | ISO 3207, same time | 0.7354 (about −0.443 EV) |

Separately, the actual GL2F allocator reproduces brightness oscillation at a fixed observation (ISO 1824, 20 ms), EV 0 and Auto EV 0. Changing only the fake gyro reading produces preview scales 1.0, 0.9357, 0.7018, 0.5614, then 1.0. The preferred shutter cap continues shortening after ISO has saturated. That loses up to 0.833 EV in this sequence. This is a confirmed code defect consistent with the video, not proof of the sole device flicker cause.

The legacy `photonExposureDecision` and modern-motion diagnostic blocks may describe an older preflight allocation. The immutable exposure plan and matching request/result are authoritative for these captures.

## Change

Finalize the shared M9 plan in physical ISO units after Photon chooses a preferred shutter. Preserve the original observed exposure energy multiplied by user EV and bounded rendered Auto EV. When the preferred shutter cannot carry that energy within the automatic ISO budget, extend the shutter just enough. User-set ISO/shutter and explicit exposure-balance bounds remain authoritative. Unattainable targets use the nearest boundary and record the residual EV error.

Automatic ISO uses a valid reported maximum analog sensitivity, falling back to the advertised sensor range if optional analog metadata is absent/invalid. This is a conservative RAW policy motivated by the supplied request/result mismatch, not a device-name special case or a claim that all RAW cameras stop at their analog maximum. Android explicitly permits mixed analog/digital gain above that value: [CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY](https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics#SENSOR_MAX_ANALOG_SENSITIVITY). Explicit manual ISO can still exceed the automatic ceiling within the sensor's advertised range; actual returned gain may be lower on this phone.

The same immutable plan still drives preview scale, the RAW request and rendering intent. `allocation2G` in PRIMARY now records reference/intended targets, preferred pairs, automatic bounds, chosen energy, residual EV, reason and shutter extension. Copying a plan at shutter time preserves this evidence. Plan revision is `M9EXPOSUREPLAN2G` and the APK version gets `m9livegl2g-exposureenergy`.

No shader, colour matrix, white-balance correction, SAT2 table, curve02, native rendering kernel, JPEG encoder, Auto brightening thresholds, focus transition or GL2F tone-curve contract is changed.

## Validation

- GL2G: 3,708 assertions through the actual allocator and RAW request setter; fixed-scene gyro sweep, recorded observations, Photo/Motion EV sweeps, native ISO floors, missing analog metadata, explicit balance limits, tripod, manual priority, true exposure boundaries and immutable diagnostics.
- Existing gates: 6,779 assertions across exposure, bright-scene negative EV, Auto placement, source math, curve agreement, paired pixels, focus and atomic publication.
- Existing GPU/native shader tests pass; GL2F source acceptance/rejection and fallback checks retained.
- The reproduced 0.5614–1.0 preview scale now remains 1.0 throughout the same gyro sweep (ISO 3200, 11.4 ms).
- Hash manifest freezes 28 other authorities; production changes are limited to allocator, immutable plan/evidence, diagnostics export and build label.
- CI performs fresh source assembly, all host/GPU gates, Android compilation, APK shader/curve byte comparison and DEX contract checks. Consult the candidate commit's dedicated GL2G workflow for the resulting status.

## Remaining phone checks and tradeoffs

A slower shutter at the automatic ISO boundary can increase subject-motion blur. GL2G prioritizes the requested scene brightness when Motion's preferred shutter would otherwise underexpose. Explicit shutter remains available; at its true ISO limit the preview should show the attainable darker result.

Retest the 15 Ultra in the same dim scene: Motion and Photo, steady then small movements, EV 0 and ±1, one still per setting. Check that the viewfinder does not pulse and stills track exposure. Then check the 17 Ultra main and telephoto for haze and focus continuity. These remain device validation tasks; this change does not establish that GL2F solved the telephoto's source-curve issue.

If flicker remains, inspect continuous source-ready/rejection transitions and actual preview AE metadata. Do not adjust the M9 colour curve or add cosmetic exposure smoothing without that evidence. Preview OES reconstruction is still not exact RAW parity, and the live-versus-RAW TC20 normalization difference remains an open limitation.
