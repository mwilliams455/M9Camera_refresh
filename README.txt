M9Cam v0.7ZQ PRIMARY2.5 PERF3I BITMAPDIRECT1A + CVDIRECT1A + ORIENTFUSE8A + EXIFASYNC1A + JPEGBUF64K1A + TC20LUMA8A + COLOR8A

Direct derivative of device-validated/promoted v0.7ZP-FIX1 PERF3H CVDIRECT1A.

PERF3I execution change only:
- Keep PERF3H direct OpenCV input and every frozen scalar photographic operation unchanged.
- On the normal path, write completed oriented ARGB pixels directly into the mutable 12 MP ARGB_8888 destination Bitmap using AndroidBitmap_getInfo()/lockPixels().
- Java and native code both validate Bitmap mutability/config/dimensions/stride before direct output.
- Native output uses explicit RGBA bytes derived from the existing Java-style 0xAARRGGBB scalar result.
- If native Bitmap layout/locking is not exactly eligible, return before modifying pixels and use the complete promoted PERF3H int[] -> Bitmap.setPixels fallback for the frame.
- No full-frame intermediate output buffer is introduced.

Quality/parity contract:
- 12 MP 3072x4096 JPEG unchanged.
- JPEG quality remains 95.
- Same Android Bitmap.compress encoder and 64 KiB transport buffer.
- Same EXIFASYNC1A and JPEG-before-DNG publication ordering.
- Same DNGASYNC1A RAW ownership/preservation architecture.
- CVDIRECT1A and ORIENTFUSE8A retained.
- Frozen R3.8 H25/TG1, Cobalt calibration, M9 bridge, TC20 selection/gain math, SAT3 M06/M07, curve02 and exact BT.601 horizontal 4:2:2 unchanged.
- No exposure changes, fast-math, NEON, encoder swap, quality reduction or render-resolution change.

Expected device normal-path diagnostics:
- nativeColorBitmapOutputMode=androidbitmap_rgba8888_direct1a
- nativeColorBitmapDirectEligible=true
- nativeColorBitmapDirectBlocks=8
- nativeColorBitmapFallbackBlocks=0
- nativeColorOutputCopyElapsedMsSum approximately 0
- directOrientedCommitElapsedMs approximately 0
- CVDIRECT1A input diagnostics remain direct/no-fallback.

Do not promote until device JPEGs are visually checked for exact orientation/channel correctness and JSON confirms JPEG/DNG/EXIF/queue health.
