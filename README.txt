M9Cam 2.55 THUMBUI1A — accepted baseline

The logcat identified a gallery thumbnail completing on AsyncTask and triggering lens animations off the UI thread. The regression reproduces that failure against unchanged 2.54 production code. 2.55 starts thumbnail requests on main, rejects obsolete work, owns/releases the Glide target and retires lens model observers with their views. On 5 October 2026, Malcolm reported that he could not reproduce the bug in 2.55 and authorised merging into main. This confirms the reported phone retest; it does not establish that every possible crash is resolved.

All photographic rendering, exposure, JPEG/DNG saving, native libraries and assets are unchanged by 2.55. The 2.54 redraw fix, 2.53 JPEG-only queue improvement and 2.52 RAW fix remain included. Lens-shading correction is the next planned task.

Start here:
- patches/thumbui1a/README.md — logcat cause, scope, recovery/build and phone retest
- patches/thumbui1a/LOGCAT_EVIDENCE.json — relevant M9 crash stack
- patches/thumbui1a/PARENT_REPRODUCTION.json — failing cached-thumbnail case against 2.54
- patches/thumbui1a/TEST_VERIFICATION.json — 44 app tests, including seven thumbnail and five lifecycle cases
- patches/thumbui1a/SOURCE_VERIFICATION.json — photographic/save code preserved
- patches/thumbui1a/assemble.py — reconstruct the complete pinned source chain
- patches/thumbui1a/PACKAGED_VERIFICATION.json — signed APK integrity

This is an incremental source assembly/recovery repository, not an assembled Android project. Accepted APK: M9Cam_2.55_THUMBUI1A.apk.
Main includes 2.53 save-queue PR #71, 2.54 redraw PR #72 and 2.55 thumbnail PR #73. Three-shot admission/recovery and the 2.55 crash retest were confirmed on the phone. Build-time verification reports remain unchanged; their pending-phone-validation fields describe the state when the APK was packaged.
