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
