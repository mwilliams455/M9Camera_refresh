# M9HEAPREPAIR1A — memory ownership and diagnostic transport

Parent: `99b095ecbdfa6d682f77c3767f6e80a5d58383ba` / PREVIEWTC20NEG1A 1.70.
Candidate: 1.71-m9heaprepair1a-tg1, versionCode 26691.

This changes memory ownership and metadata transport while preserving the current Auto exposure,
preview TC20 prediction, capture requests, 12 MP output, reconstruction, colour kernels and JPEG quality.

- OpenCV owns the RGB16 working allocation. JNI creates a borrowed direct view of that native storage.
  The renderer's existing `finally` releases it after the final synchronous JNI operation. No full-frame
  `ByteBuffer.allocateDirect` is used on this path; the borrowed view never frees the Mat.
- Diagnostic pending entries retain paths and sizes, not complete byte arrays. Recovery reads manifests,
  not every payload. One coalesced individual-export timer replaces per-update captured tasks. Bundles
  validate and stream up to 16 files per batch, avoiding a combined JSON object graph and byte array.
  Failed exports retain their private payloads. Public provider I/O still requires a visible Activity.
- Gallery DNG/TIFF metadata reads only selected label tags using bounded positional reads. Image strips
  and thumbnail payloads are not read. Cycles and malformed offsets have explicit bounds. Other formats
  retain AndroidX parsing with a 1 MiB input bound. All opened descriptors are closed.
- Histogram requests are cleared when replaced and when their ViewModel is cleared.

Validation: constrained-heap tests of exact production spool and TIFF Java; exact JNI transport methods
with a native allocation fixture; all parent gates; full native kernel/JNI parity; APK identity, signing,
16 KiB alignment and both ARM ABIs. The native owner fixture is not an Android ART/OpenCV device test.
Phone validation is required, including repeated captures, gallery swipes, background/resume and
confirmation that both JPEG and DNG become visible. These changes do not establish that every
possible memory-retention path is fixed. Auto exposure remains under photographic evaluation.

The synthetic tests and implementation are public. Device reports, photographs and their derived
measurements are not included in this branch.
