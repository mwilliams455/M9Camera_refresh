#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1a-fix2.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
if not renderer_path.exists() or not gradle_path.exists():
    raise SystemExit('BASISHSM1A-FIX2: assembled renderer/build.gradle missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1A-FIX2 method marker missing: ' + marker)
    brace = src.find('{', start)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n': state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*': state = 'block_comment'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1A-FIX2 unterminated method: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

old = '''        final int expectedHistoricalHsmLength = Math.multiplyExact(
                Math.multiplyExact(Math.max(0, ctx.hueDivisions), Math.max(0, ctx.satDivisions)), 3);
        final boolean checkpointHistoricalHsmAvailable = ctx.hsm != null
                && ctx.hueDivisions >= 2
                && ctx.satDivisions >= 2
                && ctx.hsm.length >= expectedHistoricalHsmLength;
'''
new = '''        final int expectedHistoricalHsmLength = Math.multiplyExact(
                Math.multiplyExact(Math.max(0, ctx.hueDivisions), Math.max(0, ctx.satDivisions)), 3);
        // SOURCE_ONLY intentionally uses the compact 2x2 identity sentinel (12 doubles).
        // applyHsm() itself addresses the historical 90x30 table geometry, so a 12-value
        // sentinel must never be classified as a usable historical table merely because
        // its local sentinel dimensions also multiply to 12.
        final boolean checkpointIdentityHsmSentinel = ctx.hsm != null && ctx.hsm.length == 12;
        final boolean checkpointHistoricalHsmAvailable = ctx.hsm != null
                && !checkpointIdentityHsmSentinel
                && ctx.hueDivisions >= 2
                && ctx.satDivisions >= 2
                && ctx.hsm.length >= expectedHistoricalHsmLength;
'''
if renderer.count(old) != 1:
    raise SystemExit('BASISHSM1A-FIX2 FIX1 classifier anchor count=' + str(renderer.count(old)))
renderer = renderer.replace(old, new, 1)

old_log = '''        o.put("checkpointHistoricalHsmAvailable", checkpointHistoricalHsmAvailable);
        o.put("checkpointExpectedHistoricalHsmLength", expectedHistoricalHsmLength);
'''
new_log = '''        o.put("checkpointHistoricalHsmAvailable", checkpointHistoricalHsmAvailable);
        o.put("checkpointIdentityHsmSentinel", checkpointIdentityHsmSentinel);
        o.put("checkpointExpectedHistoricalHsmLength", expectedHistoricalHsmLength);
'''
if renderer.count(old_log) != 1:
    raise SystemExit('BASISHSM1A-FIX2 checkpoint log anchor count=' + str(renderer.count(old_log)))
renderer = renderer.replace(old_log, new_log, 1)

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_after.encode('utf-8')).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1A-FIX2 changed frozen primary renderCore')

renderer_path.write_text(renderer)

base_suffix = '-basishsm1a-fix1'
fix_suffix = '-basishsm1a-fix2'
if fix_suffix not in gradle:
    if base_suffix not in gradle:
        raise SystemExit('BASISHSM1A-FIX2 build identity anchor missing')
    gradle = gradle.replace(base_suffix, fix_suffix, 1)
    gradle_path.write_text(gradle)

print('M9 BASISHSM1A-FIX2 applied')
print(' - SOURCE_ONLY 12-value identity HSM sentinel is never passed to historical applyHsm indexing')
print(' - BASIS_HSM historical HSM path is unchanged')
print(' - frozen primary renderCore sha256 preserved:', primary_sha)
