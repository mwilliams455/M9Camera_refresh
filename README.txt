M9Cam 2.54 SWITCHVIEW1A — camera-view redraw crash fix candidate

An old pre-draw callback could reach a cleared CameraFragmentBinding after switching render modes. The supplied historical crash stack was reproduced against 2.53 production code. 2.54 retires panel callbacks at view destruction and removes the listener from the exact attached window observer. Phone confirmation is pending; the historical report does not establish the cause of every recent exit.

All rendering, image quality, exposure, JPEG/DNG saving, native libraries and assets are unchanged. The 2.53 JPEG-only queue improvement and 2.52 RAW fix remain included. Lens-shading optimisation is paused until crash testing is complete.

Start here:
- patches/switchview1a/README.md — evidence dates, cause, scope, recovery/build and phone retest
- patches/switchview1a/PARENT_REPRODUCTION.json — exact failing case against 2.53
- patches/switchview1a/TEST_VERIFICATION.json — 36 app tests, including four lifecycle cases
- patches/switchview1a/SOURCE_VERIFICATION.json — photographic/save code preserved
- patches/switchview1a/assemble.py — reconstruct the complete pinned source chain
- patches/switchview1a/PACKAGED_VERIFICATION.json — signed APK integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate: M9Cam_2.54_SWITCHVIEW1A.apk.
Main remains the phone-confirmed 2.52 baseline at 5d8994f0266557747d1120764a88edd2f88d3ca4. Parent 2.53 is draft PR #71; its three-shot admission/recovery was confirmed on the phone before the mode-switch crash investigation.
