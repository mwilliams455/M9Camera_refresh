# M9Cam 3.49 JPEGPERF — faster JPEG finishing on 3.48, unchanged pixels

Parent: **3.48-jpegstore** (27348). Candidate: **3.49-jpegperf** (27349). Test candidate
only; phone timing is pending.

Performance-only. No colour, tone, exposure, noise, sharpening, falloff, JPEG quality or
EXIF value changes.

## Changes

1. **Faster JPEG fingerprint.** After every JPEG is written, the shutter trace reads the
   whole file back to fingerprint its coded bytes before the EXIF worker may touch it. This
   runs on the render thread for every shot. The reader pulled one byte per call through
   `BufferedInputStream`, which takes a lock on every call. A private, unsynchronized
   64 KiB buffer returns the same bytes. On a 12 MP quality-95 JPEG (12.5 MB) the read takes
   **32 ms instead of 239 ms** on the x86 host, with the same SHA-256. The trace records the
   reader as `signatureReader` next to the existing `payloadDigestNs` timing.
2. **Noise cancel keeps 8 threads on wide frames.** 3.47 capped noise-cancel scratch at 1 MiB,
   so frames wider than 4096 px lost threads (the 8000x6000 vendor RAW size got 5 workers).
   3.49 keeps at least the 42 scratch rows a 4096-wide frame gets, which comes to about 2 MiB
   at 8000 px. Frames up to 4096 px wide schedule exactly as in 3.48. On the host:
   8000x6000 takes 2.87 s → 2.34 s, and 8160x6144 takes 3.33 s → 2.55 s. Diagnostics label:
   `JPEGPERF349_bounded_rows_work_queue_42_row_floor`.
3. **MediaStore reservation off the render thread.** With the overlapped encode (normal M9
   shooting), the pending MediaStore entry is now reserved on the encode thread, so that
   round trip to Android's media service overlaps the post-render diagnostics instead of
   delaying the encode. Ownership is unchanged:
   - an encode that fails discards its own reservation;
   - a finished encode hands the reservation to the render thread, which publishes,
     recovers or discards it exactly as in 3.48, including when the render fails while
     the encode is still running.

   New diagnostics: `mediaStoreReserveElapsedMs` and `mediaStoreReserveThread`.
4. **No second index pass.** A JPEG published through MediaStore is indexed as part of that
   publication. The camera screen no longer also broadcasts a media-scan request for it.
   The gallery thumbnail update is unchanged. Other saves, such as DNGs and pre-Android-10
   JPEGs, still send the request.

## Evidence (x86 host unless noted)

- `M9JpegSignatureReaderTest` (4 JUnit tests) compares the new reader with a verbatim copy
  of the 3.48 reader:
  - baseline and progressive JPEGs with byte stuffing, restart markers, fill bytes, ICC
    and COM segments;
  - bulk reads of 1–200000 bytes per call;
  - the file entry point;
  - eight malformed inputs, which fail with the same exception and message.

  A deliberate one-byte skip in the new buffer makes 3 of the 4 tests fail.
- `host/noise_parity349.py` (3.48 vs 3.49):
  - pixels match the parent and the frozen scalar reference at 10 sizes, up to 8160x6144;
  - integer statistics are exact;
  - frames up to 4096 wide have identical worker counts and bit-identical mean statistics;
  - wide frames run on 8 workers;
  - ThreadSanitizer reports no race on an 8000x300 frame (8 workers, 9 bands).
- The 3.47 allocation-pressure probe (`jpegperf347/host/noise_pressure.cpp`) gives the
  same result as 3.48: 1 MiB peak at 4096 wide, and a clean fallback down to 2 rows.
- All changed Java files compile against the 3.48 tree with no new errors.
- New emulator test `mediaStorePublicationIsIndexedWithoutScanRequest` (Android 15, in CI):
  - the finalizer reports a MediaStore JPEG as indexed;
  - MediaStore holds its width, height and size without any scan request.
