M9Cam 2.58 PREVIEWPAIR1A — M9 preview frame/metadata pairing candidate

The viewfinder could apply the newest exposure metadata to pixels from an older camera frame during Auto ISO/shutter changes. This candidate uses bounded exact timestamp matching, sharing the selected state between rendering, metering and the existing Draw/shutter path. Missing or expired matches keep the parent fallback. Exposure targets, highlight safety and freshness rules are unchanged.

The user reported 2.57 improved the viewfinder, but a backlit scene still showed abrupt darkening. Host tests reproduce a metadata-pairing brightness error and verify the fix in 112 synthetic exposure cases with 272 assertions. These are not phone measurements; existing stale-meter and brightness reset paths remain.

Only MainRenderer, one new metadata-history class and version metadata change. Saved JPEG/DNG processing, native libraries, assets, Monochrom, save queues and recent crash fixes remain unchanged from 2.57. Full Android build and packaged APK integrity checks passed. Phone validation is pending with AE-L off and the usual Auto ISO limit restored.

Start here:
- patches/previewpair1a/README.md — diagnosis, limitations, recovery and phone comparison
- patches/previewpair1a/HOST_VERIFICATION.json — production class regression results
- patches/previewpair1a/SOURCE_VERIFICATION.json — source boundaries
- patches/previewpair1a/assemble.py — complete pinned source reconstruction
- patches/previewpair1a/PACKAGED_VERIFICATION.json — native/assets/signature integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.58_PREVIEWPAIR1A.apk.
Parent is 2.57 at 5807641762f5023a64ef7b846670b0b5b0a777a6, including PR #75 and the rendering speed improvement in PR #74. Main remains accepted 2.55 at e8b1a4979cc9e20237b1d42a66037a006f127b85 until requested merge.
