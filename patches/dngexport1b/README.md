# M9Cam 2.12 DNGEXPORT1B

PERF2S's native DNG serializer emitted WhiteLevel as TIFF RATIONAL, although
the DNG specification permits SHORT or LONG. Odd-length payloads could also
leave metadata or IFD offsets unaligned. The Java writer imported a third-party
widget's BuildConfig, making the Software tag identify the wrong version.

This patch writes integral WhiteLevel values as LONG, rejects invalid inputs,
aligns external TIFF values and RAW strips to two bytes, and reports the app's
own version. The CMake dependency pin is updated to the verified writer hash. Padding is excluded from strip byte counts. The historical
SetWhiteLevelRational method name remains for source compatibility.

No Bayer sample arithmetic, gain-map values, colour matrices, WB, black/white
numeric values, exposure, JPEG rendering or preview logic is changed. This is
an export correctness step in the firmware-led DNG audit, not M9 sensor
emulation or an image-quality/fringing fix. The accepted PERF2S branch remains
the control. Phone validation is required before promotion.

The host test compiles the production C++ serializer and independently reads
the resulting files with tifffile: four CFA layouts, full-range RAW16 sample
preservation, neutral/black metadata, odd payloads, multiple IFDs, and invalid
WhiteLevel values. The pre-patch writer reproduces the type/alignment defects.
Host tests do not execute Android JNI or Camera2.

Build: `python3 patches/dngexport1b/assemble.py PhotonCamera`, then follow the
dedicated workflow. Packaging preserves all accepted PERF2S native libraries
except the rebuilt libdngCreator.so, and all M9 assets. The source manifest
checks the exact inherited files and five overrides (four changed files; version.properties is retained).

`repair_export.py SOURCE OUTPUT` is an optional offline metadata-only test
converter for single-IFD, uncompressed RAW16 DNGs. It refuses overwrite, retains
RAW and other tag values, and validates the result before writing. Its Software
tag identifies an offline repair. No user photos or capture-derived fixtures
are committed here.

References:
- Adobe DNG 1.7.1, WhiteLevel (tag 50717), SHORT or LONG:
  https://helpx.adobe.com/content/dam/help/en/photoshop/pdf/DNG_Spec_1_7_1_0.pdf
- TIFF 6.0, word-aligned IFD/value offsets (DNG uses TIFF structure).
- Android Camera2 lens-shading map documentation: the live map describes
  remaining correction when lensShadingApplied is true. It is retained.
