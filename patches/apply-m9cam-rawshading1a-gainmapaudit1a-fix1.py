#!/usr/bin/env python3
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'apply-m9cam-rawshading1a-gainmapaudit1a.py'
if not source.exists():
    raise SystemExit('RAWSHADING1A FIX1 missing original apply harness')
text = source.read_text()

# EDGEPLACEMENTBESTFIT2A already changed the baseline renderCore signature from
# (... cameraRotation) to (... cameraRotation, 0.0). Change only the Phase-A
# development guard in the harness; the generated Photon source is otherwise identical.
old_guard_tail = "params.whiteLevel, params.whitePoint, cameraRotation)' not in renderer_after:"
new_guard_tail = "params.whiteLevel, params.whitePoint, cameraRotation, 0.0)' not in renderer_after:"
if text.count(old_guard_tail) != 1:
    raise SystemExit('RAWSHADING1A FIX1 expected one legacy renderCore guard, found %d' % text.count(old_guard_tail))
text = text.replace(old_guard_tail, new_guard_tail, 1)
text = text.replace(
    "raise SystemExit('RAWSHADING1A renderCore call changed; Phase A must not pass GainMap into rendering')",
    "raise SystemExit('RAWSHADING1A current BESTFIT2A baseline renderCore call changed')",
    1)

print_anchor = "print('M9RAWSHADING1A GAINMAPAUDIT1A applied')"
extra_guard = """if 'params.gainMap' in renderer_after or 'params.mapSize' in renderer_after or 'params.hasGainMap' in renderer_after:
    raise SystemExit('RAWSHADING1A Phase A unexpectedly wires GainMap into M9R35Renderer')

"""
if print_anchor not in text:
    raise SystemExit('RAWSHADING1A FIX1 print anchor missing')
text = text.replace(print_anchor, extra_guard + print_anchor, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
