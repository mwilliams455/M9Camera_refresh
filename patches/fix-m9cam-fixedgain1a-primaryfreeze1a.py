#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
p = here / 'apply-m9cam-fixedgain1a-nativeab1a.py'
if not p.exists():
    raise SystemExit('FIXEDGAIN1A PRIMARYFREEZE1A missing apply script')
text = p.read_text()

old = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
_, _, primary_render_core_after = extract_top_method(renderer_after, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_render_core_after.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A unexpectedly changed frozen primary renderCore')
'''
new = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
# PRIMARYFREEZE1A: the earlier next-member extractor is deliberately not reused after
# an additive sibling method has been inserted. Require the exact original production
# renderCore byte sequence, including its original declaration, to occur once unchanged.
# The experimental sibling has a different declaration and transformed body, so it cannot
# satisfy this exact containment check.
primary_exact_count = renderer_after.count(primary_render_core_before)
if primary_exact_count != 1:
    raise SystemExit('NATIVEAB1A primary renderCore exact-byte preservation count=' + str(primary_exact_count))
if hashlib.sha256(primary_render_core_before.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A internal pre-experiment primary renderCore SHA drift')
'''
if text.count(old) != 1:
    raise SystemExit('PRIMARYFREEZE1A old final hash block missing/non-unique')
text = text.replace(old, new, 1)
p.write_text(text)
print('FIXEDGAIN1A PRIMARYFREEZE1A applied')
print(' - final primary freeze now requires exact original renderCore bytes to occur once')
print(' - additive prospective sibling cannot satisfy the invariant because its declaration/body differ')
