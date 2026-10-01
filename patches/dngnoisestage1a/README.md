# M9 DNGNOISESTAGE1A — Android test build 2.15

Adds the validated shading-aware RAW noise adapter to the M9 physical single-RAW DNG export. The accepted JPEG source, assets and existing native libraries are retained. The new `libm9dngnoise.so` is isolated from the JPEG renderer.

- Mode 1, strength k=1: recovered same-phase [1,2,1] horizontal/vertical integer pass order, with Camera2 variance thresholds in the virtually shaded domain. This is a phone-calibrated experiment, not a bit-exact Leica threshold/ISO implementation.
- Transfer only the filtered residual back through the gain, preserving the original shading fraction. Black/white-censored support, projected clipping and borders remain unchanged.
- RAW stays uncompressed 16-bit Bayer. A power-of-two encoding expansion uses up to a 14-bit numeric range (10-bit white 1023 becomes 16368; black 64 becomes 1024). This adds processing precision, not captured sensor precision. No nonlinear 8-bit M9 encoding.
- Native processing uses a separate output and temporary expanded source. The original owned RAW remains the JPEG source. Peak additional working memory is approximately 60 MB at 12 MP; handset timing remains to be measured.
- Require genuine capture noise pairs and the exact capture gain map written by DngCreator. Map Camera2 R/G-even/G-odd/B channels to physical Bayer positions for all four CFAs. Require proven full-frame geometry and integer black levels. Unsupported crop, range, calibration, unavailable native library or allocation failure retains the existing original RAW and original optional NoiseProfile.
- Applied output omits NoiseProfile because residual noise calibration is unknown. NoiseReductionApplied is omitted, whose DNG default is 0/0 (unknown). BaselineExposure remains -0.5 EV; phone matrices, white balance, physical ISO and gain map remain unchanged.
- Diagnostics distinguish original source handoffs from actual DNG writer input/return hashes. `renderer.photonBoundary2Q.dngNoiseStage` reports applied/bypass reason, scale, timing and writer-buffer equality. The source noise pairs remain in `dngNoiseProfile`; applied output records profile omission explicitly.

Validation: independent NumPy reference, clipping/phase/rounding regression suite, native adapter tests across four CFAs and 8/10/12/14-bit source ranges, real host JNI round trip, Java ownership/fallback tests, and production TIFF serializer tests. Packaging verifies all previous native entries and M9 assets are byte-identical to 2.14, checks both new ABI exports/16 KB ELF alignment, APK signature, package/version and pinned source hashes.

Build from an empty destination with `python3 patches/dngnoisestage1a/assemble.py PhotonCamera`. The dedicated workflow runs verification, builds and signs version 27215 using the established test key. Camera/Android execution, memory pressure and RAW-editor defaults after NoiseProfile omission require handset validation. Public tests use synthetic data only.
