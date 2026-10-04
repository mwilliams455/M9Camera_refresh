#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
r = (ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
c = (ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()
n = (ROOT/'app/src/main/cpp/m9color_jni.cpp').read_text()
g = (ROOT/'app/build.gradle').read_text()

def method_bounds(text, marker):
    start = text.find(marker)
    if start < 0: raise SystemExit('missing method marker: ' + marker)
    brace = text.find('{', start)
    depth = 0; i = brace; state = 'code'; quote = ''; esc = False
    while i < len(text):
        ch = text[i]; nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('unterminated method: ' + marker)

a0,a1 = method_bounds(r, '    private static RenderCore renderNativeProspectiveCore(')
active = r[a0:a1]
l0,l1 = method_bounds(r, '    private static RenderCore renderCore(')
legacy = r[l0:l1]
ea = 'Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);'
checks = {
    'active renderer MHC call': 'M9NativeColorCore.demosaicMhcRggb(' in active,
    'active renderer direct Mat': 'CvType.CV_16UC3, mhcRgbBuffer' in active,
    'active renderer EA removed': ea not in active,
    'legacy EA control retained': ea in legacy,
    'exactly one global EA control remains': r.count(ea) == 1,
    'diagnostic identity active only': 'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct' in active and 'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct' not in legacy,
    'direct buffer reachability fenced': 'java.lang.ref.Reference.reachabilityFence(mhcRgbBuffer);' in active,
    'native demosaic timing telemetry': 'demosaicNativeElapsedMs' in active and 'demosaicWorkersUsed' in active,
    'lifetime telemetry': 'direct_ByteBuffer_reachabilityFence_through_Mat_release' in active,
    'JNI declaration': 'static native long demosaicMhcRggb(' in c,
    'native kernel': 'mhcPixelRggb(' in n,
    'native JNI': 'M9NativeColorCore_demosaicMhcRggb' in n,
    'RGGB red site': 'if (evenY && evenX)' in n,
    'version suffix': 'demosaicmhc1a' in g.lower(),
    'SAT3 frozen constants': '16754, -7632, -922' in n and '18160, -9034, -922' in n,
    'curve02 still native': 'ctx.curve' in n,
    'production native source core retained': 'renderNativeProspectiveCore(' in r,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('OK  ' if v else 'FAIL') + k)
if failed: raise SystemExit('DEMOSAICMHC1A verifier failed: ' + ', '.join(failed))
print('DEMOSAICMHC1A verifier passed: MHC active only; dormant legacy EA retained; direct-buffer lifetime fenced')
