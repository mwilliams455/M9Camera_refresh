M9Cam 2.63 PREVIEWRECOVER1B — sustain conservative recovery after exposure reductions

The recovered phone trace shows a 1.5-EV M9 correction drop in 266 ms while sensor energy changes only 0.026 EV and focus remains stationary. It also shows the rapid recovery pattern allowed by 2.62: after the first confirmed quarter-stop rise, the guard is cleared and fast acquisition resumes.

This candidate keeps all post-cut rises at 0.25 EV per fresh probe until the target is reached and four fresh probes agree over at least 750 ms. Protective cuts and all targets/limits are unchanged. Stable final exposure is unchanged; transient captures follow the slower displayed recovery. Crop diagnostics now retain actual tone gain and draw snapshots include the existing Auto reason.

Complete production Auto/tap tests pass 2,852 assertions. A synthetic reproduction changes the old recovery [0.5, 0.75, 1.5, 2.0] to [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0], with unchanged immediate safety cuts. All other 1,327 scoped source files match 2.62. Reconstruction, Android build and signed APK checks pass. Native libraries and assets remain byte-identical.

Start here:
- patches/previewrecover1b/README.md — evidence, limits, test and build instructions
- patches/previewrecover1b/TRACE_ANALYSIS.json — measured timeline and diagnostic limitations
- patches/previewrecover1b/HOST_VERIFICATION.json — parent/candidate production-controller results
- patches/previewrecover1b/SOURCE_VERIFICATION.json — exact source boundaries
- patches/previewrecover1b/assemble.py — pinned source recovery
- patches/previewrecover1b/PACKAGED_VERIFICATION.json — final APK verification

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate: M9Cam_2.63_PREVIEWRECOVER1B.apk.
Parent: 2.62 at 36cf2726c96cf2b03afd7f2016d6565d85b21cb2, draft PR #80. Main remains unchanged. Phone validation is pending; the exact changing cap behind every pulse is not yet known. Pre-shutter AF CANCEL repetition is recorded separately for follow-up; Continuous Picture AF is unchanged here.
