#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not R.exists():
    raise SystemExit('DEMOSAICMHC1A LIFETIME1A renderer missing')
text = R.read_text()
marker = '    private static RenderCore renderNativeProspectiveCore('

def method_bounds(s, marker):
    start = s.find(marker)
    if start < 0: raise SystemExit('LIFETIME1A active method marker missing')
    brace = s.find('{', start)
    depth = 0; i = brace; state = 'code'; quote = ''; esc = False
    while i < len(s):
        ch = s[i]; nxt = s[i+1] if i+1 < len(s) else ''
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
    raise SystemExit('LIFETIME1A active method unterminated')

start, end = method_bounds(text, marker)
active = text[start:end]
if 'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct' not in active:
    raise SystemExit('LIFETIME1A requires DEMOSAICMHC1A active core first')

old_finally = '''            if (nativeColorContext != 0L) M9NativeColorCore.destroyContext(nativeColorContext);\n            if (!rawMat.empty()) rawMat.release();\n            if (!cam16.empty()) cam16.release();\n            if (!meterCam16.empty()) meterCam16.release();\n'''
new_finally = old_finally + '''            // LIFETIME1A: Mat(ByteBuffer) wraps external direct memory and does not own\n            // the Java ByteBuffer. Keep it strongly reachable through every Mat release.\n            java.lang.ref.Reference.reachabilityFence(mhcRgbBuffer);\n'''
if 'reachabilityFence(mhcRgbBuffer)' not in active:
    if active.count(old_finally) != 1:
        raise SystemExit(f'LIFETIME1A active finally anchor count={active.count(old_finally)}')
    active = active.replace(old_finally, new_finally, 1)

mode_anchor = '            d.put("demosaicMode", "DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct");\n'
perf = '''            d.put("demosaicNativeElapsedMs", mhcStats[0] / 1_000_000.0);\n            d.put("demosaicWorkersUsed", mhcStats[1]);\n            d.put("demosaicBackingLifetime", "direct_ByteBuffer_reachabilityFence_through_Mat_release");\n'''
if 'demosaicBackingLifetime' not in active:
    if active.count(mode_anchor) != 1:
        raise SystemExit(f'LIFETIME1A diagnostic anchor count={active.count(mode_anchor)}')
    active = active.replace(mode_anchor, mode_anchor + perf, 1)

text = text[:start] + active + text[end:]
R.write_text(text)
print('DEMOSAICMHC1A LIFETIME1A applied')
print(' - direct RGB16 ByteBuffer reachability fenced through Mat release')
print(' - native MHC elapsed time and worker count added to diagnostics')
print(' - no photographic arithmetic changed')
