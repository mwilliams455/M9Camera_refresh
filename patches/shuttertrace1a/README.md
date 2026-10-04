# M9SHUTTERTRACE1A — one capture across preview, JPEG and gallery

This diagnostic is based on the accepted **DETAIL1H / TG1ROLLBACK1A** photographic path. It is a measurement build, not a new reconstruction or colour-correction candidate. Existing green/Sharp/D/H behaviour is retained as the control. TG2 is not reintroduced. Exposure requests, native code, colour assets, JPEG quality and EXIF writing are unchanged.

The prior ROOTCAUSE1A recorder captured only the history before the shutter. This build adds:

- A bounded ledger joining shutter ID, logical/physical sensor timestamps and exact JPEG filename. Unknown or ambiguous joins never fall back to the latest capture.
- Three unscaled 64×64 preview regions, each recording incoming OES, reference render and display render. Sampling is 1 Hz normally and 4 Hz through capture and 6.5 seconds after its result. Actual applied state, colour transforms, tone curves, texture/state timestamps, rotation, mirror, viewport and source continuity are retained. This is shader-output evidence, not sensor-resolution RAW or compositor presentation.
- Frame metadata including the actual selected physical result's CCM and tone curves. Pre-shutter evidence is saved separately; the post window no longer filters out everything after the shutter.
- Five unscaled 96×96 RGB regions copied from the final oriented Bitmap before it is recycled by JPEG encoding. `getPixels` values are non-premultiplied sRGB codes; the source Bitmap colour space is also recorded.
- A streaming hash of JPEG coding markers and all entropy scans before and after EXIF finalization. APP/COM metadata is excluded from that digest, while ICC segments and SOF sampling are reported separately.
- Actual saved EXIF colour space/orientation and Android JPEG-region decoding at the exact Bitmap crop coordinates. Deltas are encoding/decode differences, not ground-truth colour error.
- Thumbnail decode samples and gallery software-view versus PixelCopy window crops at recorded view geometry. Preview PixelCopy samples are also taken at the shutter and four times after still completion. PixelCopy returns the latest queued buffer; it does not prove physical display accuracy or an exact sensor-frame presentation join. Geometry changes and copy failures are explicit.

## Phone test

Use the same scene and light for each shot. Include a white/grey object, something with genuine fine colour, and the edge where the fringe is visible. Keep the phone still.

1. Let the viewfinder settle for at least three seconds.
2. Take one photo at the exposure where the shift occurs. Keep the viewfinder open for **eight seconds after the photograph finishes**.
3. Open that JPEG in the app's gallery, wait two seconds and leave its zoom unchanged for the sample.
4. If needed, repeat at the other EV. Two controlled shots are enough initially.
5. Supply the latest diagnostics burst(s), original JPEG and DNG for those shots. A burst with role `shutter_trace` contains the joined evidence. A `M9_SHUTTERTRACE_...json` individual sidecar is also exported. The capture ID and sequence number identify the newest snapshot when export spans several bundles.

Do not regard the APK build or host tests as a phone colour fix. Device cadence, PixelCopy availability, gallery geometry and complete export must be checked from the first capture. The EXIF string discrepancy is deliberately measured before changing the writer.

## Bounds and failure behaviour

The ledger holds at most four captures; active captures are never evicted to make a guessed join. The IO queue holds 24 tasks, preview history at most 48 samples and metadata at most 1800 rows/30 seconds. RGB copy and pre-EXIF hash durations are reported. Compression, JSON export and final JPEG decoding use a background worker. Full-resolution Bitmaps are not retained. The source image is never modified by the probes.

A missing still result times out at 60 seconds. Camera changes, GL failure, missing joins, ledger/queue saturation, unseen gallery pages and readback failures remain failures, not evidence of parity. Older gallery captures beyond the four retained sessions and app restarts are not silently joined. Retained-window timestamps expose history truncation during unusually long exposures or overlapping shots. `allEndpointKindsRecorded` reports presence only; `causalDiagnosisComplete` remains false. A successful PixelCopy is still not a calibrated screen measurement.

## Validation

`apply-m9cam-m9shuttertrace1a.py` verifies exact TG1 parent hashes and reversible hooks. `verify-m9cam-m9shuttertrace1a.py` checks every assembled source file against the receipt, reverses every hook, and verifies unchanged native code/assets/EXIF writer. No private photographs or photo-derived results belong in this branch.

Host tests exercise exact timestamp joins, saturation/eviction, physical metadata selection, missing values, post-shutter retention, GL restoration, accelerated sampling, RGB region geometry and lossless serialization, and JPEG baseline/progressive scan integrity. Android helpers are also compiled against Android APIs and the app's actual ExifInterface/SSIV versions before the full APK build. Mocked host GL tests do not establish device performance.

[Android PixelCopy contract](https://developer.android.com/reference/android/view/PixelCopy)
[Android Bitmap pixel contract](https://developer.android.com/reference/android/graphics/Bitmap#getPixels(int[],%20int,%20int,%20int,%20int,%20int,%20int))
