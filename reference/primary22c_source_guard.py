#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
assert 'm9cam.renderer.r38.h25tg1.full12.android.v8.primary2p2c' in s
assert 'precomposed_pp_to_m9_hsm_wrap_exact1_unit16lut1_m9fuse1_hsmconst1' in s
assert 'UNIT16[cam[c] & 0xffff]' in s and 'out[i] = i / 65535.0' in s
assert 'cameraToM9CurvePacked' in s and 'final double[] m90' not in s and 'final int[] rgb0' not in s
assert 'double hp = h * 15.0;' in s and 'double sp = s * 29.0;' in s
assert 'applyHsm(pr, pg, pb, ctx.hsm, hsmOut);' in s
# Keep PRIMARY2 horizontal pair semantics and scalar TG/BT reconstruction from validated 2.2.
assert 'for (int x = 0; x < w2; x += 2)' in s
assert 'long cbS = ((((-2765 * rs + 1) >> 1)' in s
assert 'double cbModern = cb < 0 ? cb * tgCbGain : cb;' in s
assert 'int rr0 = roundU8(yy0 + 1.402 * crModern);' in s
assert 'PARALLEL_RENDER_WORKERS' in s and 'RENDER_STRIP_ROWS = 24' in s
print('PRIMARY2.2C source guard PASS')
