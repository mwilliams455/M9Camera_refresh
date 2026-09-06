#!/usr/bin/env python3
"""FIX1 wrapper for EDGEPLACEMENTBESTFIT2A LIVE1 verifier.

Corrects two development-harness mistakes only:
- promoted renderer has four effective-render-gain native colour call sites;
- exact Q14 BT.601 coefficients sum to 16384, so white maps to 255.
"""
from pathlib import Path

here = Path(__file__).resolve().parent
source = here / 'verify-m9cam-edgeplacementbestfit2a-live1.py'
if not source.exists():
    raise SystemExit('LIVE1 FIX1 missing original verifier')
text = source.read_text()
replacements = {
    "if r.count('effectiveRenderGain, tgCbGain') != 3:":
        "if r.count('effectiveRenderGain, tgCbGain') != 4:",
    "BESTFIT2A LIVE1 verify expected exactly 3 effectiveRenderGain native call sites":
        "BESTFIT2A LIVE1 verify expected exactly 4 effectiveRenderGain native call sites",
    "if q14_y(255,255,255) != 254:":
        "if q14_y(255,255,255) != 255:",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit('LIVE1 FIX1 verifier anchor missing: ' + old)
    text = text.replace(old, new, 1)
code = compile(text, str(source), 'exec')
globals_dict = {'__name__': '__main__', '__file__': str(source)}
exec(code, globals_dict, globals_dict)
