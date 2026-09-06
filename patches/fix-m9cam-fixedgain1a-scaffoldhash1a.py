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
# is not authoritative here. Remove only that check from the transformed scaffold text.
insert = '''# SCAFFOLDHASH1A: remove only the obsolete prospective self-check from the text
# about to be compiled/executed. The outer FIXEDGAIN/NATIVEAB patch retains an exact-byte
# final production renderCore invariant.
old_scaffold_hash = """_, _, frozen_after = extract_method(renderer, '    private static RenderCore renderCore(')\nif hashlib.sha256(frozen_after.encode('utf-8')).hexdigest() != frozen_render_core_sha:\n    raise SystemExit('NATIVEPROSPECTIVE1A unexpectedly changed frozen renderCore')\n"""
if text.count(old_scaffold_hash) != 1:
    raise SystemExit('SCAFFOLDHASH1A old prospective hash block missing/non-unique')
text = text.replace(old_scaffold_hash, '', 1)

'''
text = text.replace(needle, insert + needle, 1)

# The outer apply script originally re-used the same fragile "next private static member"
# extraction after adding the sibling method. Replace that boundary-dependent comparison
# with an exact containment invariant: the complete original production renderCore byte
# sequence (including its original declaration) must occur exactly once after the additive
# experiment is installed. The transformed sibling has a different declaration/body and
# cannot satisfy this check.
old_final = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
_, _, primary_render_core_after = extract_top_method(renderer_after, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_render_core_after.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A unexpectedly changed frozen primary renderCore')
'''
new_final = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
# PRIMARYFREEZE1A exact-byte invariant. Do not infer the method end from the next
# member after an additive sibling has been inserted.
primary_exact_count = renderer_after.count(primary_render_core_before)
if primary_exact_count != 1:
    raise SystemExit('NATIVEAB1A primary renderCore exact-byte preservation count=' + str(primary_exact_count))
if hashlib.sha256(primary_render_core_before.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A internal pre-experiment primary renderCore SHA drift')
'''
if text.count(old_final) != 1:
    raise SystemExit('PRIMARYFREEZE1A old final hash block missing/non-unique')
text = text.replace(old_final, new_final, 1)

p.write_text(text)
print('FIXEDGAIN1A SCAFFOLDHASH1A + PRIMARYFREEZE1A applied')
print(' - obsolete NATIVEPROSPECTIVE1A internal boundary hash removed from transformed scaffold')
print(' - production renderCore must remain as one exact unchanged byte sequence')
print(' - frozen non-render seams remain independently SHA-checked by FIXEDGAIN1A/NATIVEAB1A')
