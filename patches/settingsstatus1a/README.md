# M9Cam 2.25 — settings and final-save feedback

Child of phone-accepted 2.24 / remote 6acae30ea44f815a27c0923eed36868d757f57c0.

Photo settings retain the existing Save key and values (JPEG, RAW+JPEG, RAW),
Leica saturation and both output switches. Save moves into Photo settings so an
inherited HDRX setting cannot hide it. HEIC labels are suppressed for M9.
Hidden preference values are preserved; no preference migration or reset occurs.
Unlimited/RAW video retain their inherited settings UI.

A capture-owned status ticket starts at RAW enqueue and finishes after requested
JPEG EXIF, RAW writing, profile embedding, optional unfiltered RAW and gallery
publication attempts. Captures are counted once regardless of selected file count.
Capture rearm remains unchanged. The status survives Fragment recreation and
background/resume within the same process. It is not durable work scheduling or
process-death recovery. Notifications are optional; disabled notification access
cannot break photo saving. Failures remain available in the camera until reviewed.
Successful completion displays briefly. Partial-file and missing-profile failures
are distinguished; existing completed files are retained.

## Traced settings cleanup

| Control | Active M9 finding | UI action |
| --- | --- | --- |
| Frame count | FrameNumberSelector forces one frame for M9 stills | Hidden; explanatory single-exposure summary |
| Save HEIC | M9R35Renderer uses saveBitmapAsJPGPayloadM9 / JPEG quality 95 | Hidden; Save entries always JPEG/RAW |
| Ultra HDR | M9 produces SDR JPEG; gain-map encoder is in the other processor | Hidden |
| HDRX noise reduction, sharpness, contrast, noise strength, merge strength, shadows, compressor, alignment method | Controls feed the legacy HdrxProcessor/PostPipeline; active M9 rendering does not consume these adjustments | Hidden |
| Legacy JPEG/YUV category | DefaultSaver routes M9 RAW directly to M9PrimaryRenderQueue | Hidden as before for the usual HDRX-on state; now deterministic for M9 |
| Save mode | Accepted 2.24 frozen selection | Preserved, moved to Photo settings |
| Leica saturation and optional outputs | Active native/Java/profile/preview and writer paths | Preserved |
| Exposure compensation | IsoExpoSelector reads the preference | Preserved |
| CFA / color method, sensor configuration | Parameters still reads settings before physical authority and calibration | Preserved pending any further cleanup |
| Horizon, preview format, focus, grid, lens bar, theme, backup | Useful inherited controls | Preserved |
| Video settings | Separate submenu/mode | Preserved |

This is a focused traced cleanup, not certification of every dynamically generated
vendor/tunable option. No M9 renderer, preview shader, capture policy, RAW writer,
profile math, saturation engine or native source changes are permitted by this patch.

## Validation

`verify_status.py` executes the production queue and status tracker with controlled
platform/render/storage adapters: the existing 11 mode cases plus 19 completion,
overlap, observer lifecycle, failure, fallback and rejection cases. These are not
physical phone tests. The workflow compiles the full app, retains the accepted
Android regression gates, verifies the entire inherited source manifest and reuses
all accepted 2.23 native binaries (also byte-identical in accepted 2.24).

Phone checks: install over 2.24; verify Medium high and save mode survive restart /
lens switch; take a few quick photos and watch the counter until completion; rotate
and background/resume during saving; review failure messaging if an actual failure
occurs. Do not claim low-storage, lock, all-device or process-death coverage from CI.
