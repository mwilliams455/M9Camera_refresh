# M9Cam 2.20 CAPTUREREQUEST1A

The RAW checksum boundary starts after the camera delivers its buffer. It cannot
establish which vendor processing was requested or reported before delivery.
This diagnostic records that evidence and adds a narrow capture-policy comparison.
It is not a demonstrated fringe fix.

Advanced settings contains **RAW capture comparison B**, off by default. Off
preserves the existing still policy. On changes only the `burst` argument supplied
to the unchanged Photon `VendorTagUtils.builderSessionApply` helper for ordinary
M9 single stills. This omits its three automatic remosaic assignments. Client name,
maximum-resolution flag, template defaults and per-sensor tunable keys remain.
Omission does not guarantee that hardware remosaicing is off; custom tunables may
still request it. The setting is latched once at request construction.

The completed request/result, builder values around the vendor helper, relevant
available modes/key names, tunable configuration and configured session evidence
are attached as `renderer.captureRequest1A` in the usual PRIMARY JSON. Missing or
error values remain explicit. Physical builder values use the public Builder API;
physical result metadata is recorded when exposed. Target names are app-declared
from the capture branch, not claimed as independent HAL observations.

Correlation uses exact RAW/result timestamps and immutable JSON. A bounded store
holds at most 16 records, each at most 196608 characters; duplicate timestamps are
marked ambiguous. Missing/mismatched records never infer a policy from the current
setting. Session records use weak session keys. No additional RAW frame or pixel
copy is created. Diagnostic failures do not reject photographs.

The main JPEG renderer, native libraries/assets, physical colour export, normal
DNG filter/profile and original-buffer RAW pair are retained from 2.19. Packaging
keeps the accepted 2.16 native binaries and verifies the complete expected source
manifest and final signed payload. `verify_pair.py` is the inherited 2.19 synthetic
gate with the expected version and host-probe path updated for this release.

Build via `.github/workflows/build-m9cam-capturerequest1a.yml`, branch
`research/m9-capturerequest1a`. Package/version: `com.m9project.m9cam.photon`,
`2.20-m9capturerequest1a`, 27220.

For handset comparison, retain one scene, lens and framing with fine foliage
against sky. Fix ISO, shutter and focus where possible; keep WB and all render
settings unchanged. Capture A (switch off), B (on), A (off). Do not move the phone
or compare changing light. Save each JPEG, DNG, RAW_UNFILTERED DNG and PRIMARY JSON.
The metadata must establish whether the intended request difference occurred and
whether exposure/focus were comparable before interpreting any fringe difference.
The exposures remain separate single frames; no HDR, stacking or blending.

Private capture data and photo-derived measurements are excluded from this patch.
