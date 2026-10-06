M9Cam 2.57 PREVIEWPROBE1A — M9 preview probe scheduling candidate

The Auto exposure readback could repeatedly resubmit before the preview brightness probe had a turn during slow frames or GPU readbacks. The Auto probe now yields its completion frame. Existing single-readback scheduling, metering policy and freshness rules remain intact.

Host tests reproduce starvation in 2.56 and show both probes progressing in 2.57. Normal-frame-rate controls and manual EV are unchanged. Very slow frames can still trigger the existing stale-brightness reset, so this is a focused test candidate, not a claim that all phone flicker is fixed.

Only one probe source file and app version metadata change. Saved JPEG/DNG processing, Monochrom, queues and crash fixes are byte-identical to 2.56. The user reported 2.56 rendering faster and saved images good; 2.57 needs phone validation.

Start here:
- patches/previewprobe1a/README.md — diagnosis, limitations, recovery and phone comparison
- patches/previewprobe1a/HOST_VERIFICATION.json — actual probe and scheduler regression results
- patches/previewprobe1a/SOURCE_VERIFICATION.json — source boundaries
- patches/previewprobe1a/assemble.py — complete pinned source reconstruction
- patches/previewprobe1a/PACKAGED_VERIFICATION.json — native/assets/signature integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.57_PREVIEWPROBE1A.apk.
Parent is 2.56 at 15fcb07fae6e2aa6ca4149dc2e190731a72379bc, including the shading speed improvement in PR #74. Main remains accepted 2.55 at e8b1a4979cc9e20237b1d42a66037a006f127b85 until requested merge.
