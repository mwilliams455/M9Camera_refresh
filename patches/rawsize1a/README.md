# M9Cam 2.87 RAWSIZE1A

This selectively adapts PhotonCamera commit 0100edce4b09523086d45864af0c296579695761
(the vendor raw.size discovery only) on top of 2.86. Vendor metadata can supply a
Size or width/height integer pairs. The rest of that upstream alignment commit,
including native binaries and multi-frame processing, is not imported.

New sizes are available only for RAW_SENSOR still capture, Android 10+, with the
existing Quad Bayer option enabled and the maximum-resolution-key route inactive.
PHOTO, MOTION and NIGHT qualify; video and unlimited paths do not. The setting
remains off by default. There is no new menu item, default resolution change or
claim of additional sensor resolution on the test device.

Hints must contain positive, even Bayer dimensions with an addressable 16-bit
buffer. Odd-length arrays and unknown types are rejected; invalid pairs are
filtered and duplicate sizes omitted. A publicly advertised RAW fallback must
exist before a new hint can enter selection. Null capabilities/enumeration and
unreadable vendor keys are tolerated. The maximum-resolution flag is reset for
each discovery so it cannot carry into an ordinary-mode selection.

When a newly added size is actually selected, the exact session configuration
(including physical-camera output assignments and session parameters when supported)
is checked through CameraDevice.isSessionConfigurationSupported before submission.
False, unsupported queries and exceptions cannot approve the new size. Old Android
versions and normal, unchanged sizes keep their original path without this probe.
Android may ignore session parameters on older implementations; the subsequent
onConfigureFailed/creation-exception fallback therefore remains necessary.

Failure disables the new hints for that logical/physical camera and RAW format for
the controller lifetime, restores the pre-trial active-array rectangles, and uses
the existing bounded reopen/recovery path. A rejected ImageReader size retries
output setup with the old selection. A failed still attempt is retired before
recovery; it is not silently resubmitted. Session generations, open tokens, device
identity and trial identity prevent late callbacks from changing a new lens.

Source scope: CaptureController, new policy helper, 29 regressions and version
metadata. Exposure allocation, AE qualification, the still submission method,
rendering, saved-photo pipelines, native libraries/assets and menus are unchanged.
Source reconstruction and reverse restoration are verified. CI requires the 29
new RAW-size tests plus the 146 existing focused tests (175 total), library release
resource verification and signed-installer checks. Phone validation is pending.

Testing: install over 2.86 and confirm preview/capture/lens switching with ordinary
settings first. The optional vendor-size branch needs an affected camera in Quad
Bayer mode to establish real-device support; a normal-mode pass alone does not
validate higher-resolution capture. Do not enable hidden settings merely to test.

References:
- https://github.com/eszdman/PhotonCamera/commit/0100edce4b09523086d45864af0c296579695761
- https://developer.android.com/reference/android/hardware/camera2/CameraDevice#isSessionConfigurationSupported(android.hardware.camera2.params.SessionConfiguration)

## Verified installer

All 175 focused tests passed, including the 29 RAW-size regressions, with zero
failures, errors or skips. Library release resource verification and installer
checks passed. The first run compiled the app but hit a test-fixture limitation
when mocking Android CaptureRequest.Builder; the rerun uses a real Robolectric
builder/session configuration. No production code change was needed for that fix.

[Download M9Cam-2.87-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38166983518/artifacts/11712503009).
Extract the ZIP and install `M9Cam_2.87_RAWSIZE1A.apk` over 2.86.

Built commit: `5aecaa6095ce94af2de2450157294a72bd63d8c9`; run `38166983518`.
The downloaded artifact independently passed its GitHub digest, CRC, APK identity,
accepted Android v2 signature, alignment, required code markers and preserved UI
checks. All 27 native libraries and 285 assets match the verified 2.86 installer.
See CI_VERIFICATION.json, PACKAGED_VERIFICATION.json and GITHUB_DELIVERY_VERIFICATION.json.

APK SHA-256: `7140f7b6ed3d49163d330a2d4e1ee4b93e73c78efb0b3281b008079f00209804`.

PR #105 remains a candidate pending phone validation. Additional vendor RAW-size
support on a specific phone is not established by these tests. The earlier draft
chain is not finalized into main by this selective source integration.
