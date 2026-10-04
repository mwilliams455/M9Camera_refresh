# COLOURTRIAL1C — Android validation APK

Version `1.65-m9colourtrial1c-tg1`, code `26685`, package
`com.m9project.m9cam.photon`. Built from the exact SHUTTERTRACE1B/TG1 source.
The dedicated workflow builds and signs both existing ARM ABIs with the existing
update certificate. It does not merge this candidate into the main branch.

## Selected working balance

1. Existing single-RAW normalization and NORM030 shading.
2. Same-phase RAW noise proposal, blended at exactly 25%. Physical black/white
   censored samples and the six-pixel noise border remain unchanged. Variance
   uses the unscaled fresh Camera2 CFA-position noise profile plus quantization,
   propagated through the exact shading grid and representation scale. Missing
   or invalid variance inputs bypass this correction; complete AMaZE still runs.
3. Complete AMaZE at pinned librtprocess revision
   `9a858270acb2096e2e403d932760ee688fcac425`. Original upstream sources and
   GPL notices are vendored unchanged. The 16-pixel outer RGB border uses true
   no-Sharp MHC on the original normalized RAW, matching the selected experiment.
4. Existing camera/target transform, identity HSM and gain decisions, then 25%
   directional chroma correction in target Q14 immediately before SAT. Overlapped
   bands provide full-frame spatial support; physical border is unchanged.
5. Existing SAT2, curve02, source-horizontal BT.601 4:2:2, TG1 and orientation.

No Leica green replacement, old final Sharp, clipped-ratio highlight repair or
full-strength RAW correction is active on the production path. Explicit legacy
forensic modes remain separate controls. No JPEG/Exif/DNG writer, capture request,
preview shader, target asset or tungsten policy is changed.

## Auto exposure — highlight protection

The [Auto policy](../colourtrial1a/README.md) caps total positive automatic bias,
including an inherited positive baseline, by the last consecutive bracket inside
the existing processed-preview clipping and broad-brightening budget. Missing,
stale, invalid or foreign samples cannot justify positive assistance. Explicit
user EV and manual ISO/shutter keep their established authority. Negative
baselines remain valid; rise is limited to a quarter stop per fresh sample and
unsafe positive assistance releases immediately.

This is preview-based highlight protection, not a guarantee of RAW channel
headroom and not reconstruction of already clipped colour.

## Integration and validation

`apply.py PhotonCamera` requires the complete exact SHUTTERTRACE1B source proof,
checks all anchors, records before/after inventories and is idempotent. Existing
assets, capture, Exif and preview sources stay byte-exact except the named Auto
policy. The source proof is included with the build artifact.

Host gates compile the actual native Android translation unit and real Java/JNI
helper with small Android platform stubs. They cover all four CFAs and four crop
origins, the physical variance/censor formula, invalid/missing-profile bypass,
quarter blending, one/four-worker equality, full-frame versus overlapped bands,
SAT2/3/4 integer parity, TG1, odd widths, four orientations and direct Bitmap versus
int[] fallback. The 21 actual-source Auto policy checks also run. Parent diagnostic
and exposure gates run before applying the candidate.

Android packaging checks verify both native ABIs, candidate entry points, Auto
marker, unchanged shader/curve, TG1, trace recorder, version, signature and 16KB
ZIP alignment. Host equality is not a claim of cross-architecture floating-point
identity: upstream AMaZE has SSE on x86 and scalar code on ARM. Phone cadence,
memory use, Auto transitions and photographic acceptance remain device checks.

Per-capture `colourTrial1C` metadata records the active path, actual RAW correction
state, reason, strengths, CFA/origin and timing. The SHUTTERTRACE1B recorder remains
available. Private-photo evidence is kept outside the public repository.
