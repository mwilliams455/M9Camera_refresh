# M9Cam 2.90 CCTGUARD1A

Parent: verified 2.89 RAWGEOMETRY1A, including its phone scene check. This candidate implements the custom-colour item from the 2026-10-12 numeric review; it does not claim all-lens/device acceptance.

The inherited Photon customCCT.txt parser could partially overwrite its calculated matrix, divide by an unusable reference-point difference, or pass non-finite coefficients to a shader. Cube interpolation also modified Parameters.whitePoint on each call.

This patch parses into a private candidate, validates coefficient counts and finite values, and checks non-negative red/green, positive blue and a finite positive (R+G)/B ratio. Reference ratios separated by no more than eight float ULPs at the larger magnitude are rejected. Interpolated outputs must be finite. A bad candidate falls back to a clone of the already calculated matrix. A missing/unreadable file keeps that same default, and the scanner is closed.

Valid MATRIXES/CUBES are resolved once for the capture white point before publication as MATRIX/CUBE, so shader selection cannot disagree with a later fallback. All production consumers use this resolved object. Cube arithmetic uses local red/blue values with the original double epsilon and final float cast; matrix arithmetic preserves the original double reciprocal and final float cast. No interpolation-weight clamping is introduced; valid extrapolation is preserved.

Scope: three production Java files, version metadata, one updated existing parser fixture (its two cube white points previously had the same ratio), and one new test class. All primary M9/Monochrom renderer, exposure, autofocus, capture, native and asset files are unchanged from 2.89. The primary M9/Monochrom JPEG queues bypass this inherited OpenGL custom-CCT route.

Verification:
- 28 guard tests plus the 5 existing colour tests pass in a JDK host probe (explicit Log/JUnit stubs).
- The probe compiles the original 2.89 classes in a separate namespace and compares 100,000 matrix and 100,000 cube cases by exact float bits, including extrapolation. Cube outputs match the old first call and remain stable over repeated calls, with the input white point unchanged.
- Source reconstruction fingerprint and reverse patch verification pass; 1,367 scoped files are unchanged.
- Android installer gate: 235 selected tests. Broader build/CodeQL gate: 238 selected tests. Remote results are recorded separately after completion.
- Packaging requires every native library and asset to match the verified signed 2.89 APK byte for byte, plus the accepted signing certificate and 16 KiB ZIP alignment.

Reconstruct using `python3 patches/cctguard1a/assemble.py DEST --parent VERIFIED_289`; omitting `--parent` reconstructs the full pinned chain. Source verification: `verify_source.py VERIFIED_289 DEST`. Numeric probe: `host_probe.py DEST VERIFIED_289`.

This is stacked on the v2.89 draft; neither candidate is merged into main by this change. Phone image quality and mode/lens checks remain a separate acceptance step.
