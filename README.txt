M9Cam 2.67 REGIONALCLIP1A — stabilize release of regional clipping limits

The matching 09:48 TV-room trace isolates repeated regional clipping cuts while tone gain stays at unity and reference exposure stays nearly constant. A change from two to three clipped pixels in a 30-pixel region can trigger a quarter-stop cut.

This candidate retains each triggered regional clipping field until clipping clears by more than one sampled pixel. Existing entry thresholds and immediate safety cuts remain unchanged. Baseline exemptions alone cannot release an already-triggered field. The prior exposure/tone settling remains in place.

The exact reconstructed candidate passes 4,875 inherited and 284 new host assertions, Android build and packaged APK checks. The isolated recorded-boundary regression changes eight repeated cuts/rises into one initial cut with no subsequent cycle, and genuine clearance restores recovery. This uses synthetic missing bracket steps and timing; phone validation remains pending. Near-threshold scenes can remain conservatively darker.

Start here:
- patches/regionalclip1a/README.md — behavior, limits, phone check and reproduction
- patches/regionalclip1a/HOST_VERIFICATION.json — unchanged inherited checks
- patches/regionalclip1a/REGIONAL_VERIFICATION.json — new regression checks
- patches/regionalclip1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/regionalclip1a/RECORDED_EVIDENCE.json — 2.66 matched-trace findings
- patches/regionalclip1a/FIXTURE_PROVENANCE.json — replay limitations
- patches/regionalclip1a/assemble.py — pinned source reconstruction
- patches/regionalclip1a/PACKAGED_VERIFICATION.json — signed APK verification

This is an incremental source-recovery repository, not an assembled Android project.
Parent: 2.66 at 444c246a5e2f714aa88e4a820f0a12c8b4091f42, draft PR #84.
Candidate: M9Cam_2.67_REGIONALCLIP1A.apk. Main remains unchanged.
