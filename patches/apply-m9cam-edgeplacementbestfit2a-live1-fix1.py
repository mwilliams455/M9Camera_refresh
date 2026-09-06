#!/usr/bin/env python3
"""FIX1 wrapper for EDGEPLACEMENTBESTFIT2A LIVE1 apply harness.

The first LIVE1 harness asserted three native colour call sites, but the promoted
renderer has four: direct-bitmap, direct fallback, direct outer fallback, and
copied-input fallback. This wrapper corrects only that development self-check
before executing the original patch. No PhotonCamera source is altered here.
"""
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'apply-m9cam-edgeplacementbestfit2a-live1.py'
if not source.exists():
    raise SystemExit('LIVE1 FIX1 missing original apply harness')
text = source.read_text()
old = """count_gain_calls = renderer.count('meter.gain, tgCbGain')
if count_gain_calls != 3:
    raise SystemExit(f'BESTFIT2A expected 3 native colour gain call sites, found {count_gain_calls}')
"""
new = """count_gain_calls = renderer.count('meter.gain, tgCbGain')
if count_gain_calls != 4:
    raise SystemExit(f'BESTFIT2A expected 4 native colour gain call sites, found {count_gain_calls}')
"""
if old not in text:
    raise SystemExit('LIVE1 FIX1 original gain-call self-check anchor missing')
text = text.replace(old, new, 1)
code = compile(text, str(source), 'exec')
globals_dict = {'__name__': '__main__', '__file__': str(source)}
exec(code, globals_dict, globals_dict)
