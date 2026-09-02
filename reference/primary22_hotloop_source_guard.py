#!/usr/bin/env python3
"""PRIMARY2.2 source guard: hot-loop structure only; no runtime Android timing."""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit('usage: primary22_hotloop_source_guard.py <M9R35Renderer.java>')
s=Path(sys.argv[1]).read_text()
cam=s[s.index('    private static void cameraToM9('):s.index('    private static int m9CurvePixel', s.index('    private static void cameraToM9('))]
hsm=s[s.index('    private static void applyHsm('):s.index('    private static double[] normalizedPpToXyz()', s.index('    private static void applyHsm('))]
assert 'ctx.ppToM9' in cam
assert 'PP_TO_XYZ[' not in cam
assert 'ctx.adapt50ToScene[' not in cam
assert 'ctx.m9cm[' not in cam
assert '/ ctx.mwhite[' not in cam
assert 'matMul3(ctx.m9cm, matMul3(ctx.adapt50ToScene, PP_TO_XYZ))' in s
assert 'precomposed_pp_to_m9_hsm_wrap_exact1' in s
assert 'hsv6ToRgbWrapped' in hsm
assert '% 6.0' not in hsm
assert 's = gap / v;' in hsm
assert 'int e10 = e00 + 3;' in hsm and 'int e11 = e01 + 3;' in hsm
assert 'double oneMinusHf = 1.0 - hf;' in hsm and 'double oneMinusSf = 1.0 - sf;' in hsm
print('PRIMARY2.2 colour hot-loop source guard PASS')
