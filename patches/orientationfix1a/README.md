# M9Cam 2.35 ORIENTATIONFIX1A — recover portrait preview

Parent repository commit: `63af8af93927105af9397f44cbf466a4b2b01ff4` (2.34 PREVIEWCOLOURFRAME1A).
Accepted photographic and preview control: 2.33 LEICAEV1A.

## Report and correction

On 4 October 2026 Malcolm reported: “Camera opens horizontally when the phone is in vertical orientation.” The supplied screenshot 49706.png shows upright portrait UI and a sideways camera image. This rejects 2.34's preview framing change; 2.34 must not be called phone-validated or used as the accepted orientation baseline.

2.34 added the SurfaceTexture producer matrix to a path already using the application's sensor-orientation transform. The earlier synthetic checks proved the new shader followed the supplied matrix; they did not establish that applying it on top of the existing camera geometry was correct on the handset. The report is consistent with an extra quarter turn. The actual handset matrix was not supplied, so its entries and exact producer-side reason have not been measured.

2.35 restores all six changed preview source/shader files exactly to the phone-accepted 2.33 versions. This removes the producer-matrix sampling path from the sharp preview, blur, peaking and their shared probes, along with its added geometry snapshots/tap identity changes. The two tests specific to the withdrawn integration are removed; an external GPU regression check now compares the complete restored sharp and blur output with accepted 2.33 and rejects the 2.34 extra-rotation case. There is no guessed fixed 90-degree correction and no device-specific rotation rule.

The decimal EV presentation from 2.34 is retained byte-for-byte: menu, wheel including zero, selected value and shooting-profile descriptions show −0.7, 0.0, +0.3 etc. Storage and allocation retain exact thirds. Saved JPEG/DNG rendering, capture exposure, histogram/clipping and all other accepted preview behavior match 2.33.

## Verification and limits

- 18 selected Android suites: 133 tests, 132 passed, one pre-existing skip, no failures/errors. Debug APK build passed.
- Source comparison: 1,193 files match 2.33 exactly. The only six differences are version/build identity, decimal EV formatter/wheel/profile/menu presentation and updated existing EV test expectations.
- Real GLES shader verification: 98,304 sharp pixels and 98,304 blur pixels exactly match the 2.33 control across four rotations and both mirror states. All eight simulated extra-rotation cases reject the 2.34 negative control. These are synthetic inputs, not a recreation of unreported handset metadata.
- Existing brightness/firmware shader checks pass, including 1,200 negative/unity comparisons, 1,800 positive-gain comparisons, zero oracle channel error, fallback behavior and monotonic EV response.
- The incremental patch round trip reproduces seven overridden files and removes one obsolete test. Packaging verifies every asset and all 25 native libraries against accepted 2.33, compiled decimal EV entries, signing certificate, version, archive integrity and 16 KiB alignment.

On 4 October 2026 Malcolm confirmed “That works.” The orientation recovery is now phone-accepted. The next requested stages are Auto ISO maximum/slowest shutter, AE lock and self-timer; see `../autoiso1a/README.md`. This confirmation supersedes the phone-validation-pending status recorded in the original 2.35 delivery reports.

## Current order

The user has prioritized Auto ISO/slowest shutter, followed by AE lock and self-timer. Preview colour/framing remains unfinished; 2.34's colour math audit is useful but its framing integration is withdrawn. Do not reintroduce producer transforms without a coherent full camera/stream/display orientation model and real buffer metadata. There is no justification for lens-specific colour tuning or changes to the accepted saved-image appearance.

After remaining preview work, continue the requested architecture review of one app containing M9 Colour and M Monochrom, preserving their accepted rendering, exposure policies, DNG handling and per-mode settings. Auto ISO maximum/slowest shutter proceeds in 2.36; AE-L and Leica timer follow. Bracketing remains deferred. Cross-lens colour/fringing investigations remain parked.

## Recovery

`assemble.py <fresh-tree>` chains 2.34 and applies the hash-checked rollback. Build inherited sharpness natives with `patches/sharpnessmenu1a/build_native.py` and NDK 27.0.12077973; use Java 17. The delivery includes the build runner and its distinct Gradle build directory.

`verify_source.py <2.34-tree> <accepted-2.33-tree> <2.35-tree> <report.json>` verifies the complete rollback and retained EV display. `verify_gpu.py <2.35-tree> <output-dir> <accepted-2.33-tree> <2.34-tree>` checks actual shaders against the control and regression.

`package.py <2.35-tree> <built-apk> <accepted-2.33-apk> <build-tools-35.0.0> <delivery>` creates the signed upgrade. Accepted 2.33 APK SHA256: `bff25f5bd8a9b92487d17bda2e984367b242d00fc449c8b7258d0c959cc4ef05`.

Source and recovery bundle stay private; the inherited firmware publication restriction remains. No public push is attempted.
