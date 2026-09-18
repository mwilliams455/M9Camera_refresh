#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1a-photonshader.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
blur_fs = root / "app/src/main/assets/shaders/preview/blur_oes_fs.glsl"
live_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, main_fs, blur_fs, live_preview, controller, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1A missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1A {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

# Prove we are modifying the actual Photon viewfinder, not another RAW overlay.
cf = camera_fragment.read_text()
if "import com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview;" not in cf:
    raise SystemExit("M9LIVEGL1A CameraFragment does not use ui.viewfinder.GLPreview")
gp = gl_preview.read_text()
if "public class GLPreview extends GLSurfaceView" not in gp or "mRenderer = new MainRenderer(this);" not in gp:
    raise SystemExit("M9LIVEGL1A GLPreview renderer contract missing")

# Disable the old periodic RAW -> ImageView preview completely.
lp = live_preview.read_text()
lp = one(lp,
         "    public static final boolean ENABLED = true;",
         "    // M9LIVEGL1A_RAW_LIVE_OVERLAY_DISABLED: Photon OES preview is now the live carrier.\\n"
         "    public static final boolean ENABLED = false;",
         "disable periodic RAW overlay")
live_preview.write_text(lp)

# Make still capture explicitly use the current real Camera2 preview exposure in shader mode.
cc = controller.read_text()
old_lock = """            final boolean m9DisplayedExposureAvailable1B =
                    m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;"""
new_lock = """            // M9LIVEGL1A_PHOTON_SHADER: the periodic M9 ImageView is disabled.
            // The displayed image is the current Photon SurfaceTexture transformed in GL,
            // so the still must lock the latest real preview CaptureResult exposure.
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

# Replace only the two shaders that sample the camera OES texture.
main_shader = r'''#extension GL_OES_EGL_image_external_essl3 : require
precision highp float;

// M9LIVEGL1A_PHOTON_SHADER
// Photon remains the continuous camera-preview carrier. This fragment shader
// applies the M9 display-domain approximation every GL frame; no RAW bitmap
// overlay participates in the viewfinder.
uniform samplerExternalOES sTexture;
uniform sampler2D uM9Curve;
uniform vec2 resolution;
uniform bool enablePeak;
uniform bool mirror;
uniform bool uM9Enabled;
uniform float uM9DisplayGain;
uniform float uCornerRadius;
uniform vec2 uSharpOrigin;
out vec4 Output;
in vec2 texCoord;

vec3 srgbToLinearM9(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow((c + vec3(0.055)) / 1.055, vec3(2.4));
    return mix(lo, hi, step(vec3(0.04045), c));
}

float curve02M9(float x) {
    float p = clamp(x, 0.0, 1.0) * 2047.0;
    // Exact 2048-byte firmware curve02 is uploaded as a 2048x1 GL_R8 texture.
    float u = (p + 0.5) / 2048.0;
    return texture(uM9Curve, vec2(u, 0.5)).r;
}

vec3 sat2M9(vec3 c) {
    // Leica M9 Standard firmware SAT2 M04/M05; same branch rule as still path.
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
    if (uCornerRadius > 0.0) {
        vec2 halfSize = resolution * 0.5;
        vec2 local = gl_FragCoord.xy - uSharpOrigin;
        vec2 q = abs(local - halfSize) - (halfSize - vec2(uCornerRadius));
        float cornerDist = length(max(q, vec2(0.0)))
                + min(max(q.x, q.y), 0.0) - uCornerRadius;
        if (cornerDist > 0.0)
            discard;
    }

    vec2 uv = texCoord.xy;
    if (mirror)
        uv.y = 1.0 - uv.y;

    vec4 photonColor = texture(sTexture, uv);
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb), 1.0);

    // Peaking is diagnostic UI, not M9 rendering. Avoid the historical nine
    // extra OES samples entirely when peaking is off.
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

blur_shader = r'''#extension GL_OES_EGL_image_external_essl3 : require
precision highp float;

// M9LIVEGL1A_PHOTON_SHADER
// The panel/edge blur starts from the same transformed Photon preview so glass
// regions do not reveal the unmodified Xiaomi/Photon colour underneath.
uniform samplerExternalOES sTexture;
uniform sampler2D uM9Curve;
uniform bool uM9Enabled;
uniform float uM9DisplayGain;
uniform vec2 uViewSize;
uniform vec2 uFboSize;
uniform vec2 uSharpOrigin;
uniform vec2 uSharpSize;
uniform vec2 uOffsetPx;
uniform float uCos;
uniform float uSin;
uniform bool mirror;
out vec4 Output;

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
    vec2 scale = uViewSize / uFboSize;
    vec3 sum = vec3(0.0);
    float wsum = 0.0;
    for (int i = -8; i <= 8; i++) {
        vec2 viewPx = gl_FragCoord.xy * scale + uOffsetPx * (float(i) / 8.0);
        vec2 rel = viewPx - uSharpOrigin;
        vec2 ndc = rel / max(uSharpSize, vec2(1.0)) * 2.0 - 1.0;
        vec2 q = vec2(ndc.x * uCos + ndc.y * uSin, -ndc.x * uSin + ndc.y * uCos);
        vec2 uv = vec2((1.0 + q.y) * 0.5, (q.x + 1.0) * 0.5);
        if (mirror)
            uv.y = 1.0 - uv.y;
        float w = exp(-0.5 * float(i * i) / 18.0);
        sum += texture(sTexture, clamp(uv, vec2(0.0), vec2(1.0))).rgb * w;
        wsum += w;
    }
    // Transform once after the blur accumulation: fast and visually coherent
    // with the sharp M9 viewfinder.
    Output = vec4(m9DisplayTransform(sum / wsum), 1.0);
}
'''
blur_fs.write_text(blur_shader)

mr = main_renderer.read_text()
if "M9LIVEGL1A_PHOTON_SHADER" in mr:
    raise SystemExit("M9LIVEGL1A MainRenderer already patched")

field_anchor = """    private int resolution;
"""
field_insert = """    private int resolution;

    // M9LIVEGL1A_PHOTON_SHADER
    private static final String M9_LIVE_GL1A_MODE = "PHOTON_OES_PREVIEW_M9_DISPLAY_TRANSFORM";
    // First display-domain calibration, fit against the controller/window
    // Photon->validated-M9 transition. This is intentionally a tunable preview
    // parameter, not a mutation of the still renderer.
    private static final float M9_LIVE_GL1A_DISPLAY_GAIN = 0.40f;
    private int mM9CurveTex;
    private int uM9Enabled;
    private int uM9DisplayGain;
    private int uM9Curve;
    private int uBlurM9Enabled;
    private int uBlurM9DisplayGain;
    private int uBlurM9Curve;
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

sharp_uniform_anchor = """                uSharpOrigin = GLES20.glGetUniformLocation(mSharpProgram, "uSharpOrigin");
                GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
sharp_uniform_insert = """                uSharpOrigin = GLES20.glGetUniformLocation(mSharpProgram, "uSharpOrigin");
                uM9Enabled = GLES20.glGetUniformLocation(mSharpProgram, "uM9Enabled");
                uM9DisplayGain = GLES20.glGetUniformLocation(mSharpProgram, "uM9DisplayGain");
                uM9Curve = GLES20.glGetUniformLocation(mSharpProgram, "uM9Curve");
                GLES20.glVertexAttribPointer(vPosition, 2, GLES20.GL_FLOAT, false, 4 * 2, pVertex);
"""
mr = one(mr, sharp_uniform_anchor, sharp_uniform_insert, "sharp uniform locations")

blur_program_anchor = """            if (mBlurOesProgram == 0) {
                mBlurOesProgram = loadShader(vss_quad, loadAsset("shaders/preview/blur_oes_fs.glsl"));
            }
"""
blur_program_insert = """            if (mBlurOesProgram == 0) {
                mBlurOesProgram = loadShader(vss_quad, loadAsset("shaders/preview/blur_oes_fs.glsl"));
                if (mBlurOesProgram != 0) {
                    uBlurM9Enabled = GLES20.glGetUniformLocation(mBlurOesProgram, "uM9Enabled");
                    uBlurM9DisplayGain = GLES20.glGetUniformLocation(mBlurOesProgram, "uM9DisplayGain");
                    uBlurM9Curve = GLES20.glGetUniformLocation(mBlurOesProgram, "uM9Curve");
                }
            }
"""
mr = one(mr, blur_program_anchor, blur_program_insert, "blur uniform locations")

sharp_draw_anchor = """        GLES20.glUniform2f(uSharpOrigin, sharpLeft, sharpBottom);
        bindQuadAttributes(mSharpProgram);
        // The blur passes bind 2D textures to unit 0; re-bind the camera texture.
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
"""
sharp_draw_insert = """        GLES20.glUniform2f(uSharpOrigin, sharpLeft, sharpBottom);
        GLES20.glUniform1i(uM9Enabled, mM9CurveTex != 0 ? 1 : 0);
        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1i(uM9Curve, 1);
        bindQuadAttributes(mSharpProgram);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, mM9CurveTex);
        // The blur passes bind 2D textures to unit 0; re-bind the camera texture.
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
"""
mr = one(mr, sharp_draw_anchor, sharp_draw_insert, "sharp M9 uniforms")

blur_draw_anchor = """        GLES20.glUniform1i(GLES20.glGetUniformLocation(mBlurOesProgram, "mirror"), mMirrorPreview ? 1 : 0);
        bindQuadAttributes(mBlurOesProgram);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
"""
blur_draw_insert = """        GLES20.glUniform1i(GLES20.glGetUniformLocation(mBlurOesProgram, "mirror"), mMirrorPreview ? 1 : 0);
        GLES20.glUniform1i(uBlurM9Enabled, mM9CurveTex != 0 ? 1 : 0);
        GLES20.glUniform1f(uBlurM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1i(uBlurM9Curve, 1);
        bindQuadAttributes(mBlurOesProgram);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, mM9CurveTex);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
"""
mr = one(mr, blur_draw_anchor, blur_draw_insert, "blur M9 uniforms")

init_tex_anchor = """    private void initTex() {
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
mr = one(mr, init_tex_anchor, curve_method + init_tex_anchor, "curve texture method")

main_renderer.write_text(mr)

# Distinct APK identity.
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
print(" - actual Photon OES viewfinder shader is the live carrier")
print(" - periodic RAW/ImageView renderer disabled")
print(" - exact curve02 uploaded as 2048x1 GL_R8 LUT")
print(" - firmware SAT2 M04/M05 applied in display domain")
print(" - initial display gain 0.40 calibrated against controller/window transition")
print(" - focus-peaking extra samples skipped when peaking is off")
print(" - still M9 renderer untouched by this patch")
