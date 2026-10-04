# M9Cam 2.34 PREVIEWCOLOURFRAME1A

**WITHDRAWN: phone orientation regression reported 4 October 2026.** Portrait UI displays a sideways preview in 2.34. Its texture-transform integration is reverted by 2.35 ORIENTATIONFIX1A; retain only the decimal EV presentation. Automated results below did not validate the handset orientation contract. See `../orientationfix1a/README.md`.

Parent: `a74a8ea7e824b57886cccb066eab9bdfec1d7f72`, phone-accepted M9Cam 2.33 LEICAEV1A. On 4 October 2026 Malcolm confirmed: “Everything works the only critique is that the EV should be decimal values and not fractions but that's easy to fix. If you can fix that then move on to color and framing next”. This supersedes the prior order that put Auto ISO/slowest shutter immediately after EV.

## Decimal EV

The settings menu, manual wheel (including zero), selected wheel value and shooting-profile descriptions display one decimal place: −0.7, −0.3, 0.0, +0.3, +0.7, and so on. Storage, the nineteen exact-third values from −3 to +3, normalization, persistence, profile schema and physical exposure allocation are unchanged. Display rounding is never fed back into exposure calculations. Menu help calls them “one-third EV steps” without fraction glyphs.

## First framing correction

The GL preview previously sampled the camera texture using fixed rotation/mirror coordinates without reading `SurfaceTexture.getTransformMatrix`. Android requires the producer transform after each `updateTexImage`; it can contain crop, orientation and sampling-border information. Primary reference:
https://developer.android.com/reference/android/graphics/SurfaceTexture#getTransformMatrix(float[])

The renderer now latches that matrix with each new texture, including frames consumed during lens-settle tracking. It composes the producer matrix with the conversion from the existing top-origin texture coordinates to canonical GL coordinates once per latch, on the CPU. The ordinary producer vertical flip therefore becomes an exact identity sampling matrix, preserving accepted orientation without an extra per-pixel flip/rounding round trip.

The sharp preview, focus peaking and external-texture blur use the same matrix. Auto/tap probes, tone prediction, histogram/clipping evidence and optional shutter pixel probes inherit the sharp shader's current sampling matrix, so they sample the same image region. A changed producer transform participates in the existing tap geometry identity and clears an old fixed-screen selection. Tap's existing screen-to-probe mapping and exposure policy are unchanged.

Optional diagnostics freeze the raw producer matrix with each draw and each asynchronously sampled evidence packet. This does not introduce another readback or change the existing probe cadence. Existing diagnostic-file switches remain authoritative. The current draw's matrix must not be substituted for an older paired pixel packet's matrix.

This corrects one confirmed missing framing operation. It does not prove identical live/still field of view on every camera: stream dimensions, active-array edges, stabilization and vendor stream crops can still matter. Existing aspect-ratio, RAW cropping, digital zoom policy and saved rendering are unchanged.

## Colour audit

The preview already reconstructs the controlled incoming OES signal using reported tone curves, inverse colour matrix, WB gains and post-RAW boost. It uses the saved renderer's native source-context factory for sensor→ProPhoto and ProPhoto→M9 matrices, followed by the selected firmware saturation/contrast and TG1. These colour functions are byte-for-byte unchanged by this patch.

Two historical paired diagnostic records (camera IDs 2 and 5) were replayed using their actual reported inverse tone curves, non-identity matrices, white limits, exposure scale and tungsten weights. Across 1,100 pixels and all 25 saturation/contrast combinations, candidate and parent output are identical, and the independent matrix/integer-firmware oracle has zero channel error on this corpus. This checks implementation math, not equality of processed preview and RAW-derived JPEG pixels. No colour offset, WB fit or lens-specific tuning is justified by this evidence.

Remaining colour limitations include ISP demosaic/shading, information already clipped in the preview and the saved renderer's spatial chroma/detail processing. A current paired preview/JPEG comparison is needed before another correction can be specified responsibly. Cross-lens colour calibration and fringing remain parked.

## Verification

- Android build passed. 19 selected suites: 135 tests, 134 passed, one existing skip, zero failures/errors. New framing tests check immutable draw geometry and invalidation of an active tap after producer crop changes. EV label expectations use decimals; existing exact-third/persistence/allocation tests remain active.
- Actual production GLES vertex, fragment and blur shaders compile on Mesa. 24,576 normal-transform pixels are byte-identical to 2.33. 98,304 coordinate pixels cover four sensor rotations, both mirror states, ordinary producer flip, identity producer, asymmetric crop and producer rotation. The same 98,304 pixels compare blur versus sharp geometry with at most one coordinate-code difference from floating-point sampling boundaries.
- Existing brightness/firmware GPU checks pass: 1,200 negative/unity comparison pixels, 1,800 positive-gain oracle pixels over all 25 saturation/contrast combinations, unchanged fallback, independent tone probe and monotonic EV response.
- Thirteen-file source patch reproduces all manifest hashes. Source isolation checks 1,187 unchanged files and 361 frozen photographic files; saved JPEG/DNG, capture requests, allocation, colour reconstruction and Auto/tap policies are unchanged.
- Packaging checks all 25 native libraries against accepted 2.33, all assets except the two intended preview shaders, compiled decimal menu entries, package/version, signing certificate, 16 KiB alignment and archive integrity.

Automated checks do not replace phone validation. Retain 2.33 as the accepted fallback until this candidate is checked.

## Phone comparison and next order

1. Confirm decimals in the EV menu, wheel and a profile: −0.7, 0.0, +0.7. Underlying exposure behavior should be as accepted in 2.33.
2. In a static scene containing an edge near each frame boundary plus neutral/coloured objects, compare the preview and saved JPEG. Check normal portrait/landscape use and the lenses already in use; tap metering and histogram/clipping should continue to follow the visible image.
3. If colour or framing still differs, retain the JPEG and its PRIMARY JSON with diagnostics enabled, plus a preview screenshot from the same framing. The screenshot helps compare composition; the paired samples and their matrix/timestamps identify the actual preview input. Do not claim a screenshot and later capture are the same sensor frame.
4. Continue only evidence-supported preview colour/framing corrections, then the requested architectural review for one app with M9 Colour and M Monochrom. Share camera/UI infrastructure while preserving each accepted photographic pipeline, exposure behavior, DNG handling and per-mode settings.

Auto ISO maximum/slowest shutter, AE-L, timer and bracketing remain unimplemented Leica-control stages and are deferred under Malcolm's revised priority. Do not describe all Leica standardization as complete. Optional M9 B&W/Vintage follows the merger review.

## Reproduce and recover

`assemble.py <fresh-tree>` chains the exact accepted 2.33 sources and verifies patch hashes. Build inherited sharpness natives with `patches/sharpnessmenu1a/build_native.py`, NDK 27.0.12077973 and Java 17. Run Gradle `:app:assembleDebug :app:testDebugUnitTest` with the selected suites in the delivered build runner. Use a distinct Gradle build directory.

`verify_source.py <2.33-tree> <candidate-tree> <report.json>` verifies isolation. `verify_gpu.py <candidate-tree> <output-dir> <2.33-tree>` checks the production shader math and geometry. `audit_colour.py <candidate-tree> <output-dir> <2.33-tree> <paired-JSON-dir>` runs the historical colour check; the two original input JSON files accompany the private source/checks archive.

`package.py <candidate-tree> <built-apk> <accepted-2.33-apk> <build-tools-35.0.0> <delivery>` signs and packages the final APK. Accepted 2.33 SHA256: `bff25f5bd8a9b92487d17bda2e984367b242d00fc449c8b7258d0c959cc4ef05`.

Keep source and recovery bundle private. The inherited firmware publication restriction remains; no public push is attempted.
