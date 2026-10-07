M9Cam 2.61 PREVIEWBRIDGE1A — bound temporary exposure-reference mismatches

The latest woodland recording shows substantial brightness pumping. A production-controller reproduction identifies one possible contributor: a 0.30 EV movement of the camera's metering reference can immediately erase an accepted +1.75 EV correction, then cycle between +0.75 EV and zero as probes match and mismatch.

The candidate retains a recent validated exposure through a small reference mismatch for at most 500 ms and 0.5 EV. Its temporary correction never exceeds the accepted correction or accepted absolute exposure energy. The accepted baseline is preserved; duplicate reads cannot renew the deadline or ratchet it. Fresh highlight warnings and larger, stale, invalid or foreign changes still take effect immediately. This is a demonstrated source fix, not proof that every phone fluctuation has the same cause.

Candidate host checks pass: 2,414 assertions through complete production Auto/tap classes. Only Auto continuity and version metadata change; all other 1,330 scoped files match 2.60. Continuous Picture, colour, WB, tone curves, JPEG/DNG rendering, native assets, Monochrom, frame pairing, TC20, ISO allocation, AE-L and queue fixes are unchanged. Captures during the short transition follow the displayed exposure plan.

Start here:
- patches/previewbridge1a/README.md — evidence, limits, build instructions and phone comparison
- patches/previewbridge1a/HOST_VERIFICATION.json — production controller results
- patches/previewbridge1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/previewbridge1a/assemble.py — pinned source recovery
- patches/previewbridge1a/PACKAGED_VERIFICATION.json — final APK checks

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.61_PREVIEWBRIDGE1A.apk.
Parent: 2.60 at d309662ccaed319174dcd3f05e0e4be0c1145a12, draft PR #78. Phone validation is pending. Main is unchanged.
