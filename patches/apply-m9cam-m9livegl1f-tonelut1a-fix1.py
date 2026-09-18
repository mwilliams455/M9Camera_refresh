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
