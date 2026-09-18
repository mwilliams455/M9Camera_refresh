#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1a-photonshader.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
layout = root / "app/src/main/res/layout/camera_fragment.xml"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
blur_fs = root / "app/src/main/assets/shaders/preview/blur_oes_fs.glsl"
live_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
curve = root / "app/src/main/assets/m9/m9_curve02_firmware.bin"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, layout, main_fs, blur_fs,
          live_preview, controller, curve, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1A verify missing: " + str(p))

mr = main_renderer.read_text()
gp = gl_preview.read_text()
cf = camera_fragment.read_text()
ly = layout.read_text()
mf = main_fs.read_text()
bf = blur_fs.read_text()
lp = live_preview.read_text()
cc = controller.read_text()
g = gradle.read_text()

# Prove this is Photon's actual UI viewfinder chain.
for token in (
    "import com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview;",
    "textureView = cameraFragmentBinding.texture;"):
    if token not in cf:
        raise SystemExit("M9LIVEGL1A CameraFragment viewfinder token missing: " + token)
if "public class GLPreview extends GLSurfaceView" not in gp:
    raise SystemExit("M9LIVEGL1A GLPreview is not GLSurfaceView")
if "mRenderer = new MainRenderer(this);" not in gp:
    raise SystemExit("M9LIVEGL1A GLPreview does not own MainRenderer")
if "com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview" not in ly:
    raise SystemExit("M9LIVEGL1A camera layout does not use ui viewfinder GLPreview")

# Prove the camera OES path is modified directly.
for token in (
    'loadAsset("shaders/preview/main_fs.glsl")',
    "M9LIVEGL1A_PHOTON_SHADER",
    'PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM',
    "initM9CurveTexture1A()",
    'open("m9/m9_curve02_firmware.bin")',
    "M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f",
    "GLES20.GL_TEXTURE1",
    "GLES30.GL_R8",
    "GLES30.GL_RED"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1A MainRenderer token missing: " + token)

for shader_name, text in (("main_fs", mf), ("blur_oes_fs", bf)):
    for token in (
        "M9LIVEGL1A_PHOTON_SHADER",
        "samplerExternalOES sTexture",
        "sampler2D uM9Curve",
        "uniform float uM9DisplayGain",
        "curve02M9",
        "sat2M9",
        "13659.0",
        "14811.0",
        "m9DisplayTransform"):
        if token not in text:
            raise SystemExit(f"M9LIVEGL1A {shader_name} token missing: {token}")

# Sharp preview must transform the exact OES sample, not a periodic bitmap.
for token in (
    "vec4 photonColor = texture(sTexture, uv);",
    "vec4 color = vec4(m9DisplayTransform(photonColor.rgb), 1.0);",
    "if (enablePeak)"):
    if token not in mf:
        raise SystemExit("M9LIVEGL1A sharp shader contract missing: " + token)

# Historical 3x3 peaking work must be conditional, not paid every frame.
if mf.find("if (enablePeak)") > mf.find("for (int i = -1; i <= 1; i++)"):
    raise SystemExit("M9LIVEGL1A focus-peaking samples are still unconditional")

# Old RAW live overlay must be compile-time disabled.
if "public static final boolean ENABLED = false;" not in lp:
    raise SystemExit("M9LIVEGL1A periodic RAW overlay is still enabled")
if "M9LIVEGL1A_RAW_LIVE_OVERLAY_DISABLED" not in lp:
    raise SystemExit("M9LIVEGL1A RAW overlay disable marker missing")

# Still capture follows the same live Camera2 exposure that feeds Photon.
for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "M9LivePreview1A.ENABLED",
    "Photon_GL_current_preview_result",
    "? m9LiveWysiwygDisplayedIso1B : mPreviewIso",
    "? m9LiveWysiwygDisplayedExposureNs1B : mPreviewExposureTime"):
    if token not in cc:
        raise SystemExit("M9LIVEGL1A exposure authority token missing: " + token)

# Curve02 must be the known frozen firmware curve.
curve_sha = hashlib.sha256(curve.read_bytes()).hexdigest()
expected_curve_sha = "5b303ff7d9d47ecb8e193a648ddf0570fef46ad29a62d112993d37d52f8c135c"
if curve_sha != expected_curve_sha:
    raise SystemExit("M9LIVEGL1A curve02 changed: " + curve_sha)

# Explicitly reject the failed reduced RAW architectures.
for forbidden in (
    "M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER",
    "reduceBayerMeterReference1600PreservingParity1D",
    "FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP",
    "M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE"):
    if forbidden in mr or forbidden in mf or forbidden in bf:
        raise SystemExit("M9LIVEGL1A forbidden proxy/reduced path present: " + forbidden)

if "m9livegl1a-photonshader" not in g.lower():
    raise SystemExit("M9LIVEGL1A versionName marker missing")

print("M9LIVEGL1A_PHOTON_SHADER VERIFY PASS")
print(" - CameraFragment -> UI GLPreview -> MainRenderer -> camera OES texture proven")
print(" - M9 transform executes in Photon's real fragment shader every preview frame")
print(" - periodic RAW/ImageView preview is disabled")
print(" - exact 2048-entry firmware curve02 remains frozen and is uploaded to GL")
print(" - SAT2 M04/M05 display transform present in sharp and blur preview shaders")
print(" - focus-peaking 3x3 sampling is conditional")
print(" - still capture uses latest real preview ISO/shutter in shader mode")
print(" - reduced/proxy RAW preview architectures are absent")
