#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
p = here / 'apply-m9cam-fixedgain1a-nativeab1a.py'
if not p.exists():
    raise SystemExit('FIXEDGAIN1A SCAFFOLDHASH1A missing apply script')
text = p.read_text()

# PRIMARYFREEZE1B: make the outer FIXEDGAIN script capture the actual Java method
# through its balanced closing brace. The previous "next private static" boundary could
# include separator/comment bytes whose placement legitimately changes when an additive
# sibling method is inserted, producing a false freeze failure even when method bytes do not.
old_outer_extractor = '''def extract_top_method(text,marker):
    start=text.find(marker)
    if start<0: raise SystemExit('method marker missing: '+marker)
    end=text.find('\\n    private static ',start+len(marker))
    if end<0: raise SystemExit('next method marker missing: '+marker)
    m=text[start:end].rstrip('\\n')
    return start,start+len(m),m
'''
new_outer_extractor = '''def extract_top_method(text,marker):
    start=text.find(marker)
    if start<0: raise SystemExit('method marker missing: '+marker)
    brace=text.find('{',start)
    if brace<0: raise SystemExit('method opening brace missing: '+marker)
    depth=0
    i=brace
    state='code'
    quote=''
    escape=False
    while i<len(text):
        ch=text[i]
        nxt=text[i+1] if i+1<len(text) else ''
        if state=='line_comment':
            if ch=='\\n': state='code'
        elif state=='block_comment':
            if ch=='*' and nxt=='/':
                state='code'; i+=1
        elif state=='string':
            if escape:
                escape=False
            elif ch=='\\\\':
                escape=True
            elif ch==quote:
                state='code'
        else:
            if ch=='/' and nxt=='/':
                state='line_comment'; i+=1
            elif ch=='/' and nxt=='*':
                state='block_comment'; i+=1
            elif ch in ('"', "'"):
                state='string'; quote=ch; escape=False
            elif ch=='{':
                depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:
                    return start,i+1,text[start:i+1]
        i+=1
    raise SystemExit('unterminated Java method: '+marker)
'''
if text.count(old_outer_extractor) != 1:
    raise SystemExit('PRIMARYFREEZE1B outer extractor block missing/non-unique')
text = text.replace(old_outer_extractor, new_outer_extractor, 1)

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

# Final preservation uses the balanced-brace method bytes captured before the experiment.
old_final = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
_, _, primary_render_core_after = extract_top_method(renderer_after, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_render_core_after.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A unexpectedly changed frozen primary renderCore')
'''
new_final = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
_, _, primary_render_core_after = extract_top_method(
        renderer_after, '    private static RenderCore renderCore(')
primary_render_core_after_sha = hashlib.sha256(
        primary_render_core_after.encode('utf-8')).hexdigest()
if primary_render_core_after_sha != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A changed frozen primary renderCore: before='
                     + primary_render_core_sha + ' after=' + primary_render_core_after_sha)
'''
if text.count(old_final) != 1:
    # Run-6 compatibility: the previous fixer may already have converted the final
    # block to exact containment. Replace that form as well.
    old_final_run6 = '''# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
# PRIMARYFREEZE1A exact-byte invariant. Do not infer the method end from the next
# member after an additive sibling has been inserted.
primary_exact_count = renderer_after.count(primary_render_core_before)
if primary_exact_count != 1:
    raise SystemExit('NATIVEAB1A primary renderCore exact-byte preservation count=' + str(primary_exact_count))
if hashlib.sha256(primary_render_core_before.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A internal pre-experiment primary renderCore SHA drift')
'''
    if text.count(old_final_run6) != 1:
        raise SystemExit('PRIMARYFREEZE1B final hash block missing/non-unique')
    text = text.replace(old_final_run6, new_final, 1)
else:
    text = text.replace(old_final, new_final, 1)

p.write_text(text)
print('FIXEDGAIN1A SCAFFOLDHASH1A + PRIMARYFREEZE1B applied')
print(' - outer primary renderCore is extracted by Java-aware balanced braces')
print(' - obsolete NATIVEPROSPECTIVE1A internal boundary hash removed from transformed scaffold')
print(' - final primary renderCore SHA compares actual method bytes before/after')
print(' - frozen non-render seams remain independently SHA-checked')
