#!/usr/bin/env python3
"""Verifier harness FIX1 for BASISHSM1B-METERPARITY1A.

The NOHDR1A explicit HDR=false assertion lives in FrameNumberSelector with the
single-frame boundary.  Correct that verifier-only file-location assumption and
then execute the original verifier unchanged.
"""
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'verify-m9cam-basishsm1b-meterparity1a.py'
if not source.exists():
    raise SystemExit('METERPARITY1A verify FIX1 missing original verifier')
text = source.read_text()

old_paths = '''iso_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
for p in [renderer_path, gradle_path, frames_path, iso_path]:
'''
new_paths = '''iso_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
for p in [renderer_path, gradle_path, frames_path]:
'''
if text.count(old_paths) != 1:
    raise SystemExit('METERPARITY1A verify FIX1 path anchor count=' + str(text.count(old_paths)))
text = text.replace(old_paths, new_paths, 1)

old_check = '''require(iso, 'IsoExpoSelector.HDR = false;', 'HDR disabled boundary')
'''
new_check = '''require(frames, 'IsoExpoSelector.HDR = false;', 'HDR disabled boundary')
'''
if text.count(old_check) != 1:
    raise SystemExit('METERPARITY1A verify FIX1 HDR marker anchor count=' + str(text.count(old_check)))
text = text.replace(old_check, new_check, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
