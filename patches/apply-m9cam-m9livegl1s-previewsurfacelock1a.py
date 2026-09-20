#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1s-previewsurfacelock1a.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
cc_path = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
if not cc_path.exists():
    raise SystemExit("GL1S missing CaptureController: " + str(cc_path))

cc = cc_path.read_text()

old = '''            } else {
                captureBuilder.addTarget(mImageReaderRaw.getSurface());
                CameraMode selectedMode = PhotonCamera.getSettings().selectedMode;
                if(frametime > 0.06 && !isDualSession || selectedMode == CameraMode.RAWVIDEO || selectedMode == CameraMode.UNLIMITED || (!IsoExpoSelector.HDR)) {
                    captureBuilder.addTarget(surface);
                }
            }
'''

new = '''            } else {
                captureBuilder.addTarget(mImageReaderRaw.getSurface());
                CameraMode selectedMode = PhotonCamera.getSettings().selectedMode;

                // M9LIVEGL1S_PREVIEWSURFACELOCK1A
                // The M9 still request must not be rendered into the live OES surface.
                // Doing so briefly replaces Photon's normal preview feed with the
                // still-exposure frame while the GL preview transform is still active,
                // producing the shutter-time dark flash seen on device.
                //
                // RAW remains the sole M9 still target. The session still owns the live
                // preview surface, and normal repeating preview resumes via unlockFocus().
                // Non-M9 / RAWVIDEO / UNLIMITED behavior is preserved exactly.
                final boolean m9IsolateStillFromPreview1S =
                        M9Config.isCaptureTest()
                                && selectedMode != CameraMode.RAWVIDEO
                                && selectedMode != CameraMode.UNLIMITED;
                if (!m9IsolateStillFromPreview1S
                        && (frametime > 0.06 && !isDualSession
                            || selectedMode == CameraMode.RAWVIDEO
                            || selectedMode == CameraMode.UNLIMITED
                            || (!IsoExpoSelector.HDR))) {
                    captureBuilder.addTarget(surface);
                }
                if (m9IsolateStillFromPreview1S) {
                    Log.d(TAG, "M9LIVEGL1S_PREVIEWSURFACELOCK1A stillTargets=RAW_ONLY"
                            + " previewSurfaceTarget=false"
                            + " iso=" + m9CaptureIso1B
                            + " exposureNs=" + m9CaptureExposureNs1B);
                }
            }
'''

count = cc.count(old)
if count != 1:
    raise SystemExit(f"GL1S target block anchor count={count}")

cc = cc.replace(old, new, 1)
cc_path.write_text(cc)

print("M9LIVEGL1S_PREVIEWSURFACELOCK1A applied")
print(" - M9 still request targets RAW only")
print(" - live OES preview surface no longer receives still-exposure capture")
print(" - GL1B exposure authority unchanged")
print(" - non-M9 / RAWVIDEO / UNLIMITED target behavior unchanged")
