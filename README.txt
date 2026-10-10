M9Cam 2.64 BACKGROUNDSETTLE1A — stabilize background qualification separately from clipping limits

The October 8 trace shows app exposure moving while the sensor reference stays nearly constant. The complete shutter bracket also shows a background allowance dominated by a small TV field: one fewer clipped sample can change its raw cap by a quarter stop. Previously that semantic change received an immediate safety cut.

This draft requires four fresh, consistent probes over at least 750 ms before changing the background allowance. Background-only decreases then settle in quarter-stop steps. Actual headroom/highlight protection remains immediate. Separate bounded Auto and tone histories explain target changes and freshness resets in the next shutter trace.

Full controller/qualification/history tests pass 3,622 assertions. A synthetic sequence based on the recorded room holds +1.75 EV, where 2.63 moves between +1.0 and +1.5 EV. Sustained changes still settle to the existing final target. This does not prove phone stability or identify every source of the observed pumping.

Start here:
- patches/backgroundsettle1a/README.md — evidence, limits, phone check and reproduction
- patches/backgroundsettle1a/HOST_VERIFICATION.json — production controller and history checks
- patches/backgroundsettle1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/backgroundsettle1a/BASELINE_RECOVERY.json — two stale local files restored from the unchanged source chain
- patches/backgroundsettle1a/assemble.py — pinned recovery with complete source fingerprints
- patches/backgroundsettle1a/PACKAGED_VERIFICATION.json — signed APK verification

This is an incremental source-recovery repository, not an assembled Android project.
Parent: 2.63 at 36f57c9d0013d2b1eb34a94d9121d939fc517005, draft PR #81.
Candidate: M9Cam_2.64_BACKGROUNDSETTLE1A.apk. Phone validation is pending. Main remains unchanged.
