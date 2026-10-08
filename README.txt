M9Cam 2.65 ANCHORSETTLE1A — stabilize open-anchor classification separately from clipping limits

The latest October 8 trace shows two half-stop Auto cuts caused by the open-anchor rule while the qualified background allowance stays unchanged. The TV also changes actual room light. This candidate addresses the remaining abrupt scene-classification cut while preserving responses to real exposure and tone evidence.

Open-anchor appearance, disappearance and tier changes now require four fresh, spatially coherent probes over at least 750 ms. Semantic decreases use the existing quarter-stop settling path; actual headroom/highlight protection remains immediate. The trace records raw/qualified anchor caps, masks and confirmation state.

Full controller/qualification/history tests pass 4,111 assertions. A synthetic threshold sequence based on the actual shutter bracket holds +0.50 EV where 2.64 pulses between +0.25 and +0.50. Sustained changes still settle to the existing final target. Phone validation remains pending.

Start here:
- patches/anchorsettle1a/README.md — evidence, limits, phone check and reproduction
- patches/anchorsettle1a/HOST_VERIFICATION.json — production controller and history checks
- patches/anchorsettle1a/SOURCE_VERIFICATION.json — exact source boundaries
- patches/anchorsettle1a/RECORDED_EVIDENCE.json — observed cuts and analysis limits
- patches/anchorsettle1a/assemble.py — pinned recovery with complete source fingerprints
- patches/anchorsettle1a/PACKAGED_VERIFICATION.json — signed APK verification

This is an incremental source-recovery repository, not an assembled Android project.
Parent: 2.64 at 3e471d95860e0434ec1db051ee902782fd98fb70, draft PR #82.
Candidate: M9Cam_2.65_ANCHORSETTLE1A.apk. Phone validation is pending. Main remains unchanged.
