M9Cam 2.66 EXPOSURESETTLE1A — coordinate settled exposure increases and preserve short-gap tone continuity

The user's 2.65 test still pumps with changing TV content. Its trace shows subject/scene ownership changes, real highlight-ceiling cuts and preview tone variation/resets. Anchor and background caps are nonbinding in this instance. A sampled 0.673-EV app-gain reduction occurs while hardware exposure and the incoming crop's green median stay unchanged.

This candidate requires four fresh probes over at least 750 ms before settled Auto placement or preview tone can brighten. Auto/user EV changes interrupt pending tone rises. Short, bounded metadata gaps preserve qualified tone instead of immediately resetting it. Current hard clipping cuts remain immediate. The existing trace now retains the field measurements explaining each highlight decision.

The exact reconstructed candidate passes 4,875 host assertions, Android build and packaged APK checks. Phone validation remains pending; deliberate slower brightening and transient preview/JPEG agreement need testing. No HDR or stacking is introduced.

Start here:
- patches/exposuresettle1a/README.md — behavior, limits, phone check and reproduction
- patches/exposuresettle1a/HOST_VERIFICATION.json — production controller and history checks
- patches/exposuresettle1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/exposuresettle1a/RECORDED_EVIDENCE.json — 2.65 failure evidence and analysis limits
- patches/exposuresettle1a/TONE_REPLAY.json — bounded tone-only replay, not a full scene replay
- patches/exposuresettle1a/assemble.py — pinned recovery with complete source fingerprints
- patches/exposuresettle1a/PACKAGED_VERIFICATION.json — signed APK verification

This is an incremental source-recovery repository, not an assembled Android project.
Parent: 2.65 at 78a0669eec8c81f1de0f08fd1f2d9cbc63164f76, draft PR #83.
Candidate: M9Cam_2.66_EXPOSURESETTLE1A.apk. Main remains unchanged.
