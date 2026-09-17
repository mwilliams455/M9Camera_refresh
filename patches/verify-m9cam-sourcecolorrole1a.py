#!/usr/bin/env python3
from pathlib import Path
import sys, re

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcecolorrole1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s=p.read_text()
checks={
 'A matrix':'SOURCECOLORROLE1A_A',
 'D65 matrix':'SOURCECOLORROLE1A_D65',
 'candidate mode':'sourcecolorrole1a_common_scene_dual3x3',
 'candidate flag':'d.put("sourceColorRole1A", true)',
 'runtime Cobalt off':'d.put("sourceColorRole1ACobaltTableRuntimeDependency", false)',
 'target input off':'d.put("sourceColorRole1ATargetInput15RuntimeApplied", false)',
 'SAT2 retained':'d.put("m9SaturationMatrixPair", "M04_M05")',
 'curve02 retained':'d.put("m9FirmwareCurve02Retained", true)',
 'tonebound marker':'toneBound1A',
}
for label,needle in checks.items():
    if needle not in s:
        raise SystemExit(f'SOURCECOLORROLE1A verify missing {label}: {needle}')

def arr(name):
    m=re.search(r'private static final double\[\] '+re.escape(name)+r' = \{([^}]*)\};',s,re.S)
    if not m: raise SystemExit('missing array '+name)
    vals=[float(x.strip()) for x in m.group(1).replace('\n',' ').split(',') if x.strip()]
    if len(vals)!=9: raise SystemExit(f'{name} len={len(vals)}')
    return vals
for name in ['SOURCECOLORROLE1A_A','SOURCECOLORROLE1A_D65']:
    v=arr(name)
    for r in range(3):
        sm=sum(v[r*3:r*3+3])
        if abs(sm-1.0)>1e-12:
            raise SystemExit(f'{name} row {r} neutral-axis sum={sm}')
a=s.index('            } else if (bridgeProbeMode == 4) {')
b=s.index('            } else if (bridgeProbeMode != 0) {',a)
seg=s[a:b]
if 'buildTargetInputAdapter1A(' in seg:
    raise SystemExit('SOURCECOLORROLE1A mode4 still invokes TARGETINPUTADAPTER1A')
if 'cal.hsmA[i]' in seg or 'cal.hsmD65[i]' in seg:
    raise SystemExit('SOURCECOLORROLE1A mode4 still evaluates historical HSM table')
if 'SOURCECOLORROLE1A_A, SOURCECOLORROLE1A_D65, ctx.wA' not in seg:
    raise SystemExit('SOURCECOLORROLE1A dual-illuminant interpolation missing')
print('SOURCECOLORROLE1A VERIFY PASS')
print('neutral axis preserved exactly by both fitted matrices')
print('production mode4 contains no TARGETINPUTADAPTER1A invocation')
print('production mode4 contains no historical HSM table interpolation')
print('SAT2 M04/M05, curve02 and TONEBOUND markers retained')
