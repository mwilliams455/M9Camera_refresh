#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
JAVA=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE=ROOT/'app/build.gradle'
t=CPP.read_text(); j=JAVA.read_text() if JAVA.exists() else ''; g=GRADLE.read_text()
checks={
 'schema': r'\"schema\":\"m9cam.curvedomain1b.neutralaxis1a.v1\"' in t,
 'parent': r'\"parentDiagnostic\":\"CURVEDOMAIN1A\"' in t,
 'neutral bands': 'neutralBandCount[3]' in t and 'neutralThresholds[3] = {0.05, 0.10, 0.20}' in t,
 'green deficit': 'satGreenDeficitNormalized' in t and 'positive_is_magenta_direction_negative_is_green_direction' in t,
 'pre/sat/curve': 'meanGreenDeficitNormalizedPre' in t and 'meanGreenDeficitNormalizedPostSatClamp' in t and 'meanGreenDeficitNormalizedPostCurve' in t,
 'crossing': 'crossToMagentaAtSat1pctFraction' in t and 'crossToMagentaAtCurve1pctFraction' in t,
 'hue sectors retained': 'hueSector30deg' in t and 'meanCurveHueShiftDeg' in t,
 'curve exact lookup': 'curve[static_cast<size_t>(clamped[0])]' in t and 'curve[static_cast<size_t>(clamped[2])]' in t,
 'read only json': r'\"readOnly\":true,\"renderedPixelsModified\":false' in t,
 'production SAT3 kernel retained': 'const int rr = ctx.curve[i0];\n    const int gg = ctx.curve[i1];\n    const int bb = ctx.curve[i2];' in t,
 'exact BT601 retained': 'const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;' in t,
 'version': '-curvedomain1b-neutralaxis1a-nativewpclip1a' in g,
}
if j:
    checks['control-only Java retained']='satDomainAuditControlOnly' in j and 'satDomainRenderedPixelsModified' in j
for k,v in checks.items(): print(('OK   ' if v else 'FAIL ')+k)
if not all(checks.values()): raise SystemExit('CURVEDOMAIN1B-NEUTRALAXIS1A verification failed')
start=t.find('// SATDOMAIN1A: read-only saturation-domain audit.')
end=t.find('void throwIllegalArgument',start)
if start<0 or end<0: raise SystemExit('SATDOMAIN audit scope missing')
outside=t[:start]+t[end:]
for token in ['neutralAxisAudit','neutralBandCount','satGreenDeficitNormalized']:
    if token in outside: raise SystemExit(f'neutral diagnostic escaped read-only audit scope: {token}')
print('OK   neutral-axis telemetry confined to read-only SATDOMAIN/CURVEDOMAIN audit scope')
print('CURVEDOMAIN1B-NEUTRALAXIS1A invariants verified')
