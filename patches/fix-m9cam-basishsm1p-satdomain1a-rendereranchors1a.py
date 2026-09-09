#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

repo_root = Path(__file__).resolve().parent.parent
base = repo_root / 'patches/apply-m9cam-basishsm1p-satdomain1a.py'
if not base.exists():
    raise SystemExit('SATDOMAIN1A base patch missing')

src = base.read_text()
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
print('SATDOMAIN1A renderer-anchor fix: using indentation-tolerant Java anchors')
raise SystemExit(subprocess.call(args))
