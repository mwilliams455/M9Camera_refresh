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
