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
# a dormant legacy/Cobalt-source core and the promoted native-source core.
# SATDOMAIN1A must instrument only the active native-source core. Keep every
# non-renderer anchor strict and unique.
old_replace = '''def replace1(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'SATDOMAIN1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)
'''
new_replace = '''def replace1(text, old, new, label):
    n = text.count(old)
    if n == 1:
        return text.replace(old, new, 1)
    if label in ('java audit call', 'java diagnostic json') and n > 1:
        # Select the occurrence nearest the active native-source context marker.
        # nativeContextForFrame belongs to the promoted native-source path and is
        # deliberately absent from the dormant legacy/Cobalt-source render core.
        marker = 'nativeContextForFrame'
        marker_positions = []
        start = 0
        while True:
            p = text.find(marker, start)
            if p < 0:
                break
            marker_positions.append(p)
            start = p + 1
        if not marker_positions:
            raise SystemExit(f'SATDOMAIN1A {label}: active native renderer marker missing')

        positions = []
        start = 0
        while True:
            p = text.find(old, start)
            if p < 0:
                break
            positions.append(p)
            start = p + 1

        scored = sorted((min(abs(p - m) for m in marker_positions), p) for p in positions)
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            raise SystemExit(f'SATDOMAIN1A {label}: active renderer selection ambiguous: {scored[:2]}')
        distance, p = scored[0]
        if distance > 120000:
            raise SystemExit(f'SATDOMAIN1A {label}: nearest renderer anchor is implausibly far from active native marker: {distance}')
        print(f'SATDOMAIN1A {label}: selected active native renderer occurrence at {p}, distance={distance}, globalCount={n}')
        return text[:p] + new + text[p + len(old):]
    raise SystemExit(f'SATDOMAIN1A {label}: expected 1 anchor, found {n}')
'''
if src.count(old_replace) != 1:
    raise SystemExit(f'SATDOMAIN1A active-core fix: replace1 helper anchor count={src.count(old_replace)}')
src = src.replace(old_replace, new_replace, 1)

# Make the two renderer source literals indentation-tolerant. Active-core
# selection above prevents the resulting duplicate literals from touching the
# dormant core.
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
print('SATDOMAIN1A renderer-anchor fix: targeting promoted native-source renderer core')
raise SystemExit(subprocess.call(args))
