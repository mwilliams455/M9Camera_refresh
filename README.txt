M9Cam 2.55 THUMBUI1A — gallery-thumbnail thread crash fix candidate

The new logcat identifies a gallery thumbnail completing on AsyncTask and triggering lens animations off the UI thread. The regression reproduces that failure against unchanged 2.54 production code. 2.55 starts thumbnail requests on main, rejects obsolete work, owns/releases the Glide target and retires lens model observers with their views. Phone confirmation is pending.

All photographic rendering, exposure, JPEG/DNG saving, native libraries and assets are unchanged. The 2.54 redraw fix, 2.53 JPEG-only queue improvement and 2.52 RAW fix remain included. Lens-shading optimisation is paused until crash testing is complete.

Start here:
- patches/thumbui1a/README.md — logcat cause, scope, recovery/build and phone retest
- patches/thumbui1a/LOGCAT_EVIDENCE.json — relevant M9 crash stack
- patches/thumbui1a/PARENT_REPRODUCTION.json — failing cached-thumbnail case against 2.54
- patches/thumbui1a/TEST_VERIFICATION.json — 44 app tests, including seven thumbnail and five lifecycle cases
- patches/thumbui1a/SOURCE_VERIFICATION.json — photographic/save code preserved
- patches/thumbui1a/assemble.py — reconstruct the complete pinned source chain
- patches/thumbui1a/PACKAGED_VERIFICATION.json — signed APK integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate: M9Cam_2.55_THUMBUI1A.apk.
Main remains the phone-confirmed 2.52 baseline at 5d8994f0266557747d1120764a88edd2f88d3ca4. This stacks on 2.54 draft PR #72 and 2.53 draft PR #71; 2.53 three-shot admission/recovery was confirmed on the phone before the crash investigation.
