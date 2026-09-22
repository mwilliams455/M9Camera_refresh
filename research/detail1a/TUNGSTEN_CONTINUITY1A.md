# M9TUNGSTENCONT1A — keep TG1 alive through preview source gaps

22 September 2026.

The supplied warm-light recording exposed a preview-only continuity hole. TG1 was still present in the GL2A shader, but the GL2A/GL2F fail-closed source-contract path could temporarily set `source2A.ready=false`. Two independent details then removed the warm-light protection at once:

1. `MainRenderer.bindSource2A()` returned before uploading `uM9Tungsten2A` for a not-ready source.
2. `main_fs.glsl` returned the exposure-adjusted OES fallback before calling `tungsten2A()`.

This was not an intended change to the M9 photographic renderer. The saved-JPEG DETAIL1H path, native detail kernels, SAT2/curve02 assets and exposure allocation remain frozen.

## Candidate

`M9TUNGSTENCONT1A` does three narrow things.

- The raw GL2F source contract remains fail-closed. A new outer continuity helper holds the most recent fully valid source for at most **1000 ms**, and only for the same camera ID.
- TG1 illuminant authority is separated from source-contract readiness. Normal ready frames retain the native GL2A tungsten weight. Held or true fallback frames use the already-live independent illuminant weight carried by `M9PreviewFrameState1W`.
- Once the one-second hold expires, the preview really does fall back to processed OES, but the exposure-adjusted fallback now still passes through the encoded-domain BT.601 `tungsten2A()` guard. SAT2/curve02/source inversion remain bypassed as before.

Diagnostics record whether a frame is held, the underlying contract failure, last-good age, the TG1 authority and the true fallback colour path.

## Successor rule

This overlay is chained directly from `apply-m9cam-m9detail1h.py`. That makes the ISO/noise/sharpness phone candidate the new parent contract: any later app candidate that applies DETAIL1H inherits M9TUNGSTENCONT1A automatically. Do not fork a later phone build from the pre-continuity DETAIL1H output.

The dedicated DETAIL1H workflow compiles the continuity helper, verifies same-camera/timeout behavior, checks the fallback shader call, builds Android and checks the packaged markers. Device validation still has to confirm that the visible warm/cool jumps are gone.
