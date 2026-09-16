#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-hsmab1a-sameraw-bank.py <PhotonCamera-root>')

# Preserve and replay the original HSMAB1A assembly exactly, then correct only
# the identity-HSM geometry discovered by device validation.  The frozen native
# HSM hot path is 90x30 even for a no-op table; a compact 2x2 sentinel is valid
# for source-only Java bookkeeping but is not a valid table for the native path.
legacy = Path(__file__).with_name('apply-m9cam-hsmab1a-sameraw-bank-v1.py')
if not legacy.exists():
    raise SystemExit(f'HSMAB1A FIX1 missing preserved v1 patch: {legacy}')
runpy.run_path(str(legacy), run_name='__main__')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'HSMAB1A FIX1 missing renderer: {p}')
s = p.read_text()

start_token = '            } else if (bridgeProbeMode == 60) {'
end_token = '            } else if (bridgeProbeMode != 0) {'
a = s.find(start_token)
if a < 0:
    raise SystemExit('HSMAB1A FIX1 mode60 start missing')
b = s.find(end_token, a)
if b < 0:
    raise SystemExit('HSMAB1A FIX1 mode60 end missing')
segment = s[a:b]

old = '''                ctx.hsm = new double[]{
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0
                };
                ctx.hueDivisions = 2;
                ctx.satDivisions = 2;
'''
new = '''                // HSMAB1A-FIX1: the frozen Java/native HSM evaluator uses the
                // historical 90x30 geometry.  Keep that exact geometry but populate
                // every cell with an identity operation: 0 deg hue, 1x saturation,
                // 1x value.  This changes HSM content only, never table topology.
                int identityHsmCells = Math.multiplyExact(cal.hueDivisions, cal.satDivisions);
                int identityHsmLength = Math.multiplyExact(identityHsmCells, 3);
                if (cal.hueDivisions != 90 || cal.satDivisions != 30
                        || cal.hsmA.length != identityHsmLength
                        || cal.hsmD65.length != identityHsmLength) {
                    throw new IllegalStateException(
                            "HSMAB1A-FIX1 unexpected historical HSM geometry");
                }
                ctx.hsm = new double[identityHsmLength];
                for (int i = 0; i < ctx.hsm.length; i += 3) {
                    ctx.hsm[i] = 0.0;
                    ctx.hsm[i + 1] = 1.0;
                    ctx.hsm[i + 2] = 1.0;
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
'''
if segment.count(old) != 1:
    raise SystemExit(f'HSMAB1A FIX1 compact identity anchor count={segment.count(old)}')
segment = segment.replace(old, new, 1)
s = s[:a] + segment + s[b:]
p.write_text(s)
print('HSMAB1A_SAMERAW_BANK FIX1 90x30 identity geometry applied')
