#!/usr/bin/env python3
from pathlib import Path
import hashlib
import runpy
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourcegeometryproof2a-fix1.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
base = Path(__file__).with_name('apply-m9cam-sourcegeometryproof2a.py')
if not renderer.exists() or not base.exists():
    raise SystemExit('SOURCEGEOMETRYPROOF2A FIX1 missing assembled renderer/base patch')


def method_bytes(src: str, signature: str) -> bytes:
    start = src.find(signature)
    if start < 0:
        raise SystemExit('SOURCEGEOMETRYPROOF2A FIX1 method missing: ' + signature)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('SOURCEGEOMETRYPROOF2A FIX1 opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[start:i + 1].encode('utf-8')
        i += 1
    raise SystemExit('SOURCEGEOMETRYPROOF2A FIX1 unterminated method: ' + signature)

frozen = [
    '    private static RenderCore renderNativeSourceProduction1P(',
    '    private static RenderCore renderNativeProspectiveCore(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1ABayer(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapBayer(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
]
before_src = renderer.read_text()
before = {sig: hashlib.sha256(method_bytes(before_src, sig)).hexdigest() for sig in frozen}

runpy.run_path(str(base), run_name='__main__')

after_src = renderer.read_text()
for sig in frozen:
    after = hashlib.sha256(method_bytes(after_src, sig)).hexdigest()
    if after != before[sig]:
        raise SystemExit('SOURCEGEOMETRYPROOF2A FIX1 changed frozen photographic method: '
                         + sig + '\nBEFORE=' + before[sig] + '\nAFTER=' + after)

print('SOURCEGEOMETRYPROOF2A FIX1 PASS')
for sig in frozen:
    print(before[sig], sig.strip())
print(' - production wrapper unchanged')
print(' - native source/shading core unchanged')
print(' - all LensShadingMap interpolation/application helpers unchanged')
