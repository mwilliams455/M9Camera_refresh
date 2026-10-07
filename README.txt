M9Cam 2.60 PREVIEWRECOVER1A — confirm recovery after protective exposure cuts

Outdoor phone testing still shows brightness swings when panning near the sun. Source tests reproduce a controller rebound: a protective headroom cut can be undone by the next permissive probe. This candidate keeps the cut immediate, then requires two consecutive fresh probes supporting a rise and bounds the first recovered step to a quarter-stop.

Candidate host checks pass: 1,772 checks through the complete production Auto/tap classes. In the synthetic mapped backlit case, alternating permissive/restrictive probes no longer cause repeated +0.5-to-+1.25 EV rebounds. Sustained safe evidence reaches the same +1.75 EV target. These are synthetic controller checks, not phone validation or proof that every observed swing has the same cause.

Only Auto recovery timing and version metadata change. All exposure targets and highlight budgets remain intact. Saved JPEG/DNG processing, colour, WB, shaders, native sources/assets, Monochrom, frame pairing, ISO allocation, AE-L and queue fixes remain unchanged. Captures during recovery continue to follow the displayed exposure plan.

Start here:
- patches/previewrecover1a/README.md — evidence, behavior, trade-off and phone comparison
- patches/previewrecover1a/HOST_VERIFICATION.json — production controller results
- patches/previewrecover1a/SOURCE_VERIFICATION.json — source boundaries
- patches/previewrecover1a/assemble.py — pinned source recovery
- patches/previewrecover1a/PACKAGED_VERIFICATION.json — final APK integrity checks

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.60_PREVIEWRECOVER1A.apk.
Parent is 2.59 at cced095b9134255fa7883584a7ba186a77d81a70, draft PR #77, retaining its predecessors. Full Android build and package checks passed. Phone validation is pending. Main is unchanged.
