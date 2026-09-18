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
