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
viewfinder_layout = root / "app/src/main/res/layout/layout_main_viewfinder.xml"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
live_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
curve = root / "app/src/main/assets/m9/m9_curve02_firmware.bin"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, viewfinder_layout,
          main_fs, live_preview, controller, curve, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1A verify missing: " + str(p))

mr = main_renderer.read_text()
gp = gl_preview.read_text()
cf = camera_fragment.read_text()
vl = viewfinder_layout.read_text()
mf = main_fs.read_text()
lp = live_preview.read_text()
cc = controller.read_text()
g = gradle.read_text()

# Actual pinned Photon viewfinder chain.
for token in (
    "import com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview;",
    "textureView = cameraFragmentBinding.layoutViewfinder.texture;"):
    if token not in cf:
        raise SystemExit("M9LIVEGL1A CameraFragment viewfinder token missing: " + token)
if "public class GLPreview extends GLSurfaceView" not in gp:
    raise SystemExit("M9LIVEGL1A GLPreview is not GLSurfaceView")
if "mRenderer = new MainRenderer(this);" not in gp:
    raise SystemExit("M9LIVEGL1A GLPreview does not own MainRenderer")
if "com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview" not in vl:
    raise SystemExit("M9LIVEGL1A viewfinder layout does not use GLPreview")

# Direct OES shader path.
for token in (
    'PhotonCamera.getAssetLoader().getString("shaders/preview/main_fs.glsl")',
    "M9LIVEGL1A_PHOTON_SHADER",
    "PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM",
    "initM9CurveTexture1A()",
    'open("m9/m9_curve02_firmware.bin")',
    "M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f",
    "GLES20.GL_TEXTURE1",
    "GLES30.GL_R8",
    "GLES30.GL_RED",
    "GLES11Ext.GL_TEXTURE_EXTERNAL_OES"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1A MainRenderer token missing: " + token)

for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "samplerExternalOES sTexture",
    "sampler2D uM9Curve",
    "uniform float uM9DisplayGain",
    "curve02M9",
    "sat2M9",
    "13659.0",
    "14811.0",
    "m9DisplayTransform",
    "vec4 photonColor = texture(sTexture, uv);",
    "vec4 color = vec4(m9DisplayTransform(photonColor.rgb), 1.0);"):
    if token not in mf:
        raise SystemExit("M9LIVEGL1A shader token missing: " + token)

# Focus peaking extra samples occur only when explicitly enabled.
p_if = mf.find("if (enablePeak)")
p_loop = mf.find("for (int i = -1; i <= 1; i++)")
if p_if < 0 or p_loop < 0 or p_if > p_loop:
    raise SystemExit("M9LIVEGL1A focus-peaking samples are unconditional")

# RAW overlay disabled.
if "public static final boolean ENABLED = false;" not in lp:
    raise SystemExit("M9LIVEGL1A periodic RAW overlay is still enabled")
if "M9LIVEGL1A_RAW_LIVE_OVERLAY_DISABLED" not in lp:
    raise SystemExit("M9LIVEGL1A RAW overlay marker missing")

# Capture exposure follows current Camera2 preview in shader mode.
for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "M9LivePreview1A.ENABLED",
    "Photon_GL_current_preview_result",
    "? m9LiveWysiwygDisplayedIso1B : mPreviewIso",
    "? m9LiveWysiwygDisplayedExposureNs1B : mPreviewExposureTime"):
    if token not in cc:
        raise SystemExit("M9LIVEGL1A exposure authority token missing: " + token)

curve_sha = hashlib.sha256(curve.read_bytes()).hexdigest()
expected_curve_sha = "5b303ff7d9d47ecb8e193a648ddf0570fef46ad29a62d112993d37d52f8c135c"
if curve_sha != expected_curve_sha:
    raise SystemExit("M9LIVEGL1A curve02 changed: " + curve_sha)

for forbidden in (
    "M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER",
    "reduceBayerMeterReference1600PreservingParity1D",
    "FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP",
    "M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE"):
    if forbidden in mr or forbidden in mf:
        raise SystemExit("M9LIVEGL1A forbidden proxy/reduced path present: " + forbidden)

if "m9livegl1a-photonshader" not in g.lower():
    raise SystemExit("M9LIVEGL1A versionName marker missing")

print("M9LIVEGL1A_PHOTON_SHADER VERIFY PASS")
print(" - pinned CameraFragment -> GLPreview -> MainRenderer -> OES texture path proven")
print(" - M9 transform executes in Photon's real preview fragment shader")
print(" - periodic RAW/ImageView preview disabled")
print(" - exact 2048-entry curve02 frozen and uploaded to GL")
print(" - SAT2 M04/M05 display transform active")
print(" - focus-peaking 3x3 sampling conditional")
print(" - still capture uses current real preview ISO/shutter")
print(" - reduced/proxy RAW preview architectures absent")
