#!/usr/bin/env python3
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'apply-m9cam-rawshading1a-gainmapaudit1a.py'
if not source.exists():
    raise SystemExit('RAWSHADING1A FIX1 missing original apply harness')
text = source.read_text()

old = '''renderer_after = read(renderer_rel)
if 'rawShadingGainMapApplied\\", false' not in renderer_after:
    raise SystemExit('RAWSHADING1A renderer diagnostic marker missing')
if 'renderCore(frame.buffer, frame.width, frame.height,\\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation)' not in renderer_after:
    raise SystemExit('RAWSHADING1A renderCore call changed; Phase A must not pass GainMap into rendering')
'''
new = '''renderer_after = read(renderer_rel)
if 'rawShadingGainMapApplied\\", false' not in renderer_after:
    raise SystemExit('RAWSHADING1A renderer diagnostic marker missing')
# EDGEPLACEMENTBESTFIT2A already extended renderCore with a final TC20 offset argument.
# Phase A must preserve that exact baseline call and, critically, must not consume GainMap.
if 'renderCore(frame.buffer, frame.width, frame.height,\\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0)' not in renderer_after:
    raise SystemExit('RAWSHADING1A current BESTFIT2A baseline renderCore call changed')
if 'params.gainMap' in renderer_after or 'params.mapSize' in renderer_after or 'params.hasGainMap' in renderer_after:
    raise SystemExit('RAWSHADING1A Phase A unexpectedly wires GainMap into M9R35Renderer')
'''
if old not in text:
    raise SystemExit('RAWSHADING1A FIX1 old guard anchor missing')
text = text.replace(old, new, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
