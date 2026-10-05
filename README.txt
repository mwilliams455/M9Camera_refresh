M9Cam 2.53 JPEGQUEUE1A — M9 JPEG-only save queue test candidate

2.52 is the phone-confirmed main baseline: the RAW profile fix works and rendering is faster. PRs #67–#70 were merged into main at 5d8994f0266557747d1120764a88edd2f88d3ca4.

This candidate releases the M9 JPEG-only render worker while EXIF and gallery publication finish on the existing bounded background worker. Save status remains pending until finalization completes. Full queues retain the synchronous preservation fallback. Image processing, JPEG quality, native libraries and assets are unchanged; RAW modes and Monochrom retain their established routing.

Start here:
- patches/jpegqueue1a/README.md — behaviour, validation limits, recovery/build, phone checks
- patches/jpegqueue1a/assemble.py — reconstruct complete source from pinned parent chain
- patches/jpegqueue1a/QUEUE_VERIFICATION.json — 13 queue/failure scenarios plus 250 rapid callbacks
- patches/jpegqueue1a/SOURCE_VERIFICATION.json — photographic code and DNG path preservation
- patches/jpegqueue1a/TEST_VERIFICATION.json — 34 app regressions
- patches/jpegqueue1a/PACKAGED_VERIFICATION.json — signed APK identity/integrity

This is an incremental source assembly/recovery repository, not an already-assembled Android project. Build candidate: M9Cam_2.53_JPEGQUEUE1A.apk. Phone validation is pending; main remains the accepted 2.52 baseline until the candidate is reviewed.
