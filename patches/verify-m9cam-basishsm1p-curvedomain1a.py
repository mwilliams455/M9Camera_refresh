#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE = ROOT / 'app/build.gradle'

t = CPP.read_text(); j = JAVA.read_text(); g = GRADLE.read_text()
checks = {
    'schema': r'\"schema\":\"m9cam.curvedomain1a.v1\"' in t,
    'parent SATDOMAIN': r'\"parentDiagnostic\":\"SATDOMAIN1A\"' in t,
    'curve exact lookup': 'curve[static_cast<size_t>(clamped[0])]' in t and 'curve[static_cast<size_t>(clamped[2])]' in t,
    'curve hue delta': 'meanAbsHueClampedToCurveDeg' in t,
    'curve magenta creation': 'magentaCreatedByCurveCount' in t and 'magentaRemovedByCurveCount' in t,
    '30deg sectors': 'hueSector30deg' in t and 'meanCurveHueShiftDeg' in t,
    'read only JSON': r'\"readOnly\":true,\"renderedPixelsModified\":false' in t,
    'SATDOMAIN JNI retained': 'auditSatDomainJsonDirect' in t,
    'control-only Java retained': 'satDomainAuditControlOnly' in j and 'satDomainRenderedPixelsModified' in j,
    'production SAT3 kernel retained': 'const int rr = ctx.curve[i0];\n    const int gg = ctx.curve[i1];\n    const int bb = ctx.curve[i2];' in t,
    'exact BT601 retained': 'const int64_t yy0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;' in t,
    'version': '-curvedomain1a-nativewpclip1a' in g,
}
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if not all(checks.values()):
    raise SystemExit('CURVEDOMAIN1A verification failed')

# Scope guard: new telemetry must live only inside the existing SATDOMAIN audit region.
start = t.find('// SATDOMAIN1A: read-only saturation-domain audit.')
end = t.find('void throwIllegalArgument', start)
if start < 0 or end < 0:
    raise SystemExit('CURVEDOMAIN1A SATDOMAIN audit scope missing')
outside = t[:start] + t[end:]
for token in ['magentaCreatedByCurve', 'hueSector30deg', 'sumHueClampedToCurve']:
    if token in outside:
        raise SystemExit(f'CURVEDOMAIN1A token escaped read-only audit scope: {token}')
print('OK   curve telemetry confined to read-only SATDOMAIN audit scope')
print('CURVEDOMAIN1A invariants verified')
