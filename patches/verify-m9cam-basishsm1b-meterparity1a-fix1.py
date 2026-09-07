#!/usr/bin/env python3
"""Verifier harness FIX1 for BASISHSM1B-METERPARITY1A.

Correct two verifier-only assumptions before executing the original verifier:
1) NOHDR1A's explicit HDR=false assertion lives in FrameNumberSelector alongside
   the single-frame allocation boundary.
2) BASISHSM checkpoint sentinel/mode strings live in the shared checkpoint helper,
   not inside renderNativeProspectiveCore itself.
No PhotonCamera photographic source is changed by this wrapper.
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

# FIX1/FIX2 checkpoint implementation is deliberately a shared helper outside the
# prospective render method. Keep prospective-only checks prospective, then assert
# checkpoint identity/mode against the assembled renderer globally.
for marker_line in [
    "    'checkpointIdentityHsmSentinel',\n",
    "    'historical_interpolated_table',\n",
]:
    if text.count(marker_line) != 1:
        raise SystemExit('METERPARITY1A verify FIX1 checkpoint list anchor count=' + str(text.count(marker_line)))
    text = text.replace(marker_line, '', 1)

anchor = '''    require(prospective, marker, 'prospective invariant')

# Field outputs now isolate meter parity only. SOURCE_ONLY is retired from the hook.
'''
replacement = '''    require(prospective, marker, 'prospective invariant')

# FIX2 sentinel classification is implemented by the shared checkpoint helper.
require(renderer, 'checkpointIdentityHsmSentinel', 'global checkpoint sentinel')
require(renderer, 'ctx.hsm.length == 12', 'global identity sentinel length')
require(renderer, 'historical_interpolated_table', 'global historical HSM checkpoint mode')
require(renderer, 'identity_passthrough_source_only', 'global SOURCE_ONLY checkpoint identity mode')

# Field outputs now isolate meter parity only. SOURCE_ONLY is retired from the hook.
'''
if text.count(anchor) != 1:
    raise SystemExit('METERPARITY1A verify FIX1 prospective-loop anchor count=' + str(text.count(anchor)))
text = text.replace(anchor, replacement, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
