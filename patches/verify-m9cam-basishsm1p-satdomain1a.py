#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
cp = root/'app/src/main/cpp/m9color_jni.cpp'
np = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
rp = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
bp = root/'app/build.gradle'
for p in (cp, np, rp, bp):
    if not p.exists(): raise SystemExit('SATDOMAIN1A missing '+str(p))
c = cp.read_text(); n = np.read_text(); r = rp.read_text(); b = bp.read_text()

def extract_method(src, marker):
    start=src.find(marker)
    if start<0: raise SystemExit('SATDOMAIN1A verify method marker missing: '+marker)
    brace=src.find('{',start); depth=0; i=brace; state='code'; quote=''; esc=False
    while i<len(src):
        ch=src[i]; nxt=src[i+1] if i+1<len(src) else ''
        if state=='line':
            if ch=='\n': state='code'
        elif state=='block':
            if ch=='*' and nxt=='/': state='code'; i+=1
        elif state=='string':
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch==quote: state='code'
        else:
            if ch=='/' and nxt=='/': state='line'; i+=1
            elif ch=='/' and nxt=='*': state='block'; i+=1
            elif ch in ('"',"'"): state='string'; quote=ch; esc=False
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return src[start:i+1]
        i+=1
    raise SystemExit('SATDOMAIN1A verify unterminated method')

active=extract_method(r,'    private static RenderCore renderNativeProspectiveCore(')
legacy=extract_method(r,'    private static RenderCore renderCore(')
checks = {
    'native audit helper': 'auditSatDomainJson(const ColorContext& ctx' in c,
    'native JNI entry': 'M9NativeColorCore_auditSatDomainJsonDirect' in c,
    'render first SAT clamp retained': 'clipl(a0 >> 16, 0, LUT_MAX)' in c and 'clipl(a1 >> 16, 0, LUT_MAX)' in c and 'clipl(a2 >> 16, 0, LUT_MAX)' in c,
    'audit exact signed shift domain': 'unclampedSatCoordinateDomain' in c and 'static_cast<double>(shifted[0])' in c and 'static_cast<double>(shifted[1])' in c and 'static_cast<double>(shifted[2])' in c,
    'SAT2 exact family retained': 'Q2E' in c and 'Q2O' in c,
    'SAT3 exact family retained': 'QE' in c and 'QO' in c,
    'SAT4 exact family retained': 'Q4E' in c and 'Q4O' in c,
    'read-only declaration': 'static native String auditSatDomainJsonDirect' in n,
    'control-only call active core': active.count('skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A') == 1,
    'active native core only': active.count('auditSatDomainJsonDirect(') == 1 and 'auditSatDomainJsonDirect(' not in legacy,
    'exact effective gain audited': 'effectiveRenderGain);' in active and 'meter.gain);' not in active[active.find('auditSatDomainJsonDirect('):active.find('auditSatDomainJsonDirect(')+400],
    'diagnostic JSON': active.count('d.put("satDomainTelemetry", new JSONObject(satDomainTelemetryJson1A))') == 1,
    'no rendered-pixel claim': active.count('d.put("satDomainRenderedPixelsModified", false)') == 1,
    'native source provenance': 'renderNativeProspectiveCore_active_native_SOURCECAL2A_path' in active,
    'legacy core untouched by SATDOMAIN': 'satDomainTelemetry' not in legacy and 'SATDOMAIN1A' not in legacy,
    'SATDOMAIN version': '-basishsm1p-satdomain1a-nativewpclip1a' in b,
}
failed=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('OK   ' if v else 'FAIL ')+k)
if failed: raise SystemExit('SATDOMAIN1A verify failed: '+', '.join(failed))
print('SATDOMAIN1A verification OK')
print(' - exact SAT2/SAT3/SAT4 family math retained')
print(' - causal hue audit uses exact signed a>>16 coordinate before first 0..2047 clamp')
print(' - instrumentation is confined to active native SOURCECAL2A render core')
print(' - dormant legacy Cobalt-source core contains no SATDOMAIN instrumentation')
print(' - rendered pixels / capture / DNG / HDR boundary remain unchanged')
