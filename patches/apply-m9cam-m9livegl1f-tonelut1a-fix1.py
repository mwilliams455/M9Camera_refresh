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
        Log.d("M9LiveGL1F", "M9LIVEGL1F_UNPACK1 rowBytes=867 unpackAlignment=1");
"""
count = main.count(old_upload)
if count != 1:
    raise SystemExit(f"GL1F UNPACK1 upload anchor count={count}")
main_path.write_text(main.replace(old_upload, new_upload, 1))
print("M9LIVEGL1F_UNPACK1 applied: RGB8 rowBytes=867 uses GL_UNPACK_ALIGNMENT=1")

