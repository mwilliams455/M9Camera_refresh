#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1b-exposureintent.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
selector = root / "app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, main_fs,
          controller, selector, renderer, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1B missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1B {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

# Require the direct Photon GL architecture from 1A.
mr = main_renderer.read_text()
gp = gl_preview.read_text()
cf = camera_fragment.read_text()
fs = main_fs.read_text()
cc = controller.read_text()
sel = selector.read_text()

for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM",
    "M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1B missing GL1A MainRenderer token: " + token)
for token in (
    "M9LIVEGL1A_PHOTON_SHADER",
    "m9DisplayTransform",
    "uM9DisplayGain"):
    if token not in fs:
        raise SystemExit("M9LIVEGL1B missing GL1A shader token: " + token)
if "M9LIVEGL1A_PHOTON_SHADER capture lock source=" not in cc:
    raise SystemExit("M9LIVEGL1B missing GL1A capture-lock token")
if "setExactExposureM9Wysiwyg1B(" not in sel:
    raise SystemExit("M9LIVEGL1B exact still exposure setter missing")

# ---------------------------------------------------------------------------
# 1) CaptureController: latch the intended non-ZSL exposure pair represented by
#    the GL preview, then use that exact pair for still capture.
# ---------------------------------------------------------------------------
field_anchor = """    private volatile long m9LiveWysiwygDisplayedRawTimestampNs1B = -1L;
"""
field_new = field_anchor + """    // M9LIVEGL1B_EXPOSUREINTENT
    // Latest non-ZSL IsoExpoSelector pair represented by the Photon GL viewfinder.
    private volatile int m9LiveGlIntendedIso1B = -1;
    private volatile long m9LiveGlIntendedExposureNs1B = -1L;
    private volatile long m9LiveGlIntendedUpdatedElapsedMs1B = 0L;
"""
cc = one(cc, field_anchor, field_new, "intended exposure fields")

method_anchor = """    private void captureStillPicture() {
"""
method_new = r'''    /**
     * M9LIVEGL1B_EXPOSUREINTENT
     *
     * CameraFragment calls this from the current preview CaptureResult after computing
     * the exact IsoExpoSelector pair shown in the non-ZSL HUD. The GL preview is scaled
     * to represent this pair, therefore this same pair is the shutter authority.
     */
    public void updateM9LiveGlIntendedExposure1B(int iso, long exposureNs) {
        if (iso <= 0 || exposureNs <= 0L) return;
        m9LiveGlIntendedIso1B = iso;
        m9LiveGlIntendedExposureNs1B = exposureNs;
        m9LiveGlIntendedUpdatedElapsedMs1B = android.os.SystemClock.elapsedRealtime();
    }

''' + method_anchor
cc = one(cc, method_anchor, method_new, "intended exposure latch method")

old_block = """            // M9LIVEGL1A_PHOTON_SHADER: no periodic rendered ImageView exists.
            // The visible frame is Photon's current OES texture transformed in GL.
            final boolean m9DisplayedExposureAvailable1B =
                    M9LivePreview1A.ENABLED
                            && m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;
            final int m9CaptureIso1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedIso1B : mPreviewIso;
            final long m9CaptureExposureNs1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedExposureNs1B : mPreviewExposureTime;
            final long m9CapturePreviewTimestampNs1B =
                    m9DisplayedExposureAvailable1B
                            ? m9LiveWysiwygDisplayedRawTimestampNs1B : -1L;
"""
new_block = """            // M9LIVEGL1B_EXPOSUREINTENT
            // GL1A incorrectly fell back to the hardware-AE preview result. That is NOT
            // the non-ZSL exposure shown by Photon/IsoExpoSelector. Device video proved
            // the error directly: HUD 1/100 ISO50, saved JPEG 1/100 ISO221.
            // In GL mode the latched intended pair is authoritative because the shader
            // explicitly simulates that pair from the current OES preview.
            final boolean m9DisplayedExposureAvailable1B =
                    M9LivePreview1A.ENABLED
                            && m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;
            final boolean m9GlIntendedExposureAvailable1B =
                    !M9LivePreview1A.ENABLED
                            && m9LiveGlIntendedIso1B > 0
                            && m9LiveGlIntendedExposureNs1B > 0L;
            final int m9CaptureIso1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedIso1B
                    : (m9GlIntendedExposureAvailable1B
                        ? m9LiveGlIntendedIso1B : mPreviewIso);
            final long m9CaptureExposureNs1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedExposureNs1B
                    : (m9GlIntendedExposureAvailable1B
                        ? m9LiveGlIntendedExposureNs1B : mPreviewExposureTime);
            final long m9CapturePreviewTimestampNs1B =
                    m9DisplayedExposureAvailable1B
                            ? m9LiveWysiwygDisplayedRawTimestampNs1B : -1L;
"""
cc = one(cc, old_block, new_block, "capture exposure authority")

old_log = """            Log.d(TAG, "M9LIVEGL1A_PHOTON_SHADER capture lock source="
                    + (m9DisplayedExposureAvailable1B
                            ? "ImageView_displayed_M9_frame" : "Photon_GL_current_preview_result")
                    + " iso=" + m9CaptureIso1B
                    + " exposureNs=" + m9CaptureExposureNs1B
                    + " displayedRawTimestampNs=" + m9CapturePreviewTimestampNs1B);
"""
new_log = """            Log.d(TAG, "M9LIVEGL1B_EXPOSUREINTENT capture lock source="
                    + (m9DisplayedExposureAvailable1B
                            ? "ImageView_displayed_M9_frame"
                            : (m9GlIntendedExposureAvailable1B
                                ? "Photon_GL_IsoExpoSelector_intended_pair"
                                : "latest_real_preview_result_FALLBACK"))
                    + " iso=" + m9CaptureIso1B
                    + " exposureNs=" + m9CaptureExposureNs1B
                    + " intendedAgeMs="
                    + (m9GlIntendedExposureAvailable1B
                        ? Math.max(0L, android.os.SystemClock.elapsedRealtime()
                            - m9LiveGlIntendedUpdatedElapsedMs1B)
                        : -1L)
                    + " displayedRawTimestampNs=" + m9CapturePreviewTimestampNs1B);
"""
cc = one(cc, old_log, new_log, "capture authority log")
controller.write_text(cc)

# ---------------------------------------------------------------------------
# 2) MainRenderer / GLPreview: dynamic exposure-energy scale.
#    Photon keeps hardware AE for fluidity; in linearized display space, scale
#    the OES frame by targetEnergy / actualPreviewEnergy before SAT2+curve02.
# ---------------------------------------------------------------------------
mr = main_renderer.read_text()
field_anchor = """    private int uM9Curve;
"""
field_new = field_anchor + """    // M9LIVEGL1B_EXPOSUREINTENT
    private volatile float mM9ExposureScale1B = 1.0f;
    private int uM9ExposureScale1B;
"""
mr = one(mr, field_anchor, field_new, "GL exposure fields")

uniform_anchor = """        uM9DisplayGain = GLES20.glGetUniformLocation(hProgram, "uM9DisplayGain");
        uM9Curve = GLES20.glGetUniformLocation(hProgram, "uM9Curve");
        GLES20.glUniform1i(uM9Curve, 1);
"""
uniform_new = """        uM9DisplayGain = GLES20.glGetUniformLocation(hProgram, "uM9DisplayGain");
        uM9Curve = GLES20.glGetUniformLocation(hProgram, "uM9Curve");
        uM9ExposureScale1B = GLES20.glGetUniformLocation(hProgram, "uM9ExposureScale1B");
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, uniform_anchor, uniform_new, "GL exposure uniform location")

draw_anchor = """        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1i(uM9Curve, 1);
"""
draw_new = """        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1f(uM9ExposureScale1B, mM9ExposureScale1B);
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, draw_anchor, draw_new, "GL exposure uniform upload")

setter_anchor = """    public void setMirror(boolean mirrorPreview) {
"""
setter_new = r'''    public void setM9ExposureScale1B(float scale) {
        if (!Float.isFinite(scale) || scale <= 0.0f) scale = 1.0f;
        // Preview transport guard only. Normal exposure controls sit comfortably
        // inside this +/-4 EV window.
        mM9ExposureScale1B = Math.max(0.0625f, Math.min(16.0f, scale));
        mView.requestRender();
    }

''' + setter_anchor
mr = one(mr, setter_anchor, setter_new, "MainRenderer exposure setter")
main_renderer.write_text(mr)

gp = gl_preview.read_text()
gp_anchor = """    public void setMirror(boolean mirror) {
        mRenderer.setMirror(mirror);
        requestRender();
    }
"""
gp_new = gp_anchor + r'''
    /** M9LIVEGL1B_EXPOSUREINTENT: target/actual exposure energy for the GL M9 view. */
    public void setM9ExposureScale1B(float scale) {
        if (mRenderer != null) {
            mRenderer.setM9ExposureScale1B(scale);
        }
    }
'''
gp = one(gp, gp_anchor, gp_new, "GLPreview exposure bridge")
gl_preview.write_text(gp)

fs = main_fs.read_text()
uniform_fs_anchor = """uniform float uM9DisplayGain;
"""
uniform_fs_new = uniform_fs_anchor + """uniform float uM9ExposureScale1B;
"""
fs = one(fs, uniform_fs_anchor, uniform_fs_new, "shader exposure uniform")

linear_anchor = """    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));
    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
"""
linear_new = """    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));
    // M9LIVEGL1B_EXPOSUREINTENT: represent the exact non-ZSL shutter/ISO pair
    // rather than the hardware-AE preview energy.
    linear *= uM9ExposureScale1B;
    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
"""
fs = one(fs, linear_anchor, linear_new, "shader exposure application")
main_fs.write_text(fs)

# ---------------------------------------------------------------------------
# 3) CameraFragment: on every real preview result, calculate the same intended
#    IsoExpoSelector pair the HUD displays. Feed its energy ratio to GL and
#    latch that exact pair for the shutter.
# ---------------------------------------------------------------------------
cf = camera_fragment.read_text()
screen_anchor = """    private void updateScreenLog(CaptureResult result) {
        surfaceView.post(() -> {
"""
screen_new = r'''    private void updateScreenLog(CaptureResult result) {
        // M9LIVEGL1B_EXPOSUREINTENT
        // The non-ZSL HUD already advertises IsoExpoSelector.GenerateExpoPair(-1).
        // GL1A displayed transformed hardware AE but captured hardware AE too, so
        // the advertised/user-selected exposure never reached the saved still.
        // Drive both the GL representation and still latch from this exact pair.
        if (captureController != null && textureView != null
                && !captureController.isZslMode() && result != null) {
            try {
                IsoExpoSelector.ExpoPair intended1B =
                        IsoExpoSelector.GenerateExpoPair(-1, captureController);
                Long actualExposure1B = result.get(CaptureResult.SENSOR_EXPOSURE_TIME);
                Integer actualIso1B = result.get(CaptureResult.SENSOR_SENSITIVITY);
                if (intended1B != null
                        && intended1B.exposure > 0L && intended1B.iso > 0
                        && actualExposure1B != null && actualExposure1B > 0L
                        && actualIso1B != null && actualIso1B > 0) {
                    double intendedEnergy1B =
                            (double) intended1B.exposure * (double) intended1B.iso;
                    double actualEnergy1B =
                            (double) actualExposure1B * (double) actualIso1B;
                    double exposureScale1B = intendedEnergy1B / actualEnergy1B;
                    if (Double.isFinite(exposureScale1B) && exposureScale1B > 0.0) {
                        textureView.setM9ExposureScale1B((float) exposureScale1B);
                        captureController.updateM9LiveGlIntendedExposure1B(
                                intended1B.iso, intended1B.exposure);
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "M9LIVEGL1B exposure intent update failed: " + t);
            }
        }
        surfaceView.post(() -> {
'''
cf = one(cf, screen_anchor, screen_new, "CameraFragment exposure intent")
camera_fragment.write_text(cf)

# ---------------------------------------------------------------------------
# 4) Still photographic renderer is deliberately untouched. Existing TONEBOUND050
#    already bounds TC20 to +/-0.5 EV, so after the capture-pair correction the
#    photographer's multi-EV exposure choice cannot be wholly normalized away.
# ---------------------------------------------------------------------------
r = renderer.read_text()
for token in (
    'toneBoundLimitEv1A = 0.5',
    'm9cam.tonebound.v1a.050ev',
    'captureExposureMutation", false'):
    if token not in r:
        raise SystemExit("M9LIVEGL1B expected frozen TONEBOUND050 token missing: " + token)

# Build identity.
g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("versionName "):
        if "m9livegl1b" not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len("versionName "):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit("M9LIVEGL1B unsupported versionName syntax: " + line)
            base = value[1:-1]
            lines[i] = prefix + "versionName " + quote + base + "-m9livegl1b-exposureintent" + quote
            changed = True
        break
else:
    raise SystemExit("M9LIVEGL1B versionName missing")
if changed:
    gradle.write_text("\n".join(lines) + ("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1B_EXPOSUREINTENT applied")
print(" - non-ZSL IsoExpoSelector pair is now the GL preview exposure authority")
print(" - GL simulates target ISO*shutter / actual-preview ISO*shutter in linear space")
print(" - exact same intended pair is latched for still capture")
print(" - GL1A hardware-AE capture fallback is no longer primary")
print(" - still M9 photographic renderer remains frozen")
print(" - existing TONEBOUND050 retained")
