# M9Cam 2.21 RAWREADOUT1A

This read-only diagnostic extends 2.20's exact-timestamp capture evidence. It
records selected vendor RAW controls using actual typed keys returned by public
Camera2 APIs, including keys omitted from an individual request's key list.
No vendor key type or value is guessed. Availability, metadata listing, null,
reported zero/false, and read errors remain distinct. Reported values do not
independently prove internal sensor or ISP execution.

The targeted controls are `com.xiaomi.control.qcfa.isSuperRemosaic`, Qualcomm
`RawCbSourceType`, `EnableIdealRAW`, `EnableXCFAOptimization`, Android
`sensor.pixelMode`, and `sensor.rawBinningFactorUsed`. The last field describes
the delivered RAW Bayer grouping under Android's API contract; it is not a
universal indication of every internal sensor-binning operation.

Evidence is added inside the existing `renderer.captureRequest1A` record:

- `rawReadoutBeforeVendorHelper`, `rawReadoutAfterVendorHelper`, and
  `rawReadoutRequest`: typed reads at the existing capture boundaries.
- `rawReadoutResult`, plus per-physical-result reads without borrowing another
  camera's advertised result keys.
- `rawReadoutCapabilities`: selected characteristics, default and maximum
  resolution RAW_SENSOR/RAW10/RAW12 output sizes, high-resolution output sizes
  and input sizes.
- `configuredSession.rawReadoutSessionParameters`: supplied session request
  only. No supplied request does not establish the vendor's internal defaults.
- `configuredSession.rawReadoutCameraInventory`: platform characteristics for
  the actual session device and stream, enumerated IDs and advertised physical
  members. It does not open cameras, probe guessed IDs or select a new mode.

Inventory is collected once per configured session, limited to 16 cameras and
49152 record characters, with explicit truncation. Arrays retain at most 64
values; size lists at most 32 entries. Existing weak session ownership and the
16-record, 196608-character per-frame timestamp store are retained. No new pixel
copies, captures or worker threads are introduced. Unsupported keys stay optional
on other devices and lenses.

The capture policy, rendering, DNG serialization and RAW filtering remain as in
2.20. The prior Advanced setting **RAW capture comparison B** is unchanged.
For the first readout audit, leave that switch **off**, restart the app to create
a fresh camera session, select the main camera and take one normal single-frame
photo. Preserve the PRIMARY JSON, JPEG, normal DNG and RAW_UNFILTERED DNG.
This initial capture discovers what the device reports; it is not a fringe-fix
evaluation or a request for another demosaic sweep.

Version: `2.21-m9rawreadout1a`, code `27221`, package
`com.m9project.m9cam.photon`. Build:
`.github/workflows/build-m9cam-rawreadout1a.yml`, branch
`research/m9-rawreadout1a`. Packaging retains all accepted 2.16 native libraries
and M9 assets and verifies the complete source manifest, signing certificate,
package and version. Unit tests exercise typed-key identity, missing/unadvertised
keys, null versus false/zero, read failures, physical metadata scope, absent
session parameters and bounded array serialization.

Only source and synthetic tests belong in this branch; no private photos or
photo-derived measurements are included. Handset validation remains necessary.
