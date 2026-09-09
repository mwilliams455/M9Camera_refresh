#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

repo_root = Path(__file__).resolve().parent.parent
base = repo_root / 'patches/apply-m9cam-basishsm1p-satdomain1a.py'
if not base.exists():
    raise SystemExit('SATDOMAIN1A base patch missing')

src = base.read_text()

# The assembled renderer intentionally contains two historical render cores:
#   renderCore(...)                  = dormant legacy/Cobalt-source forensic core
#   renderNativeProspectiveCore(...) = promoted native SOURCECAL2A production core
# SATDOMAIN1A must instrument only the latter. Rewrite the base patch's generic
# replacement helper so the two duplicated Java anchors are selected strictly
# inside renderNativeProspectiveCore, never by global occurrence or proximity.
old_replace = '''def replace1(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'SATDOMAIN1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)
'''
new_replace = '''def _method_bounds(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('SATDOMAIN1A active native method marker missing: ' + marker)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('SATDOMAIN1A active native method opening brace missing')
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    esc = False
    while i < len(text):
        ch = text[i]
        nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; esc = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('SATDOMAIN1A active native method unterminated')

def replace1(text, old, new, label):
    n = text.count(old)
    if label in ('java audit call', 'java diagnostic json'):
        start, end = _method_bounds(text, '    private static RenderCore renderNativeProspectiveCore(')
        method = text[start:end]
        scoped = method.count(old)
        if scoped != 1:
            raise SystemExit(f'SATDOMAIN1A {label}: expected 1 active-native scoped anchor, found {scoped}; global={n}')
        rel = method.find(old)
        pos = start + rel
        print(f'SATDOMAIN1A {label}: selected renderNativeProspectiveCore occurrence at {pos}, globalCount={n}')
        return text[:pos] + new + text[pos + len(old):]
    if n != 1:
        raise SystemExit(f'SATDOMAIN1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)
'''
if src.count(old_replace) != 1:
    raise SystemExit(f'SATDOMAIN1A active-core fix: replace1 helper anchor count={src.count(old_replace)}')
src = src.replace(old_replace, new_replace, 1)

# Make only the source literals indentation-tolerant. Method scoping above is
# the authority for choosing the active occurrence.
old_render = "'''            long fullRenderStartedNs = System.nanoTime();'''"
new_render = "'''long fullRenderStartedNs = System.nanoTime();'''"
old_diag = "'''            d.put(\"satBank\", SATURATION_BANK);'''"
new_diag = "'''d.put(\"satBank\", SATURATION_BANK);'''"
for old, new, label in ((old_render, new_render, 'render-start'), (old_diag, new_diag, 'diagnostic-json')):
    if src.count(old) != 1:
        raise SystemExit(f'SATDOMAIN1A renderer-anchor fix {label}: expected exactly one source literal, found {src.count(old)}')
    src = src.replace(old, new, 1)

out = Path('/tmp/apply-m9cam-basishsm1p-satdomain1a-anchorfixed.py')
out.write_text(src)
args = [sys.executable, str(out)] + sys.argv[1:]
print('SATDOMAIN1A renderer-anchor fix: targeting renderNativeProspectiveCore explicitly')
rc = subprocess.call(args)
if rc != 0:
    raise SystemExit(rc)

# Post-apply telemetry correctness fixes. These are audit-only and do not touch
# the renderer hot-loop arithmetic.
if len(sys.argv) < 2:
    raise SystemExit('SATDOMAIN1A fix requires PhotonCamera root argument')
root = Path(sys.argv[1])
cpp_path = root / 'app/src/main/cpp/m9color_jni.cpp'
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cpp = cpp_path.read_text()
renderer = renderer_path.read_text()

# Causal SAT-domain telemetry must use the exact signed integer coordinate that
# immediately feeds the first 0..2047 clamp: arithmetic a >> 16. A fractional
# a/65536 proxy can differ at negative boundaries and is therefore forbidden.
old_coord = '''    const double unclamped[3] = {
        static_cast<double>(a0) / 65536.0,
        static_cast<double>(a1) / 65536.0,
        static_cast<double>(a2) / 65536.0
    };'''
new_coord = '''    const double unclamped[3] = {
        static_cast<double>(shifted[0]),
        static_cast<double>(shifted[1]),
        static_cast<double>(shifted[2])
    };'''
if cpp.count(old_coord) != 1:
    raise SystemExit(f'SATDOMAIN1A exact-shift telemetry anchor count={cpp.count(old_coord)}')
cpp = cpp.replace(old_coord, new_coord, 1)

old_domain = '    os << "\\\"matrixAccumulatorDomain\\\":\\\"signed_int64_Q_family_dot_product\\\",";'
new_domain = old_domain + '\n    os << "\\\"unclampedSatCoordinateDomain\\\":\\\"exact_signed_arithmetic_shift_16_before_clamp\\\",";'
if cpp.count(old_domain) != 1:
    raise SystemExit(f'SATDOMAIN1A coordinate-domain JSON anchor count={cpp.count(old_domain)}')
cpp = cpp.replace(old_domain, new_domain, 1)
cpp_path.write_text(cpp)

# The audit must evaluate the same final gain that the SAT3 control actually
# renders with, not the pre-edge-placement TC20 meter.gain alone.
def method_bounds(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('SATDOMAIN1A assembled active method missing')
    brace = text.find('{', start)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    esc = False
    while i < len(text):
        ch = text[i]
        nxt = text[i+1] if i+1 < len(text) else ''
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
            elif ch in ('"', "'"): state = 'string'; quote = ch; esc = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('SATDOMAIN1A assembled active method unterminated')

start, end = method_bounds(renderer, '    private static RenderCore renderNativeProspectiveCore(')
active = renderer[start:end]
call = 'auditSatDomainJsonDirect('
call_pos = active.find(call)
if call_pos < 0 or active.count(call) != 1:
    raise SystemExit(f'SATDOMAIN1A active audit call count={active.count(call)}')
window_end = min(len(active), call_pos + 600)
window = active[call_pos:window_end]
if 'meter.gain);' not in window:
    raise SystemExit('SATDOMAIN1A expected meter.gain audit argument not found in active call window')
if 'effectiveRenderGain' not in active:
    raise SystemExit('SATDOMAIN1A active core lacks effectiveRenderGain authority')
window = window.replace('meter.gain);', 'effectiveRenderGain);', 1)
active = active[:call_pos] + window + active[window_end:]
renderer = renderer[:start] + active + renderer[end:]
renderer = renderer.replace(
    '// demosaiced camera Mat and the exact already-computed TC20 gain, evaluates SAT2/3/4',
    '// demosaiced camera Mat and the exact final effective render gain, evaluates SAT2/3/4',
    1)
renderer_path.write_text(renderer)

print('SATDOMAIN1A audit integrity repair applied')
print(' - Java instrumentation scoped only to renderNativeProspectiveCore')
print(' - dormant legacy renderCore remains untouched')
print(' - audit coordinate is exact signed a>>16 before first 0..2047 clamp')
print(' - audit gain is exact control effectiveRenderGain')
print(' - rendered pixels and saturation/TC20/curve02 arithmetic unchanged')
