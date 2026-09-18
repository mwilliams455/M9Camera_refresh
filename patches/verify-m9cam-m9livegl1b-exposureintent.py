#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1b-exposureintent.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradle = root / "app/build.gradle"

for p in (controller, camera_fragment, gl_preview, main_renderer, main_fs, renderer, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1B verify missing: " + str(p))

cc = controller.read_text()
cf = camera_fragment.read_text()
gp = gl_preview.read_text()
mr = main_renderer.read_text()
fs = main_fs.read_text()
rr = renderer.read_text()
g = gradle.read_text()

# The direct Photon GL viewfinder architecture remains.
for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM",
    "M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1B missing GL1A renderer anchor: " + token)

# Intended exposure is computed from the exact pair Photon itself advertises in Photo mode.
for token in (
    "M9LIVEGL1B_EXPOSUREINTENT",
    "IsoExpoSelector.GenerateExpoPair(-1, captureController)",
    "intended1B.exposure",
    "intended1B.iso",
    "CaptureResult.SENSOR_EXPOSURE_TIME",
    "CaptureResult.SENSOR_SENSITIVITY",
    "intendedEnergy1B / actualEnergy1B",
    "textureView.setM9ExposureScale1B((float) exposureScale1B)",
    "captureController.updateM9LiveGlIntendedExposure1B("):
    if token not in cf:
        raise SystemExit("M9LIVEGL1B CameraFragment token missing: " + token)

# Same intended pair is latched into the still request.
for token in (
    "m9LiveGlIntendedIso1B",
    "m9LiveGlIntendedExposureNs1B",
    "updateM9LiveGlIntendedExposure1B(int iso, long exposureNs)",
    "m9GlIntendedExposureAvailable1B",
    "Photon_GL_IsoExpoSelector_intended_pair",
    "? m9LiveGlIntendedIso1B : mPreviewIso",
    "? m9LiveGlIntendedExposureNs1B : mPreviewExposureTime"):
    if token not in cc:
        raise SystemExit("M9LIVEGL1B CaptureController token missing: " + token)

# Confirm the GL1A erroneous fallback is no longer the primary logged authority.
if "Photon_GL_current_preview_result" in cc:
    raise SystemExit("M9LIVEGL1B stale GL1A hardware-AE authority still present")

# GL preview bridge and shader exposure scale.
for token in (
    "setM9ExposureScale1B(float scale)",
    "mRenderer.setM9ExposureScale1B(scale)"):
    if token not in gp:
        raise SystemExit("M9LIVEGL1B GLPreview token missing: " + token)
for token in (
    "mM9ExposureScale1B",
    "uM9ExposureScale1B",
    "GLES20.glUniform1f(uM9ExposureScale1B, mM9ExposureScale1B)",
    "setM9ExposureScale1B(float scale)"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1B MainRenderer token missing: " + token)
for token in (
    "uniform float uM9ExposureScale1B;",
    "linear *= uM9ExposureScale1B;",
    "sat2M9(linear) * uM9DisplayGain"):
    if token not in fs:
        raise SystemExit("M9LIVEGL1B shader token missing: " + token)

# Exposure intent is applied BEFORE SAT2 and curve02.
if not (fs.find("linear *= uM9ExposureScale1B;") < fs.find("sat2M9(linear)") < fs.find("curve02M9(sat2.r)")):
    raise SystemExit("M9LIVEGL1B shader exposure/SAT2/curve order incorrect")

# TONEBOUND050 remains exactly the current still-render authority; GL1B must not
# invent a second JPEG-side exposure manipulation.
for token in (
    "toneBoundLimitEv1A = 0.5",
    'toneBound1AJson.put("schema", "m9cam.tonebound.v1a.050ev")',
    'toneBound1AJson.put("captureExposureMutation", false)'):
    if token not in rr:
        raise SystemExit("M9LIVEGL1B frozen TONEBOUND050 token missing: " + token)

if "m9livegl1b-exposureintent" not in g.lower():
    raise SystemExit("M9LIVEGL1B versionName marker missing")

print("M9LIVEGL1B_EXPOSUREINTENT VERIFY PASS")
print(" - Photo-mode IsoExpoSelector pair drives GL exposure representation")
print(" - target/actual ISO*shutter ratio applied in linearized Photon preview")
print(" - exact same intended ISO/shutter pair is latched for still capture")
print(" - GL1A hardware-AE still fallback is no longer primary")
print(" - exposure scale precedes SAT2 and curve02")
print(" - still M9 renderer/TONEBOUND050 contract retained")
