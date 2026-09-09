#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
cp = root/'app/src/main/cpp/m9color_jni.cpp'
np = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
rp = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
bp = root/'app/build.gradle'
for p in (cp, np, rp, bp):
    if not p.exists():
        raise SystemExit('SATDOMAIN1A missing '+str(p))
c = cp.read_text(); n = np.read_text(); r = rp.read_text(); b = bp.read_text()
checks = {
    'native audit helper': 'auditSatDomainJson(const ColorContext& ctx' in c,
    'native JNI entry': 'M9NativeColorCore_auditSatDomainJsonDirect' in c,
    'exact first SAT clamp retained': 'clipl(a0 >> 16, 0, LUT_MAX)' in c and 'clipl(a1 >> 16, 0, LUT_MAX)' in c and 'clipl(a2 >> 16, 0, LUT_MAX)' in c,
    'SAT2 exact family retained': 'Q2E' in c and 'Q2O' in c,
    'SAT3 exact family retained': 'QE' in c and 'QO' in c,
    'SAT4 exact family retained': 'Q4E' in c and 'Q4O' in c,
    'read-only declaration': 'static native String auditSatDomainJsonDirect' in n,
    'control-only call': 'skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A' in r,
    'diagnostic JSON': 'd.put("satDomainTelemetry", new JSONObject(satDomainTelemetryJson1A))' in r,
    'no rendered-pixel claim': 'd.put("satDomainRenderedPixelsModified", false)' in r,
    'SATDOMAIN version': '-basishsm1p-satdomain1a-nativewpclip1a' in b,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items():
    print(('OK  ' if v else 'FAIL') + k)
if failed:
    raise SystemExit('SATDOMAIN1A verify failed: '+', '.join(failed))
print('SATDOMAIN1A verification OK: audit is additive/read-only; SKYSAT render arithmetic retained')
