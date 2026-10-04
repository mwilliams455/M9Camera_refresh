# M9SHUTTERTRACE1B

Diagnostic-only successor to SHUTTERTRACE1A on the accepted DETAIL1H/TG1 control. Version 1.64-m9shuttertrace1b-tg1, code 26684. This does not change demosaic, sharpening, saturation, white balance, JPEG sampling, EXIF writing, preview shaders or camera requests.

Changes:

- Batch JPEG coding bytes into 64 KiB digest updates. Preserve the previous marker parser and exact canonical coding/ICC hashes, including progressive scans, stuffed bytes and restart markers.
- Observe until eight seconds after JPEG finalization, with a sixty-second capture timeout even when Camera2 completes but rendering fails. Retain the initial post-capture window separately and record callback versus persistence times. Coverage requires actual preview samples after the JPEG endpoint.
- Sample only the currently selected, loaded, opaque gallery page with unit transforms on the entire ancestor chain. Check again before readback and after its callback; record the transforms and reject changed geometry. Failed or unverified comparisons do not satisfy gallery coverage. A window readback still does not calibrate the physical display or prove exact presentation timing or absence of overlays.
- Resolve file URI thumbnail names from their paths; query the provider only for content URIs. Label exact-stem DNG thumbnail joins as RAW, and never count them as a decoded JPEG thumbnail. Unknown or ambiguous joins remain unavailable.

The bounded pixel ring can omit part of a very long render. Its retained timestamps, initial window, finite timeout and missing endpoint flags must be respected. A RAW thumbnail that arrives before its JPEG filename has been bound cannot yet join; it is logged as unavailable. No nearest-capture fallback is used.

Validation:

```
python3 patches/apply-m9cam-m9shuttertrace1a.py PhotonCamera
python3 patches/verify-m9cam-m9shuttertrace1a.py PhotonCamera
python3 patches/apply-m9cam-m9shuttertrace1b.py PhotonCamera
python3 patches/tests/m9shuttertrace1b/run.py PhotonCamera
python3 patches/verify-m9cam-m9shuttertrace1b.py PhotonCamera
```

Tests use synthetic JPEGs, the production page transformer with minimal view stubs, pure lifecycle/filename policies, and parity against the unchanged 1A digest implementation. The dedicated workflow also runs the parent gates and full Android build. Android timing and actual gallery capture require device validation. No photographic correction is claimed by these tests.
