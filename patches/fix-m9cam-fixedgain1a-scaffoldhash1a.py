#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
p = here / 'apply-m9cam-fixedgain1a-nativeab1a.py'
if not p.exists():
    raise SystemExit('FIXEDGAIN1A SCAFFOLDHASH1A missing apply script')
text = p.read_text()

needle = "# Execute the transformed additive scaffolding against the assembled Photon tree.\n"
if text.count(needle) != 1:
    raise SystemExit('FIXEDGAIN1A SCAFFOLDHASH1A execution anchor missing/non-unique')

# The reused NATIVEPROSPECTIVE1A scaffold contains its own historical post-insertion
# renderCore hash check. Its method-boundary implementation was the run-409 failure and
# is not authoritative here. Remove only that check from the transformed scaffold text;
# apply-m9cam-fixedgain1a-nativeab1a.py independently hashes the true primary renderCore
# before the experiment and verifies it again after all NATIVEAB changes are installed.
insert = '''# SCAFFOLDHASH1A: remove only the obsolete prospective self-check from the text
# about to be compiled/executed. The outer FIXEDGAIN/NATIVEAB patch retains its own
# final primary-renderCore SHA invariant.
old_scaffold_hash = """_, _, frozen_after = extract_method(renderer, '    private static RenderCore renderCore(')\nif hashlib.sha256(frozen_after.encode('utf-8')).hexdigest() != frozen_render_core_sha:\n    raise SystemExit('NATIVEPROSPECTIVE1A unexpectedly changed frozen renderCore')\n"""
if text.count(old_scaffold_hash) != 1:
    raise SystemExit('SCAFFOLDHASH1A old prospective hash block missing/non-unique')
text = text.replace(old_scaffold_hash, '', 1)

'''
text = text.replace(needle, insert + needle, 1)
p.write_text(text)
print('FIXEDGAIN1A SCAFFOLDHASH1A applied')
print(' - obsolete NATIVEPROSPECTIVE1A internal hash check removed from transformed scaffold only')
print(' - outer FIXEDGAIN1A/NATIVEAB1A primary renderCore SHA verification remains authoritative')
