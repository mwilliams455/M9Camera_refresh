#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-basishsm1p-satdomain1a-scopedrenderer1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
repo_root = Path(__file__).resolve().parent.parent
base = repo_root / 'patches/apply-m9cam-basishsm1p-satdomain1a.py'
rp = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cp = root/'app/src/main/cpp/m9color_jni.cpp'
np = root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
bp = root/'app/build.gradle'

# The original SATDOMAIN patch intentionally applies native/JNI additions before touching
# the renderer. On the modern 1P assembled source the two renderer anchors exist in both
# dormant legacy renderCore and active renderNativeProspectiveCore, so let the base patch
# install its native pieces, then repair the ambiguous renderer insertion explicitly.
p = subprocess.run([sys.executable, str(base), str(root)], text=True, capture_output=True)
print(p.stdout, end='')
if p.returncode == 0:
    raise SystemExit('SATDOMAIN1A scoped fix expected the unscoped base patch to stop on duplicate renderer anchors')
print(p.stderr, end='')
expected = ('java audit call' in (p.stdout + p.stderr)) or ('expected 1 anchor, found 2' in (p.stdout + p.stderr))
if not expected:
    raise SystemExit('SATDOMAIN1A base patch failed for an unexpected reason')

c = cp.read_text(); n = np.read_text()
for marker in ('auditSatDomainJson(const ColorContext& ctx', 'M9NativeColorCore_auditSatDomainJsonDirect'):
    if marker not in c:
        raise SystemExit('SATDOMAIN1A native partial apply missing marker: '+marker)
if 'static native String auditSatDomainJsonDirect' not in n:
    raise SystemExit('SATDOMAIN1A Java JNI declaration missing after partial apply')

r = rp.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0: raise SystemExit('SATDOMAIN1A method marker missing: '+marker)
    brace = src.find('{', start)
    if brace < 0: raise SystemExit('SATDOMAIN1A method opening brace missing')
    depth=0; i=brace; state='code'; quote=''; esc=False
    while i < len(src):
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
            elif ch in ('"', "'"): state='string'; quote=ch; esc=False
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return start, i+1, src[start:i+1]
        i+=1
    raise SystemExit('SATDOMAIN1A unterminated method')

def replace1(text, old, new, label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'SATDOMAIN1A scoped {label}: expected 1 in active native method, found {n}')
    return text.replace(old,new,1)

marker='    private static RenderCore renderNativeProspectiveCore('
ms, me, method = extract_method(r, marker)
if 'SATDOMAIN1A' in method:
    raise SystemExit('SATDOMAIN1A renderer instrumentation already present')

old='''            long fullRenderStartedNs = System.nanoTime();'''
new='''            // SATDOMAIN1A: read-only exact-family audit on the ACTIVE native-source core only.
            // Uses the same full-resolution demosaiced camera Mat and exact effective render gain
            // that enter native SAT rendering. It never writes cam16, output pixels, TC20 state,
            // edge-placement state, DNG data, or any capture parameter.
            String satDomainTelemetryJson1A = null;
            long satDomainAuditElapsedMs1A = -1L;
            final boolean satDomainAuditInputEligible1A = cam16.isContinuous()
                    && cam16.channels() == 3
                    && cam16.elemSize1() == 2L
                    && cam16.step1() == (long)width * 3L
                    && cam16.dataAddr() != 0L;
            if (skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A) {
                long satDomainStartedNs1A = System.nanoTime();
                satDomainTelemetryJson1A = M9NativeColorCore.auditSatDomainJsonDirect(
                        nativeContextForFrame, cam16.dataAddr(), pixels, width, height, effectiveRenderGain);
                satDomainAuditElapsedMs1A = (System.nanoTime() - satDomainStartedNs1A) / 1_000_000L;
            }

            long fullRenderStartedNs = System.nanoTime();'''
method=replace1(method,old,new,'render-start')

old='''            d.put("satBank", SATURATION_BANK);'''
new='''            d.put("satBank", SATURATION_BANK);
            d.put("satDomain1A", skySatDiagnosticEncoded1A);
            d.put("satDomainAuditReadOnly", true);
            d.put("satDomainAuditControlOnly", true);
            d.put("satDomainAuditInputEligible", satDomainAuditInputEligible1A);
            d.put("satDomainAuditElapsedMs", satDomainAuditElapsedMs1A);
            d.put("satDomainRenderedPixelsModified", false);
            d.put("satDomainAuditedGain", effectiveRenderGain);
            d.put("satDomainAuditedCore", "renderNativeProspectiveCore_active_native_SOURCECAL2A_path");
            if (satDomainTelemetryJson1A != null && !satDomainTelemetryJson1A.isEmpty()) {
                d.put("satDomainTelemetry", new JSONObject(satDomainTelemetryJson1A));
            }'''
method=replace1(method,old,new,'diagnostic-json')
r = r[:ms] + method + r[me:]

# Change only the SKYSAT diagnostic schema marker if it is unique. This is provenance,
# not photographic arithmetic.
if r.count('"m9cam.renderer.skysat.v1a"') == 1:
    r = r.replace('"m9cam.renderer.skysat.v1a"','"m9cam.renderer.satdomain.v1a"',1)
rp.write_text(r)

b=bp.read_text()
oldv='-basishsm1p-skysat1a-nativewpclip1a'
if b.count(oldv)!=1:
    raise SystemExit('SATDOMAIN1A version anchor count='+str(b.count(oldv)))
b=b.replace(oldv,'-basishsm1p-satdomain1a-nativewpclip1a',1)
bp.write_text(b)

# Guard against accidental instrumentation of the dormant legacy Cobalt-source core.
_, _, active = extract_method(rp.read_text(), marker)
_, _, legacy = extract_method(rp.read_text(), '    private static RenderCore renderCore(')
if active.count('auditSatDomainJsonDirect(') != 1:
    raise SystemExit('SATDOMAIN1A active native core audit call count invalid')
if 'auditSatDomainJsonDirect(' in legacy or 'satDomainTelemetry' in legacy:
    raise SystemExit('SATDOMAIN1A leaked into dormant legacy renderCore')
if 'effectiveRenderGain);' not in active:
    raise SystemExit('SATDOMAIN1A must audit exact effective render gain')
print('SATDOMAIN1A SCOPEDRENDERER1A applied')
print(' - native/JNI audit additions retained from base SATDOMAIN patch')
print(' - renderer audit inserted only in active renderNativeProspectiveCore')
print(' - dormant legacy Cobalt-source renderCore remains SATDOMAIN-free')
print(' - audit uses exact effectiveRenderGain, matching rendered pre-SAT vectors')
