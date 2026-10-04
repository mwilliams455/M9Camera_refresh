#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1c-appearanceparity.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, main_fs, camera_fragment, controller, renderer, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1C missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1C {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

mr = main_renderer.read_text()
fs = main_fs.read_text()
cf = camera_fragment.read_text()
cc = controller.read_text()
r = renderer.read_text()

# GL1B exposure authority is a frozen prerequisite. GL1C must not re-author it.
for token in (
    "M9LIVEGL1B_EXPOSUREINTENT",
    "uM9ExposureScale1B",
    "setM9ExposureScale1B"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1C missing GL1B MainRenderer token: " + token)
for token in (
    "M9LIVEGL1B_EXPOSUREINTENT",
    "linear *= uM9ExposureScale1B"):
    if token not in fs:
        raise SystemExit("M9LIVEGL1C missing GL1B shader token: " + token)
if "updateM9LiveGlIntendedExposure1B" not in cf:
    raise SystemExit("M9LIVEGL1C missing CameraFragment exposure-intent bridge")
if "Photon_GL_IsoExpoSelector_intended_pair" not in cc:
    raise SystemExit("M9LIVEGL1C missing still exposure-intent authority")
for token in (
    "toneBoundLimitEv1A = 0.5",
    'captureExposureMutation", false'):
    if token not in r:
        raise SystemExit("M9LIVEGL1C expected frozen still-render token missing: " + token)

# ---------------------------------------------------------------------------
# 1) MainRenderer: install a compact preview-state set.
#
# The active colour matrix is not an arbitrary "look" matrix. It is the D65
# slice of the recovered Leica M9 target model expressed as:
#
#   linear sRGB(D65) -> XYZ(D65) -> M9 ColorMatrix2 -> per-channel M9 white norm
#
# Rows were normalized to exact unit response for neutral [1,1,1]. The Java
# array is column-major because glUniformMatrix3fv(transpose=false) requires it.
#
# The still target-falloff contract is currently uncalibrated/identity, so the
# live falloff mechanism is installed but strength remains exactly 0.0.
# ---------------------------------------------------------------------------
field_anchor = """    private int uM9ExposureScale1B;
"""
field_new = field_anchor + """    // M9LIVEGL1C_APPEARANCEPARITY
    private static final float[] M9_LIVE_GL1C_SOURCE_D65 = {
            0.53316906f, 0.09333790f, 0.01986253f,
            0.32894386f, 0.70803917f, 0.28021240f,
            0.13788708f, 0.19862293f, 0.69992507f
    };
    private static final float M9_LIVE_GL1C_BLACK_FLOOR = 0.0030f;
    private static final float M9_LIVE_GL1C_SHADOW_POWER = 1.040f;
    private static final float M9_LIVE_GL1C_HIGHLIGHT_SHOULDER = 0.20f;
    private static final float M9_LIVE_GL1C_FALLOFF_STRENGTH = 0.0f;
    private static final float M9_LIVE_GL1C_FALLOFF_POWER = 2.0f;
    private int uM9SourceMatrix1C;
    private int uM9BlackFloor1C;
    private int uM9ShadowPower1C;
    private int uM9HighlightShoulder1C;
    private int uM9FalloffStrength1C;
    private int uM9FalloffPower1C;
"""
mr = one(mr, field_anchor, field_new, "preview-state fields")

uniform_anchor = """        uM9Curve = GLES20.glGetUniformLocation(hProgram, "uM9Curve");
        uM9ExposureScale1B = GLES20.glGetUniformLocation(hProgram, "uM9ExposureScale1B");
        GLES20.glUniform1i(uM9Curve, 1);
"""
uniform_new = """        uM9Curve = GLES20.glGetUniformLocation(hProgram, "uM9Curve");
        uM9ExposureScale1B = GLES20.glGetUniformLocation(hProgram, "uM9ExposureScale1B");
        uM9SourceMatrix1C = GLES20.glGetUniformLocation(hProgram, "uM9SourceMatrix1C");
        uM9BlackFloor1C = GLES20.glGetUniformLocation(hProgram, "uM9BlackFloor1C");
        uM9ShadowPower1C = GLES20.glGetUniformLocation(hProgram, "uM9ShadowPower1C");
        uM9HighlightShoulder1C = GLES20.glGetUniformLocation(hProgram, "uM9HighlightShoulder1C");
        uM9FalloffStrength1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffStrength1C");
        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffPower1C");
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, uniform_anchor, uniform_new, "preview-state uniform locations")

draw_anchor = """        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1f(uM9ExposureScale1B, mM9ExposureScale1B);
        GLES20.glUniform1i(uM9Curve, 1);
"""
draw_new = """        GLES20.glUniform1f(uM9DisplayGain, M9_LIVE_GL1A_DISPLAY_GAIN);
        GLES20.glUniform1f(uM9ExposureScale1B, mM9ExposureScale1B);
        GLES20.glUniformMatrix3fv(uM9SourceMatrix1C, 1, false, M9_LIVE_GL1C_SOURCE_D65, 0);
        GLES20.glUniform1f(uM9BlackFloor1C, M9_LIVE_GL1C_BLACK_FLOOR);
        GLES20.glUniform1f(uM9ShadowPower1C, M9_LIVE_GL1C_SHADOW_POWER);
        GLES20.glUniform1f(uM9HighlightShoulder1C, M9_LIVE_GL1C_HIGHLIGHT_SHOULDER);
        GLES20.glUniform1f(uM9FalloffStrength1C, M9_LIVE_GL1C_FALLOFF_STRENGTH);
        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, draw_anchor, draw_new, "preview-state uniform upload")

log_anchor = """        Log.d("M9LiveGL1A", "M9LIVEGL1A_PHOTON_SHADER mode=" + M9_LIVE_GL1A_MODE
                + " gain=" + M9_LIVE_GL1A_DISPLAY_GAIN
                + " RAW_LIVE_OVERLAY_DISABLED");
"""
log_new = log_anchor + """        Log.d("M9LiveGL1C", "M9LIVEGL1C_APPEARANCEPARITY"
                + " source=M9_D65_NORMALIZED"
                + " blackFloor=" + M9_LIVE_GL1C_BLACK_FLOOR
                + " shadowPower=" + M9_LIVE_GL1C_SHADOW_POWER
                + " highlightShoulder=" + M9_LIVE_GL1C_HIGHLIGHT_SHOULDER
                + " falloffStrength=" + M9_LIVE_GL1C_FALLOFF_STRENGTH
                + " GL1B_EXPOSURE_FROZEN");
"""
mr = one(mr, log_anchor, log_new, "appearance log")
main_renderer.write_text(mr)

# ---------------------------------------------------------------------------
# 2) Shader: reconstruct the missing M9 target-domain entry before SAT2/curve02.
# Keep the exact GL1B exposure-energy multiplication in the same authority role.
# ---------------------------------------------------------------------------
fs = main_fs.read_text()
uniform_fs_anchor = """uniform float uM9ExposureScale1B;
"""
uniform_fs_new = uniform_fs_anchor + """// M9LIVEGL1C_APPEARANCEPARITY
uniform mat3 uM9SourceMatrix1C;
uniform float uM9BlackFloor1C;
uniform float uM9ShadowPower1C;
uniform float uM9HighlightShoulder1C;
uniform float uM9FalloffStrength1C;
uniform float uM9FalloffPower1C;
"""
fs = one(fs, uniform_fs_anchor, uniform_fs_new, "shader preview-state uniforms")

sat_anchor = """vec3 sat2M9(vec3 c) {
"""
helpers = r'''vec3 sourceToM9Target1C(vec3 linearSrgb) {
    // D65 white-balanced display input -> normalized Leica M9 virtual sensor.
    // Neutral axis is preserved exactly by the row-normalized matrix.
    return max(uM9SourceMatrix1C * linearSrgb, vec3(0.0));
}

vec3 tonePlacement1C(vec3 c) {
    float floor1C = clamp(uM9BlackFloor1C, 0.0, 0.05);
    c = max((c - vec3(floor1C)) / max(1.0 - floor1C, 0.001), vec3(0.0));

    // Photon preview already contains ISP tone placement. A small power restores
    // the denser M9 lower-mid placement before the exact firmware curve02.
    c = pow(c, vec3(max(uM9ShadowPower1C, 0.01)));

    // Soft knee only above 0.65 linear. curve02 remains the final authoritative
    // tone curve; this merely prevents vendor-preview highlights from entering
    // it much harder than the RAW-derived still path.
    float knee1C = 0.65;
    float shoulder1C = max(uM9HighlightShoulder1C, 0.0);
    vec3 over1C = max(c - vec3(knee1C), vec3(0.0));
    vec3 compressed1C = vec3(knee1C) + over1C / (vec3(1.0) + shoulder1C * over1C);
    c = mix(c, compressed1C, step(vec3(knee1C), c));
    return max(c, vec3(0.0));
}

float falloffGain1C(vec2 uv) {
    // Hook is active architecturally but strength is 0 while the frozen still
    // target-falloff coefficients remain uncalibrated/identity.
    vec2 p = uv * 2.0 - 1.0;
    float radius = clamp(length(p) * 0.70710678, 0.0, 1.0);
    float falloff = clamp(uM9FalloffStrength1C, 0.0, 0.95)
            * pow(radius, max(uM9FalloffPower1C, 0.1));
    return 1.0 - falloff;
}

''' + sat_anchor
fs = one(fs, sat_anchor, helpers, "shader appearance helpers")

old_transform = """vec3 m9DisplayTransform(vec3 photonSrgb) {
    if (!uM9Enabled) return photonSrgb;
    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));
    // M9LIVEGL1B_EXPOSUREINTENT: represent the exact non-ZSL shutter/ISO pair
    // rather than the hardware-AE preview energy.
    linear *= uM9ExposureScale1B;
    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    return vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
}
"""
new_transform = """vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv) {
    if (!uM9Enabled) return photonSrgb;
    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));

    // M9LIVEGL1C_APPEARANCEPARITY: enter the same recovered M9 target family
    // before the existing exposure intent, SAT2 and exact curve02 stages.
    linear = sourceToM9Target1C(linear);

    // M9LIVEGL1B_EXPOSUREINTENT stays authoritative and unchanged.
    linear *= uM9ExposureScale1B;

    linear = tonePlacement1C(linear);
    linear *= falloffGain1C(uv);

    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    return vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
}
"""
fs = one(fs, old_transform, new_transform, "shader target-domain transform")

call_anchor = """    vec4 photonColor = texture(sTexture, uv);
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb), 1.0);
"""
call_new = """    vec4 photonColor = texture(sTexture, uv);
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb, uv), 1.0);
"""
fs = one(fs, call_anchor, call_new, "shader transform call")
main_fs.write_text(fs)

# Build identity only; no still-render source is written by this patch.
g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("versionName "):
        if "m9livegl1c" not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len("versionName "):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit("M9LIVEGL1C unsupported versionName syntax: " + line)
            base = value[1:-1]
            lines[i] = prefix + "versionName " + quote + base + "-m9livegl1c-appearanceparity" + quote
            changed = True
        break
else:
    raise SystemExit("M9LIVEGL1C versionName missing")
if changed:
    gradle.write_text("\n".join(lines) + ("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1C_APPEARANCEPARITY applied")
print(" - GL1B IsoExpoSelector exposure authority preserved exactly")
print(" - added neutral-preserving D65 linear-sRGB -> Leica M9 target matrix")
print(" - added bounded black-floor / lower-mid / highlight-knee preview shaping")
print(" - added target-falloff hook with strength 0.0 because still target falloff is identity")
print(" - SAT2 M04/M05 and exact curve02 preview stages retained")
print(" - still M9 photographic renderer untouched")
