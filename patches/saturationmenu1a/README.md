# M9Cam 2.22 — Leica M9 saturation menu

Adds **Settings → Photo settings → Leica M9 saturation** with Low, Medium low,
Standard, Medium high and High. Standard remains the installation/upgrade default.
The choice persists globally across lenses. The old generic saturation slider is
replaced so there is one saturation control for the M9 route.

The five levels select the recovered M9 1.216 sRGB matrices M00/M01 through M08/M09;
they are not generic saturation percentages. `firmware_saturation.json` records the
exact signed Q13 coefficients, LUT offset and SHA-256. The established selector
proof is in `forensics/M9_FIRMWARE_RENDER_STATE_MODEL_v1.json`.
The English names match the [Leica M9 manual](https://leica-camera.com/sites/default/files/pm-29379-Leica-M9-M9-P_Instructions_DE-EN.pdf).

The selection is frozen when a RAW frame enters the render queue, and the DNG
profile reads that frame's frozen renderer result. Preview reads the current
selection on each GL draw. JPEG, Java fallback and preview use the selected matrix
pair before the unchanged curve02 lookup. DNG profiles retain their existing
approximation and spatial-shading limitations. Unfiltered diagnostic DNGs continue
to contain physical RAW without the embedded M9 look.

Capture requests, RAW samples, source calibration, metering, tone curve, sRGB,
demosaic and existing sharpening are unchanged. This is a colour preference, not
a fix for magenta fringes. No HDR, stacking or device-specific calibration is added.

Validation:

- Production native and DNG sampler: 81,390 synthetic samples per level against
  the recovered firmware arithmetic, including both branches, clipping and neutrals.
- Standard's full 180×65×129 DNG look table and 129-point tone curve are byte exact
  against the accepted pre-menu implementation.
- Full production preview shader compiled on Mesa GLES; 256 pixels per level
  matched the firmware result exactly (`verify_preview.py`, separate host check).
- Existing DNG profile/storage, RAW-pair, metadata and request-isolation gates retained.
- Android preference tests cover all levels, live changes, missing/corrupt preferences
  and immutable firmware coefficient copies.

The package rebuilds only the two ARM `libm9color.so` binaries and preserves the
other 21 native entries and six M9 assets from accepted 2.16. Source hashes, 16 KB
alignment, signing certificate and version 27222 are checked before delivery.
Handset installation and visual confirmation remain necessary.
