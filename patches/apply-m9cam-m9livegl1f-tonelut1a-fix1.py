#!/usr/bin/env python3
import base64
import sys
import zlib
from pathlib import Path

base = Path(__file__).with_name("apply-m9cam-m9livegl1f-tonelut1a.py")
text = base.read_text()
marker = "b64decode('"
start = text.find(marker)
if start < 0:
    raise SystemExit("GL1F base loader payload start not found")
start += len(marker)
end = text.find("')", start)
if end < 0:
    raise SystemExit("GL1F base loader payload end not found")
src = zlib.decompress(base64.b64decode(text[start:end])).decode()

old_uniform = """uniform_anchor = '''        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, \"uM9FalloffPower1C\");
        GLES20.glUniform1i(uM9Curve, 1);
'''
uniform_new = '''        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, \"uM9FalloffPower1C\");
        uM9PreviewGainEv1F = GLES20.glGetUniformLocation(hProgram, \"uM9PreviewGainEv1F\");
"""
new_uniform = """uniform_anchor = '''        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, \"uM9FalloffPower1C\");
        uM9SourceMatrixA1D = GLES20.glGetUniformLocation(hProgram, \"uM9SourceMatrixA1D\");
        uM9IlluminantWeightA1D = GLES20.glGetUniformLocation(hProgram, \"uM9IlluminantWeightA1D\");
        uM9TungstenWeight1D = GLES20.glGetUniformLocation(hProgram, \"uM9TungstenWeight1D\");
        GLES20.glUniform1i(uM9Curve, 1);
'''
uniform_new = '''        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, \"uM9FalloffPower1C\");
        uM9SourceMatrixA1D = GLES20.glGetUniformLocation(hProgram, \"uM9SourceMatrixA1D\");
        uM9IlluminantWeightA1D = GLES20.glGetUniformLocation(hProgram, \"uM9IlluminantWeightA1D\");
        uM9TungstenWeight1D = GLES20.glGetUniformLocation(hProgram, \"uM9TungstenWeight1D\");
        uM9PreviewGainEv1F = GLES20.glGetUniformLocation(hProgram, \"uM9PreviewGainEv1F\");
"""

old_draw = """draw_anchor = '''        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniform1i(uM9Curve, 1);
'''
draw_new = '''        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniform1f(uM9PreviewGainEv1F, mM9PreviewGainEv1F);
"""
new_draw = """draw_anchor = '''        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniformMatrix3fv(uM9SourceMatrixA1D, 1, false, M9_LIVE_GL1D_SOURCE_A, 0);
        GLES20.glUniform1f(uM9IlluminantWeightA1D, mM9IlluminantWeightA1D);
        GLES20.glUniform1f(uM9TungstenWeight1D, mM9TungstenWeight1D);
        GLES20.glUniform1i(uM9Curve, 1);
'''
draw_new = '''        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniformMatrix3fv(uM9SourceMatrixA1D, 1, false, M9_LIVE_GL1D_SOURCE_A, 0);
        GLES20.glUniform1f(uM9IlluminantWeightA1D, mM9IlluminantWeightA1D);
        GLES20.glUniform1f(uM9TungstenWeight1D, mM9TungstenWeight1D);
        GLES20.glUniform1f(uM9PreviewGainEv1F, mM9PreviewGainEv1F);
"""

for label, old, new in (
    ("uniform", old_uniform, new_uniform),
    ("draw", old_draw, new_draw),
):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f"GL1F FIX1 {label} patch-source anchor count={count}")
    src = src.replace(old, new, 1)

exec(compile(src, "apply_gl1f_fix1.py", "exec"))

# M9LIVEGL1F_LUTPACK1
# Base asset is emitted in conventional .cube traversal [B][G][R], R fastest.
# The shader's 2-sample tiled layout expects image memory [G row][B tile][R].
# Repack the raw RGB8 asset so shader coordinates and file layout agree.
root = Path(sys.argv[1]).resolve()
lut_path = root / "app/src/main/assets/m9/m9_preview_standard_gl1f_17.rgb"
raw = lut_path.read_bytes()
n = 17
expected = n * n * n * 3
if len(raw) != expected:
    raise SystemExit(f"GL1F LUTPACK1 raw size={len(raw)} expected={expected}")
packed = bytearray(expected)
for b in range(n):
    for g in range(n):
        for r in range(n):
            src_pixel = ((b * n + g) * n + r)
            dst_pixel = (g * n * n + b * n + r)
            so = src_pixel * 3
            do = dst_pixel * 3
            packed[do:do+3] = raw[so:so+3]
lut_path.write_bytes(packed)
print("M9LIVEGL1F_LUTPACK1 applied: canonical [B][G][R] -> texture [G][B][R]")

# M9LIVEGL1F_UNPACK1
# The packed 17^3 LUT is uploaded as a 289x17 RGB8 texture. Each source row is
# 289*3 = 867 bytes, which is not compatible with OpenGL ES's default
# GL_UNPACK_ALIGNMENT=4. Force byte alignment for the upload, then restore 4.
root = Path(sys.argv[1]).resolve()
main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
old_upload = """        // 17 blue slices are tiled horizontally; R varies within a tile, G vertically.
        GLES30.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES30.GL_RGB8,
                M9_LIVE_GL1F_LUT_SIZE * M9_LIVE_GL1F_LUT_SIZE,
                M9_LIVE_GL1F_LUT_SIZE, 0,
                GLES20.GL_RGB, GLES20.GL_UNSIGNED_BYTE, data);
"""
new_upload = """        // M9LIVEGL1F_UNPACK1
        // 289x17 RGB8 => 867 bytes/row. Default GL_UNPACK_ALIGNMENT=4 would
        // advance rows as if padded to 868 bytes, corrupting RGB after row 0.
        GLES20.glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 1);
        // 17 blue slices are tiled horizontally; R varies within a tile, G vertically.
        GLES30.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES30.GL_RGB8,
                M9_LIVE_GL1F_LUT_SIZE * M9_LIVE_GL1F_LUT_SIZE,
                M9_LIVE_GL1F_LUT_SIZE, 0,
                GLES20.GL_RGB, GLES20.GL_UNSIGNED_BYTE, data);
        GLES20.glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 4);
        Log.d("M9LiveGL1F", "M9LIVEGL1F_UNPACK1 rowBytes=867 unpackAlignment=1");\n        Log.d("M9LiveGL1F", "M9LIVEGL1F_LUTPACK1 layout=G_rows_B_tiles_R_inner");
"""
count = main.count(old_upload)
if count != 1:
    raise SystemExit(f"GL1F UNPACK1 upload anchor count={count}")
main_path.write_text(main.replace(old_upload, new_upload, 1))
print("M9LIVEGL1F_UNPACK1 applied: RGB8 rowBytes=867 uses GL_UNPACK_ALIGNMENT=1")



# M9LIVEGL1G_DISPLAYDELTA1A
# Paired device evidence shows that applying fixed 0.40 linear gain + exact
# curve02 to Photon OES double-tones an already display-rendered preview.
# Keep GL1B exposure authority, but return to display space without re-running
# the still curve. This is the clean baseline for a calibrated residual delta.
root = Path(sys.argv[1]).resolve()
shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()

helper_anchor = """vec3 srgbToLinearM9(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow((c + vec3(0.055)) / 1.055, vec3(2.4));
    return mix(lo, hi, step(vec3(0.04045), c));
}
"""
helper_new = helper_anchor + """
vec3 linearToSrgbM9(vec3 c) {
    c = max(c, vec3(0.0));
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(c, vec3(1.0 / 2.4)) - vec3(0.055);
    return mix(lo, hi, step(vec3(0.0031308), c));
}
"""
if shader.count(helper_anchor) != 1:
    raise SystemExit("GL1G helper anchor count=" + str(shader.count(helper_anchor)))
shader = shader.replace(helper_anchor, helper_new, 1)

old_transform = """    // M9LIVEGL1F_TONELUT1A
    // Keep GL1E's validated display-domain colour boundary: no sensor matrix,
    // firmware SAT2, or TG1 is called on the already-rendered OES texture.
    // GL1B exposure intent remains the first photographic authority.
    linear *= uM9ExposureScale1B;

    // Dynamic scene placement predicts the still tone decision without executing
    // the RAW renderer. The falloff hook remains frozen/identity.
    linear = tonePlacement1F(linear);
    linear *= falloffGain1C(uv);

    vec3 toned1F = clamp(linear * uM9DisplayGain, vec3(0.0), vec3(1.0));
    vec3 curved1F = vec3(curve02M9(toned1F.r),
                         curve02M9(toned1F.g),
                         curve02M9(toned1F.b));

    // Colour only: display-domain Standard prototype after exact curve02.
    return previewLut1F(curved1F);
"""
new_transform = """    // M9LIVEGL1G_DISPLAYDELTA1A
    // Photon OES is already display-rendered. Re-applying the fixed 0.40 gain
    // and exact still curve02 double-toned the live image (paired validation:
    // crushed shadows, excessive contrast). Preserve only intended exposure
    // here; subsequent M9 appearance work must be a calibrated display delta.
    linear *= uM9ExposureScale1B;
    linear *= falloffGain1C(uv);
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
if shader.count(old_transform) != 1:
    raise SystemExit("GL1G active transform anchor count=" + str(shader.count(old_transform)))
shader = shader.replace(old_transform, new_transform, 1)
shader_path.write_text(shader)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
log_anchor = 'Log.d("M9LiveGL1F", "M9LIVEGL1F_LUTPACK1 layout=G_rows_B_tiles_R_inner");'
if log_anchor in main:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1G", "M9LIVEGL1G_DISPLAYDELTA1A active=EXPOSURE_ONLY curve02_live=false lut_live=false displayGain040_live=false");', 1)
else:
    # Marker may live in the texture-init log block in reconstructed parent.
    marker = 'M9LIVEGL1F_TONELUT1A LUT=STANDARD_PROTOTYPE_17'
    if marker not in main:
        raise SystemExit("GL1G MainRenderer log anchor missing")
    main = main.replace(marker, marker + ' M9LIVEGL1G_DISPLAYDELTA1A', 1)
main_path.write_text(main)
print("M9LIVEGL1G_DISPLAYDELTA1A applied: OES + GL1B exposure, no live curve02/0.40/LUT")


# M9LIVEGL1H_LUMAGAMMA1A
# Paired GL1G device validation (14685 preview vs 14686 output) shows colour
# chroma is already close but live shadows/midtones remain too bright while
# highlights are near parity. A luminance-only linear-light gamma preserves
# colour direction and leaves white fixed.
root = Path(sys.argv[1]).resolve()
shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()

old_transform = """    // M9LIVEGL1G_DISPLAYDELTA1A
    // Photon OES is already display-rendered. Re-applying the fixed 0.40 gain
    // and exact still curve02 double-toned the live image (paired validation:
    // crushed shadows, excessive contrast). Preserve only intended exposure
    // here; subsequent M9 appearance work must be a calibrated display delta.
    linear *= uM9ExposureScale1B;
    linear *= falloffGain1C(uv);
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
new_transform = """    // M9LIVEGL1H_LUMAGAMMA1A
    // Photon OES is already display-rendered. Preserve GL1B intended exposure,
    // then apply the measured residual as luminance only. 1.22 was fitted from
    // the aligned GL1G preview/output pair: it darkens mids/shadows while
    // leaving the white point fixed and avoids per-channel hue distortion.
    linear *= uM9ExposureScale1B;
    linear *= falloffGain1C(uv);
    float y1H = max(dot(linear, vec3(0.2126, 0.7152, 0.0722)), 1e-6);
    float y1HTarget = pow(y1H, 1.22);
    linear *= y1HTarget / y1H;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
if shader.count(old_transform) != 1:
    raise SystemExit("GL1H active transform anchor count=" + str(shader.count(old_transform)))
shader = shader.replace(old_transform, new_transform, 1)
shader_path.write_text(shader)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
log_anchor = 'Log.d("M9LiveGL1G", "M9LIVEGL1G_DISPLAYDELTA1A active=EXPOSURE_ONLY curve02_live=false lut_live=false displayGain040_live=false");'
if log_anchor in main:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1H", "M9LIVEGL1H_LUMAGAMMA1A gamma=1.22 chromaPreserving=true curve02_live=false lut_live=false");', 1)
else:
    marker = 'M9LIVEGL1G_DISPLAYDELTA1A'
    if marker not in main:
        raise SystemExit("GL1H MainRenderer log anchor missing")
    main = main.replace(marker, marker + ' M9LIVEGL1H_LUMAGAMMA1A', 1)
main_path.write_text(main)
print("M9LIVEGL1H_LUMAGAMMA1A applied: linear-light luminance gamma=1.22, chroma-preserving")


# M9LIVEGL1I_SCENEKEY1A
# Two paired device validations show the residual preview->JPEG mapping is
# scene-dependent. Reuse the existing live backlight/highlight classifier and
# drive only a display-domain luma gain + gamma delta.
root = Path(sys.argv[1]).resolve()

tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
tone = tone_path.read_text()
tone = tone.replace("public static final float DEFAULT_GAIN_EV = 0.0f;",
                    "public static final float DEFAULT_GAIN_EV = -0.30f;")
tone = tone.replace("public static final float DEFAULT_GAMMA = 1.040f;",
                    "public static final float DEFAULT_GAMMA = 1.120f;")

old_gain = """        // Match the still path's restrained normalization philosophy: live predictive
        // gain remains narrower than TONEBOUND050's +/-0.5 EV authority.
        double gainEv = 0.10 * shadowNeed + 0.08 * backlit
                - 0.20 * highlightPressure - 0.05 * lowKey;
        gainEv = clamp(gainEv, -0.30, 0.20);
"""
new_gain = """        // M9LIVEGL1I_SCENEKEY1A
        // Paired live/final device frames establish two anchors:
        // ordinary-key: ~-0.30 EV, gamma ~1.12
        // backlit/highlight-pressure: ~-2.25 EV, gamma ~1.29.
        // Blend the already-proven classifiers rather than introducing a second
        // scene detector. This is a display delta only; capture/still remain frozen.
        final double sceneKey1I = clamp01(0.65 * backlit + 0.35 * highlightPressure);
        double gainEv = -0.30 - 3.00 * sceneKey1I;
        gainEv = clamp(gainEv, -2.50, -0.25);
"""
if tone.count(old_gain) != 1:
    raise SystemExit("GL1I gain anchor count=" + str(tone.count(old_gain)))
tone = tone.replace(old_gain, new_gain, 1)

old_gamma = """        // GL1C's 1.040 power remains the neutral/default state.
        double gamma = DEFAULT_GAMMA
                - 0.025 * shadowNeed - 0.030 * backlit
                + 0.020 * lowKey + 0.022 * flatMid + 0.020 * highlightPressure;
        gamma = clamp(gamma, 0.985, 1.095);
"""
new_gamma = """        // Chroma-preserving residual contrast. The scene-key fit is intentionally
        // modest; the large scene change is carried by gain, not by crushing black.
        double gamma = 1.12 + 0.26 * sceneKey1I;
        gamma = clamp(gamma, 1.10, 1.32);
"""
if tone.count(old_gamma) != 1:
    raise SystemExit("GL1I gamma anchor count=" + str(tone.count(old_gamma)))
tone = tone.replace(old_gamma, new_gamma, 1)
tone_path.write_text(tone)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
main = main.replace("private volatile float mM9PreviewGainEv1F = 0.0f;",
                    "private volatile float mM9PreviewGainEv1F = -0.30f;")
main = main.replace("private volatile float mM9MidtoneGamma1F = 1.040f;",
                    "private volatile float mM9MidtoneGamma1F = 1.120f;")
main = main.replace("if (!Float.isFinite(gainEv)) gainEv = 0.0f;",
                    "if (!Float.isFinite(gainEv)) gainEv = -0.30f;")
main = main.replace("if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.040f;",
                    "if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.120f;")
main = main.replace("mM9PreviewGainEv1F = Math.max(-0.50f, Math.min(0.50f, gainEv));",
                    "mM9PreviewGainEv1F = Math.max(-2.50f, Math.min(0.50f, gainEv));")
main = main.replace("mM9MidtoneGamma1F = Math.max(0.90f, Math.min(1.15f, midtoneGamma));",
                    "mM9MidtoneGamma1F = Math.max(1.00f, Math.min(1.40f, midtoneGamma));")
log_anchor = 'Log.d("M9LiveGL1H", "M9LIVEGL1H_LUMAGAMMA1A gamma=1.22 chromaPreserving=true curve02_live=false lut_live=false");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1I", "M9LIVEGL1I_SCENEKEY1A gain=[-2.50,-0.25] gamma=[1.10,1.32] displayDeltaOnly=true");', 1)
else:
    raise SystemExit("GL1I log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
old_transform = """    // M9LIVEGL1H_LUMAGAMMA1A
    // Photon OES is already display-rendered. Preserve GL1B intended exposure,
    // then apply the measured residual as luminance only. 1.22 was fitted from
    // the aligned GL1G preview/output pair: it darkens mids/shadows while
    // leaving the white point fixed and avoids per-channel hue distortion.
    linear *= uM9ExposureScale1B;
    linear *= falloffGain1C(uv);
    float y1H = max(dot(linear, vec3(0.2126, 0.7152, 0.0722)), 1e-6);
    float y1HTarget = pow(y1H, 1.22);
    linear *= y1HTarget / y1H;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
new_transform = """    // M9LIVEGL1I_SCENEKEY1A
    // Photon OES is already display-rendered. GL1B remains exposure authority.
    // Apply only the scene-aware residual fitted from paired preview/final frames.
    linear *= uM9ExposureScale1B;
    linear *= falloffGain1C(uv);
    float y1I = max(dot(linear, vec3(0.2126, 0.7152, 0.0722)), 1e-6);
    float gamma1I = clamp(uM9MidtoneGamma1F, 1.00, 1.40);
    float gain1I = exp2(clamp(uM9PreviewGainEv1F, -2.50, 0.50));
    float y1ITarget = gain1I * pow(y1I, gamma1I);
    linear *= y1ITarget / y1I;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
if shader.count(old_transform) != 1:
    raise SystemExit("GL1I active transform anchor count=" + str(shader.count(old_transform)))
shader = shader.replace(old_transform, new_transform, 1)
shader_path.write_text(shader)
print("M9LIVEGL1I_SCENEKEY1A applied: live scene-key gain/gamma display delta")


# M9LIVEGL1J_DUALDEVICE1A
# Cross-device paired validation: Xiaomi 15 Ultra and 17 Ultra show the same
# GL1I residual (~+1.2 EV and ~+1.1 EV final-vs-preview median respectively).
# Therefore keep the portable classifier but reduce scene-key gain strength.
root = Path(sys.argv[1]).resolve()

tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
tone = tone_path.read_text()
old_gain = """        double gainEv = -0.30 - 3.00 * sceneKey1I;
        gainEv = clamp(gainEv, -2.50, -0.25);
"""
new_gain = """        // M9LIVEGL1J_DUALDEVICE1A
        // 15U/17U same-scene validation shows GL1I over-dark by ~1.1 EV on
        // both devices. Preserve scene-key ordering, reduce only its amplitude.
        double gainEv = -0.30 - 1.40 * sceneKey1I;
        gainEv = clamp(gainEv, -1.50, -0.25);
"""
if tone.count(old_gain) != 1:
    raise SystemExit("GL1J gain anchor count=" + str(tone.count(old_gain)))
tone = tone.replace(old_gain, new_gain, 1)
tone_path.write_text(tone)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
main = main.replace("mM9PreviewGainEv1F = Math.max(-2.50f, Math.min(0.50f, gainEv));",
                    "mM9PreviewGainEv1F = Math.max(-1.50f, Math.min(0.50f, gainEv));")
log_anchor = 'Log.d("M9LiveGL1I", "M9LIVEGL1I_SCENEKEY1A gain=[-2.50,-0.25] gamma=[1.10,1.32] displayDeltaOnly=true");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1J", "M9LIVEGL1J_DUALDEVICE1A gain=[-1.50,-0.25] sceneKeySlope=1.40 calibrated15U17U=true");', 1)
else:
    raise SystemExit("GL1J log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
shader = shader.replace("// M9LIVEGL1I_SCENEKEY1A",
                        "// M9LIVEGL1J_DUALDEVICE1A\n    // GL1I classifier retained; gain amplitude recalibrated from 15U + 17U pairs.")
shader = shader.replace("exp2(clamp(uM9PreviewGainEv1F, -2.50, 0.50))",
                        "exp2(clamp(uM9PreviewGainEv1F, -1.50, 0.50))")
shader_path.write_text(shader)
print("M9LIVEGL1J_DUALDEVICE1A applied: GL1I classifier retained, gain slope 3.00 -> 1.40")


# M9LIVEGL1K_PIVOTGAMMA1A
# GL1J 17U aligned fit shows the residual is primarily contrast, not exposure:
# y_final ~= 2.37 * y_preview^2.26, whose fixed point is ~0.50 linear.
# Drive scene-key contrast around that fixed pivot instead of global darkening.
root = Path(sys.argv[1]).resolve()

tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
tone = tone_path.read_text()
tone = tone.replace("public static final float DEFAULT_GAIN_EV = -0.30f;",
                    "public static final float DEFAULT_GAIN_EV = 0.20f;")
tone = tone.replace("public static final float DEFAULT_GAMMA = 1.120f;",
                    "public static final float DEFAULT_GAMMA = 1.200f;")

old_gain = """        double gainEv = -0.30 - 1.40 * sceneKey1I;
        gainEv = clamp(gainEv, -1.50, -0.25);
"""
new_gain = """        // M9LIVEGL1K_PIVOTGAMMA1A
        // Preserve a 0.50 linear-light pivot. For y' = gain * y^gamma,
        // gainEv = gamma - 1 exactly keeps y=0.5 fixed.
        final double gamma1K = clamp(1.20 + 1.10 * sceneKey1I, 1.18, 2.30);
        double gainEv = gamma1K - 1.0;
        gainEv = clamp(gainEv, 0.18, 1.30);
"""
if tone.count(old_gain) != 1:
    raise SystemExit("GL1K gain anchor count=" + str(tone.count(old_gain)))
tone = tone.replace(old_gain, new_gain, 1)

old_gamma = """        // Chroma-preserving residual contrast. The scene-key fit is intentionally
        // modest; the large scene change is carried by gain, not by crushing black.
        double gamma = 1.12 + 0.26 * sceneKey1I;
        gamma = clamp(gamma, 1.10, 1.32);
"""
new_gamma = """        // Scene-key now controls contrast around the 0.50 pivot; no independent
        // exposure darkening. Strong backlight can reach the measured ~2.25 fit.
        double gamma = gamma1K;
"""
if tone.count(old_gamma) != 1:
    raise SystemExit("GL1K gamma anchor count=" + str(tone.count(old_gamma)))
tone = tone.replace(old_gamma, new_gamma, 1)
tone_path.write_text(tone)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
main = main.replace("private volatile float mM9PreviewGainEv1F = -0.30f;",
                    "private volatile float mM9PreviewGainEv1F = 0.20f;")
main = main.replace("private volatile float mM9MidtoneGamma1F = 1.120f;",
                    "private volatile float mM9MidtoneGamma1F = 1.200f;")
main = main.replace("if (!Float.isFinite(gainEv)) gainEv = -0.30f;",
                    "if (!Float.isFinite(gainEv)) gainEv = 0.20f;")
main = main.replace("if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.120f;",
                    "if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.200f;")
main = main.replace("mM9PreviewGainEv1F = Math.max(-1.50f, Math.min(0.50f, gainEv));",
                    "mM9PreviewGainEv1F = Math.max(0.00f, Math.min(1.50f, gainEv));")
main = main.replace("mM9MidtoneGamma1F = Math.max(1.00f, Math.min(1.40f, midtoneGamma));",
                    "mM9MidtoneGamma1F = Math.max(1.00f, Math.min(2.40f, midtoneGamma));")
log_anchor = 'Log.d("M9LiveGL1J", "M9LIVEGL1J_DUALDEVICE1A gain=[-1.50,-0.25] sceneKeySlope=1.40 calibrated15U17U=true");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1K", "M9LIVEGL1K_PIVOTGAMMA1A pivot=0.50 gamma=[1.18,2.30] gainEv=gammaMinus1 chromaPreserving=true");', 1)
else:
    raise SystemExit("GL1K log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
shader = shader.replace("// M9LIVEGL1J_DUALDEVICE1A\n    // GL1I classifier retained; gain amplitude recalibrated from 15U + 17U pairs.",
                        "// M9LIVEGL1K_PIVOTGAMMA1A\n    // Scene-key contrast around a 0.50 linear pivot; no global darkening.")
shader = shader.replace("float gamma1I = clamp(uM9MidtoneGamma1F, 1.00, 1.40);",
                        "float gamma1I = clamp(uM9MidtoneGamma1F, 1.00, 2.40);")
shader = shader.replace("float gain1I = exp2(clamp(uM9PreviewGainEv1F, -1.50, 0.50));",
                        "float gain1I = exp2(clamp(uM9PreviewGainEv1F, 0.00, 1.50));")
shader_path.write_text(shader)
print("M9LIVEGL1K_PIVOTGAMMA1A applied: scene-key contrast around 0.50 linear pivot")


# M9LIVEGL1L_BRACKETFIT1A
# GL1I and GL1J bracket the target on the same 17 Ultra scene:
# GL1I residual ~= +0.99 EV (preview too dark), slope=3.00
# GL1J residual ~= -1.52 EV (preview too bright), slope=1.40
# Linear zero-crossing gives slope ~= 2.37. Revert GL1K pivot experiment and
# restore the GL1I/J display-delta architecture at the bracket-fit strength.
root = Path(sys.argv[1]).resolve()

tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
tone = tone_path.read_text()
tone = tone.replace("public static final float DEFAULT_GAIN_EV = 0.20f;",
                    "public static final float DEFAULT_GAIN_EV = -0.30f;")
tone = tone.replace("public static final float DEFAULT_GAMMA = 1.200f;",
                    "public static final float DEFAULT_GAMMA = 1.120f;")

old_gain = """        final double gamma1K = clamp(1.20 + 1.10 * sceneKey1I, 1.18, 2.30);
        double gainEv = gamma1K - 1.0;
        gainEv = clamp(gainEv, 0.18, 1.30);
"""
new_gain = """        // M9LIVEGL1L_BRACKETFIT1A
        // Same-scene GL1I/GL1J residual interpolation zero-crosses at slope 2.37.
        double gainEv = -0.30 - 2.37 * sceneKey1I;
        gainEv = clamp(gainEv, -2.40, -0.25);
"""
if tone.count(old_gain) != 1:
    raise SystemExit("GL1L gain anchor count=" + str(tone.count(old_gain)))
tone = tone.replace(old_gain, new_gain, 1)

old_gamma = """        // Scene-key now controls contrast around the 0.50 pivot; no independent
        // exposure darkening. Strong backlight can reach the measured ~2.25 fit.
        double gamma = gamma1K;
"""
new_gamma = """        // Return to the GL1I/J modest chroma-preserving gamma. The bracket fit
        // is carried by scene-key gain, not a new contrast architecture.
        double gamma = 1.12 + 0.26 * sceneKey1I;
        gamma = clamp(gamma, 1.10, 1.32);
"""
if tone.count(old_gamma) != 1:
    raise SystemExit("GL1L gamma anchor count=" + str(tone.count(old_gamma)))
tone = tone.replace(old_gamma, new_gamma, 1)
tone_path.write_text(tone)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
main = main.replace("private volatile float mM9PreviewGainEv1F = 0.20f;",
                    "private volatile float mM9PreviewGainEv1F = -0.30f;")
main = main.replace("private volatile float mM9MidtoneGamma1F = 1.200f;",
                    "private volatile float mM9MidtoneGamma1F = 1.120f;")
main = main.replace("if (!Float.isFinite(gainEv)) gainEv = 0.20f;",
                    "if (!Float.isFinite(gainEv)) gainEv = -0.30f;")
main = main.replace("if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.200f;",
                    "if (!Float.isFinite(midtoneGamma)) midtoneGamma = 1.120f;")
main = main.replace("mM9PreviewGainEv1F = Math.max(0.00f, Math.min(1.50f, gainEv));",
                    "mM9PreviewGainEv1F = Math.max(-2.40f, Math.min(0.50f, gainEv));")
main = main.replace("mM9MidtoneGamma1F = Math.max(1.00f, Math.min(2.40f, midtoneGamma));",
                    "mM9MidtoneGamma1F = Math.max(1.00f, Math.min(1.40f, midtoneGamma));")
log_anchor = 'Log.d("M9LiveGL1K", "M9LIVEGL1K_PIVOTGAMMA1A pivot=0.50 gamma=[1.18,2.30] gainEv=gammaMinus1 chromaPreserving=true");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1L", "M9LIVEGL1L_BRACKETFIT1A sceneKeySlope=2.37 gain=[-2.40,-0.25] gamma=[1.10,1.32] bracket17U=true");', 1)
else:
    raise SystemExit("GL1L log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
shader = shader.replace("// M9LIVEGL1K_PIVOTGAMMA1A\n    // Scene-key contrast around a 0.50 linear pivot; no global darkening.",
                        "// M9LIVEGL1L_BRACKETFIT1A\n    // GL1I/J architecture restored at the measured zero-crossing gain strength.")
shader = shader.replace("float gamma1I = clamp(uM9MidtoneGamma1F, 1.00, 2.40);",
                        "float gamma1I = clamp(uM9MidtoneGamma1F, 1.00, 1.40);")
shader = shader.replace("float gain1I = exp2(clamp(uM9PreviewGainEv1F, 0.00, 1.50));",
                        "float gain1I = exp2(clamp(uM9PreviewGainEv1F, -2.40, 0.50));")
shader_path.write_text(shader)
print("M9LIVEGL1L_BRACKETFIT1A applied: GL1I/J zero-crossing slope=2.37")


# M9LIVEGL1M_BRACKETREFINE1A
# Same-scene 17U bracket:
# GL1J slope=1.40 -> residual -0.99 EV (preview too bright)
# GL1L slope=2.37 -> residual +0.56 EV (preview too dark)
# Linear zero-crossing => slope ~= 2.02.
root = Path(sys.argv[1]).resolve()

tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
tone = tone_path.read_text()
old = "double gainEv = -0.30 - 2.37 * sceneKey1I;"
new = """// M9LIVEGL1M_BRACKETREFINE1A
        double gainEv = -0.30 - 2.02 * sceneKey1I;"""
if tone.count(old) != 1:
    raise SystemExit("GL1M slope anchor count=" + str(tone.count(old)))
tone = tone.replace(old, new, 1)
tone_path.write_text(tone)

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
log_anchor = 'Log.d("M9LiveGL1L", "M9LIVEGL1L_BRACKETFIT1A sceneKeySlope=2.37 gain=[-2.40,-0.25] gamma=[1.10,1.32] bracket17U=true");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1M", "M9LIVEGL1M_BRACKETREFINE1A sceneKeySlope=2.02 sameScene17U=true");', 1)
else:
    raise SystemExit("GL1M log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
shader = shader.replace("// M9LIVEGL1L_BRACKETFIT1A",
                        "// M9LIVEGL1M_BRACKETREFINE1A\n    // GL1J/GL1L same-scene zero-crossing slope=2.02.")
shader_path.write_text(shader)
print("M9LIVEGL1M_BRACKETREFINE1A applied: sceneKey slope 2.37 -> 2.02")


# M9LIVEGL1N_LOWPIVOT1A
# GL1M aligned 17U fit: y_final ~= 5.98 * y_preview^1.675,
# giving a fixed point near 0.071 linear. Apply this as a scene-weighted
# residual contrast stage after the GL1M exposure/tone delta.
root = Path(sys.argv[1]).resolve()

main_path = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main = main_path.read_text()
log_anchor = 'Log.d("M9LiveGL1M", "M9LIVEGL1M_BRACKETREFINE1A sceneKeySlope=2.02 sameScene17U=true");'
if main.count(log_anchor) == 1:
    main = main.replace(log_anchor, log_anchor + '\n        Log.d("M9LiveGL1N", "M9LIVEGL1N_LOWPIVOT1A pivotLinear=0.071 residualGammaMax=1.675 sceneWeighted=true chromaPreserving=true");', 1)
else:
    raise SystemExit("GL1N log anchor count=" + str(main.count(log_anchor)))
main_path.write_text(main)

shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
shader = shader_path.read_text()
old = """    float y1ITarget = gain1I * pow(y1I, gamma1I);
    linear *= y1ITarget / y1I;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
new = """    float y1ITarget = gain1I * pow(y1I, gamma1I);

    // M9LIVEGL1N_LOWPIVOT1A
    // Derive scene strength from the already-smoothed GL1I/J/M gamma authority.
    // Strong backlight receives the measured residual contrast; ordinary scenes
    // remain close to identity. 0.071 linear is the measured fixed point.
    float scene1N = clamp((gamma1I - 1.12) / 0.26, 0.0, 1.0);
    float residualGamma1N = mix(1.0, 1.675, scene1N);
    const float pivot1N = 0.071;
    float y1N = pivot1N * pow(max(y1ITarget, 1e-6) / pivot1N, residualGamma1N);

    linear *= y1N / y1I;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
"""
if shader.count(old) != 1:
    raise SystemExit("GL1N shader anchor count=" + str(shader.count(old)))
shader = shader.replace(old, new, 1)
shader = shader.replace("// M9LIVEGL1M_BRACKETREFINE1A",
                        "// M9LIVEGL1N_LOWPIVOT1A\n    // GL1M gain retained; measured low-pivot residual contrast added.")
shader_path.write_text(shader)
print("M9LIVEGL1N_LOWPIVOT1A applied: pivot=0.071 residualGammaMax=1.675")
