#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
rp = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
np = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
cp = root / 'app/src/main/cpp/m9color_jni.cpp'
bp = root / 'app/build.gradle'
for p in (rp, np, cp, bp):
    if not p.exists():
        raise SystemExit('SKYDOWN1A-FIX1 verify missing ' + str(p))

r = rp.read_text()
n = np.read_text()
c = cp.read_text()
b = bp.read_text()

def need(text, token, label):
    if token not in text:
        raise SystemExit('SKYDOWN1A-FIX1 verify failed: ' + label)

def forbid(text, token, label):
    if token in text:
        raise SystemExit('SKYDOWN1A-FIX1 verify failed: ' + label)

# Java bank contract: encoded 40..44 must decode to native modes 0,5,6,7,8.
need(r, 'int[] bridgeProbeModes = {40, 41, 42, 43, 44};', 'encoded SKYDOWN bank')
need(r, 'skyDownDiagnosticEncoded1A = bridgeProbeMode >= 40 && bridgeProbeMode <= 44', 'encoded range')
need(r, 'bridgeProbeMode == 40 ? 0 : bridgeProbeMode - 36', 'decode formula')
decoded = {40: 0, 41: 5, 42: 6, 43: 7, 44: 8}

# JNI signature must carry the diagnostic mode all the way into native context creation.
need(n, 'int skyChromaMode1A);', 'Java native createContext mode parameter')
need(r, 'ctx.hueDivisions, ctx.satDivisions,\n                    skyChromaMode1A);', 'renderer passes decoded diagnostic mode')
need(r, 'PP_TO_XYZ, XYZ2SRGB, cal.curve02, ctx.hueDivisions, ctx.satDivisions,\n                    0);', 'production primary context stays explicit mode 0')

m = re.search(r'skyChromaMode1A\s*<\s*0\s*\|\|\s*skyChromaMode1A\s*>\s*(\d+)', c)
if not m:
    raise SystemExit('SKYDOWN1A-FIX1 verify failed: native mode-range guard not found')
native_max = int(m.group(1))
required_max = max(decoded.values())
if native_max < required_max:
    raise SystemExit(
        f'SKYDOWN1A-FIX1 verify failed: native max mode {native_max} rejects required mode {required_max}'
    )
if native_max != 8:
    raise SystemExit(f'SKYDOWN1A-FIX1 verify failed: expected exact native max 8, got {native_max}')
forbid(c, 'skyChromaMode1A > 4', 'stale SKYCHROMA-only native guard remains')
need(c, 'SKYDOWN1A-FIX1: modes 5..8 are diagnostic-only downstream probes; production remains mode 0.',
     'repair provenance comment')

# Every decoded non-control mode must have a real native branch, not merely pass validation.
for mode in (5, 6, 7, 8):
    need(c, f'ctx.skyChromaMode1A == {mode}', f'native implementation for mode {mode}')

# Validate the encoded->decoded values against the native accepted range.
for encoded, mode in decoded.items():
    if not (0 <= mode <= native_max):
        raise SystemExit(
            f'SKYDOWN1A-FIX1 verify failed: encoded mode {encoded} decodes to rejected native mode {mode}'
        )

# Preserve the experiment's photographic freeze and no-HDR boundary markers.
need(r, 'public static final int JPEG_QUALITY = 95', 'JPEG Q95 freeze')
need(r, 'public static final int SATURATION_BANK = 3', 'SAT3 freeze')
need(r, 'private static final double HSM_H = 0.25', 'HSM H freeze')
need(r, 'private static final double HSM_S = 0.85', 'HSM S freeze')
need(r, 'private static final double HSM_V = 1.00', 'HSM V freeze')
need(b, '-basishsm1p-skydown1a-fix1-nativewpclip1a', 'FIX1 build provenance')
forbid(r, 'Ultra HDR', 'Ultra HDR must remain absent')

print('SKYDOWN1A-FIX1 mode-contract verification OK')
print(' - Java encoded modes 40/41/42/43/44 -> native 0/5/6/7/8')
print(' - native createContext accepted range is exactly 0..8')
print(' - native implementations for diagnostic modes 5..8 are present')
print(' - production context remains explicit mode 0; Q95/SAT3/HSM frozen')
