#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1a-photonshader.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
viewfinder_layout = root / "app/src/main/res/layout/layout_main_viewfinder.xml"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
live_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, viewfinder_layout,
          main_fs, live_preview, controller, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1A missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1A {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

# Exact pinned Photon viewfinder contract.
cf = camera_fragment.read_text()
if "import com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview;" not in cf:
    raise SystemExit("M9LIVEGL1A CameraFragment GLPreview import missing")
if "textureView = cameraFragmentBinding.layoutViewfinder.texture;" not in cf:
    raise SystemExit("M9LIVEGL1A CameraFragment binding does not point to viewfinder GLPreview")
gp = gl_preview.read_text()
if "public class GLPreview extends GLSurfaceView" not in gp or "mRenderer = new MainRenderer(this);" not in gp:
    raise SystemExit("M9LIVEGL1A pinned GLPreview renderer contract missing")
vl = viewfinder_layout.read_text()
if "com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview" not in vl:
    raise SystemExit("M9LIVEGL1A pinned viewfinder layout GLPreview missing")

# Disable the old periodic RAW -> ImageView path. The ImageView may remain in
# the assembled layout, but it can never be scheduled or made visible.
lp = live_preview.read_text()
lp = one(lp,
         "    public static final boolean ENABLED = true;",
         "    // M9LIVEGL1A_RAW_LIVE_OVERLAY_DISABLED: Photon OES preview is the live carrier.\\n"
         "    public static final boolean ENABLED = false;",
         "disable periodic RAW overlay")
live_preview.write_text(lp)

# In shader mode the displayed image corresponds to the current Camera2 preview,
# so still capture must use that same real preview exposure rather than stale
# ImageView bookkeeping from the retired RAW overlay.
cc = controller.read_text()
old_lock = """            final boolean m9DisplayedExposureAvailable1B =
                    m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;"""
new_lock = """            // M9LIVEGL1A_PHOTON_SHADER: no periodic rendered ImageView exists.
            // The visible frame is Photon's current OES texture transformed in GL.
            final boolean m9DisplayedExposureAvailable1B =
                    M9LivePreview1A.ENABLED
                            && m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;"""
cc = one(cc, old_lock, new_lock, "shader exposure authority")
old_log = """            Log.d(TAG, "M9LIVEWYSIWYG1B capture lock source="
                    + (m9DisplayedExposureAvailable1B
                            ? "ImageView_displayed_M9_frame" : "latest_real_preview_result")"""
new_log = """            Log.d(TAG, "M9LIVEGL1A_PHOTON_SHADER capture lock source="
                    + (m9DisplayedExposureAvailable1B
                            ? "ImageView_displayed_M9_frame" : "Photon_GL_current_preview_result")"""
cc = one(cc, old_log, new_log, "capture lock log")
controller.write_text(cc)

# Replace Photon's real OES fragment shader. This does not touch RAW or the
# still renderer. curve02 comes from the exact frozen firmware asset as a GL LUT.
main_shader = r'''#extension GL_OES_EGL_image_external_essl3 : require
precision highp float;

// M9LIVEGL1A_PHOTON_SHADER
uniform samplerExternalOES sTexture;
uniform sampler2D uM9Curve;
uniform vec2 resolution;
uniform bool enablePeak;
uniform bool mirror;
uniform bool uM9Enabled;
uniform float uM9DisplayGain;
out vec4 Output;
in vec2 texCoord;

vec3 srgbToLinearM9(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow((c + vec3(0.055)) / 1.055, vec3(2.4));
    return mix(lo, hi, step(vec3(0.04045), c));
}

float curve02M9(float x) {
    float p = clamp(x, 0.0, 1.0) * 2047.0;
    float u = (p + 0.5) / 2048.0;
    return texture(uM9Curve, vec2(u, 0.5)).r;
}

vec3 sat2M9(vec3 c) {
    vec3 outv;
    if (c.r >= c.g) {
        outv.r = dot(vec3(13659.0, -4457.0, -1004.0) / 8192.0, c);
        outv.g = dot(vec3(-2244.0, 13469.0, -3033.0) / 8192.0, c);
        outv.b = dot(vec3(-199.0, -6014.0, 14398.0) / 8192.0, c);
    } else {
        outv.r = dot(vec3(14811.0, -5604.0, -1004.0) / 8192.0, c);
        outv.g = dot(vec3(-2455.0, 13688.0, -3033.0) / 8192.0, c);
        outv.b = dot(vec3(393.0, -6588.0, 14398.0) / 8192.0, c);
    }
    return max(outv, vec3(0.0));
}

vec3 m9DisplayTransform(vec3 photonSrgb) {
    if (!uM9Enabled) return photonSrgb;
    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));
    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    return vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
}

void main() {
    vec2 uv = texCoord.xy;
    if (mirror)
        uv.y = 1.0 - uv.y;

    vec4 photonColor = texture(sTexture, uv);
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb), 1.0);

    // Peaking is UI diagnostics; avoid nine extra OES samples unless requested.
    if (enablePeak) {
        vec2 size = resolution;
        vec4 avg = vec4(0.0);
        for (int i = -1; i <= 1; i++) {
            for (int j = -1; j <= 1; j++) {
                avg += texture(sTexture, uv + vec2(i * 2, j * 2) / size);
            }
        }
        avg /= 9.0;
        float diff = dot(abs(photonColor - avg), vec4(0.299, 0.587, 0.114, 0.0));
        float denoiseK = 0.05;
        float w = (diff * diff) / (denoiseK + (diff * diff));
        color = color + vec4(1.0, 0.0, 1.0, 0.0) * 32.0 * diff * w;
    }

    Output = color;
}
'''
main_fs.write_text(main_shader)

mr = main_renderer.read_text()
if "M9LIVEGL1A_PHOTON_SHADER" in mr:
    raise SystemExit("M9LIVEGL1A MainRenderer already patched")

field_anchor = """    private int mirror;
"""
field_insert = """    private int mirror;

    // M9LIVEGL1A_PHOTON_SHADER
    private static final String M9_LIVE_GL1A_MODE =
            "PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM";
    // Initial display-domain calibration from the controller/window
    // Photon -> validated full M9 preview transition.
    private static final float M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f;
    private int mM9CurveTex;
    private int uM9Enabled;
    private int uM9DisplayGain;
    private int uM9Curve;
"""
mr = one(mr, field_anchor, field_insert, "M9 fields")

surface_anchor = """        initTex();
        mSTexture = new SurfaceTexture(hTex[0]);
"""
surface_insert = """        initTex();
        initM9CurveTexture1A();
        Log.d("M9LiveGL1A", "M9LIVEGL1A_PHOTON_SHADER mode=" + M9_LIVE_GL1A_MODE
                + " gain=" + M9_LIVE_GL1A_DISPLAY_GAIN
                + " RAW_LIVE_OVERLAY_DISABLED");
        mSTexture = new SurfaceTexture(hTex[0]);
"""
mr = one(mr, surface_anchor, surface_insert, "surface curve init")

uniform_anchor = """        enablePeak = GLES20.glGetUniformLocation(hProgram, "enablePeak");
        mirror = GLES20.glGetUniformLocation(hProgram, "mirror");
        GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
uniform_insert = """        enablePeak = GLES20.glGetUniformLocation(hProgram, "enablePeak");
        mirror = GLES20.glGetUniformLocation(hProgram, "mirror");
        uM9Enabled = GLES20.glGetUniformLocation(hProgram, "uM9Enabled");
        uM9DisplayGain = GLES20.glGetUniformLocation(hProgram, "uM9DisplayGain");
        uM9Curve = GLES20.glGetUniformLocation(hProgram, "uM9Curve");
        GLES20.glUniform1i(uM9Curve, 1);
        GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
mr = one(mr, uniform_anchor, uniform_insert, "shader uniform locations")

draw_anchor = """        GLES20.glUniform1i(enablePeak, peakEnabled);
        GLES20.glUniform1i(mirror, mMirrorPreview ? 1 : 0);

        GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
draw_insert = """        GLES20.glUniform1i(enablePeak, peakEnabled);
        GLES20.glUniform1i(mirror, mMirrorPreview ? 1 : 0);
        GLES20.glUniform1i(uM9Enabled, mM9CurveTex != 0 ? 1 : 0);
        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1i(uM9Curve, 1);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, mM9CurveTex);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, hTex[0]);

        GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
mr = one(mr, draw_anchor, draw_insert, "per-frame M9 uniforms")

init_anchor = """    private void initTex() {
"""
curve_method = r'''    private void initM9CurveTexture1A() {
        mM9CurveTex = 0;
        final byte[] curve = new byte[2048];
        try (java.io.InputStream in = mView.getContext().getAssets()
                .open("m9/m9_curve02_firmware.bin")) {
            int off = 0;
            while (off < curve.length) {
                int n = in.read(curve, off, curve.length - off);
                if (n < 0) break;
                off += n;
            }
            if (off != curve.length) {
                Log.e("M9LiveGL1A", "curve02 size=" + off + " expected=2048");
                return;
            }
        } catch (java.io.IOException e) {
            Log.e("M9LiveGL1A", "curve02 load failed " + e);
            return;
        }

        ByteBuffer data = ByteBuffer.allocateDirect(curve.length).order(ByteOrder.nativeOrder());
        data.put(curve);
        data.position(0);
        int[] tex = new int[1];
        GLES20.glGenTextures(1, tex, 0);
        if (tex[0] == 0) return;
        mM9CurveTex = tex[0];
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, mM9CurveTex);
        GLES30.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES30.GL_R8,
                2048, 1, 0, GLES30.GL_RED, GLES20.GL_UNSIGNED_BYTE, data);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
    }

'''
mr = one(mr, init_anchor, curve_method + init_anchor, "curve texture method")
main_renderer.write_text(mr)

# Distinct validation build identity.
g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("versionName "):
        if "m9livegl1a" not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len("versionName "):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit("M9LIVEGL1A unsupported versionName syntax: " + line)
            base = value[1:-1]
            lines[i] = prefix + "versionName " + quote + base + "-m9livegl1a-photonshader" + quote
            changed = True
        break
else:
    raise SystemExit("M9LIVEGL1A versionName missing")
if changed:
    gradle.write_text("\n".join(lines) + ("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1A_PHOTON_SHADER applied")
print(" - pinned Photon OES viewfinder is the live carrier")
print(" - periodic RAW/ImageView renderer disabled")
print(" - exact curve02 uploaded as 2048x1 GL_R8 LUT")
print(" - firmware SAT2 M04/M05 applied in display domain")
print(" - initial display gain 0.40 from controller/window calibration")
print(" - focus-peaking extra samples skipped when peaking is off")
print(" - still M9 renderer untouched")
