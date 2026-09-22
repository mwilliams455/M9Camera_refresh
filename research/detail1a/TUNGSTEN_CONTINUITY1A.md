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


## 22 September follow-up video 41117.mp4 — state/texture pairing

The continuity APK removed the known source-not-ready hole but did not remove the
reported live-view flicker. The recording is stronger evidence than another TG1
strength adjustment. The HUD remains in the fully warm-light region (roughly
2400–2800 K), so the 4500 K -> 3200 K TG1 ramp should already be saturated.

A particularly useful interval is about 24.83–24.87 s: the HUD remains
1/15 s, ISO 175, AWB 2600 K and AF-C LOCK while the viewfinder changes abruptly.
The next displayed hardware pair, 1/29 s at ISO 369, differs in exposure energy
from 1/15 s at ISO 175 by only about +0.125 EV. That is insufficient to explain
the larger transient viewfinder step. This falsifies "TG1 weight ramp" as the
primary flicker explanation and points to asynchronous OES/metadata state.

GL1W made each published preview state internally atomic but explicitly did not
pair the state to the SurfaceTexture timestamp. `M9PREVIEWPAIR1A` closes that
gap: result states are queued by `SENSOR_TIMESTAMP`; a draw selects only a state
within 5 ms of the current OES texture timestamp. If the matching CaptureResult
has not arrived yet, the draw is deferred for up to 120 ms, leaving the previously
presented frame on screen. Only after that bounded interval does portability
fallback use the latest state. Pairing decisions and timestamp deltas are added
to `shutterPreview1W.stateTexturePair1A`.

TG1 coefficients are deliberately unchanged in this candidate. First establish
that the correct metadata is being applied to the correct OES pixels. If a
timestamp-paired 2400–2800 K view remains too warm without flicker, TG1 strength
or domain can then be evaluated independently rather than compensating for a
transport race.
