# M9ROOTCAUSE1A — temporal diagnosis

This diagnostic-only successor to RBROLLBACK1A records the missing history needed
to distinguish focus movement, ISP/source detail loss, display processing and
white-point changes. It is not a photographic correction.

The source application gate verifies the complete RBROLLBACK1A parent inventory.
It adds two observer classes and hooks them into CaptureController and MainRenderer.
All other application sources and assets remain byte-identical, except versionName.
No native reconstruction, colour, exposure, focus, AWB, shader or TG2 policy changes.

The PRIMARY shutterPreview1W object receives:

- `rootCauseMetadata1A`: up to 30 seconds / 1,800 completed capture metadata rows.
  Physical results are selected explicitly. Sensor timestamps and frame numbers
  remain 64-bit integers; missing values are null. Rows contain neutral, WB gains,
  AF request/result state, lens position, hardware exposure, ISP modes and user EV.
- `rootCausePixels1A`: up to 20 seconds / 20 asynchronous probes. Each probe draws
  the existing source, reference and displayed modes from the same OES texture.
  The centre 96×96 crop retains original GL viewport pixel scale, rather than
  shrinking the whole scene. Scissors isolate panels. All GL state is restored.
  Pixels are losslessly zlib-compressed RGB8, base64 encoded, bottom row first.

Join texture timestamps to metadata exactly. Do not substitute nearest metadata
silently: source-state timestamps are stored separately and may be one frame away.
The crop is in display pixels, not sensor pixels. These are submitted GPU pixels,
not a guarantee of final compositor presentation. Probes do not feed metering.

Validation covers physical-result authority, missing values, camera isolation,
time windows, bounds, portable pixel payloads, nonblocking fences, failure isolation
and GL state restoration. A real Mesa GLES test compares shifted-viewport crops
against the corresponding full-render pixels at source/reference/display stages.
Hardware cadence and focus behaviour still require phone validation.

Diagnostics add bounded memory, GPU sampling and sidecar work. They must not be
described as performance-neutral before testing. There is no per-frame file I/O.

For a useful recording: keep a detailed stationary subject in the centre, change
EV, wait several seconds, then take one photo within 15 seconds of the change.
Return the normal diagnostic burst, DNG and JPEG with the screen recording.
An uncoloured matte reference under the same light helps assess AWB; an arbitrary
replacement Kelvin value is not ground truth.
