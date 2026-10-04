#!/usr/bin/env python3
"""Harness-only FIX1 for BASISHSM1B-METERPARITY1A.

NOHDR1A writes the explicit `IsoExpoSelector.HDR = false;` assertion into
FrameNumberSelector alongside the single-frame allocation markers.  The first
METERPARITY harness incorrectly searched IsoExpoSelector.java itself.  This
wrapper corrects only that development preflight before executing the original
patch; it does not change PhotonCamera photographic code.
"""
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'apply-m9cam-basishsm1b-meterparity1a.py'
if not source.exists():
    raise SystemExit('METERPARITY1A FIX1 missing original apply harness')
text = source.read_text()

old = '''# Capture exposure / no-HDR boundary remains frozen. This is JPEG-side diagnostic work only.
if frames_path.exists():
    frames = frames_path.read_text()
    for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;']:
        if marker not in frames:
            raise SystemExit('BASISHSM1B-METERPARITY1A NOHDR boundary missing: ' + marker)
if iso_path.exists() and 'IsoExpoSelector.HDR = false;' not in iso_path.read_text():
    raise SystemExit('BASISHSM1B-METERPARITY1A HDR=false boundary missing')
'''
new = '''# Capture exposure / no-HDR boundary remains frozen. This is JPEG-side diagnostic work only.
if not frames_path.exists():
    raise SystemExit('BASISHSM1B-METERPARITY1A FrameNumberSelector missing')
frames = frames_path.read_text()
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1B-METERPARITY1A NOHDR boundary missing: ' + marker)
'''
if text.count(old) != 1:
    raise SystemExit('METERPARITY1A FIX1 NOHDR preflight anchor count=' + str(text.count(old)))
text = text.replace(old, new, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
