#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
p = here / 'apply-m9cam-fixedgain1a-nativeab1a.py'
if not p.exists():
    raise SystemExit('FIXEDGAIN1A SCAFFOLDHASH1A missing apply script')
text = p.read_text()

# PRIMARYFREEZE1D: extract the actual Java method through balanced braces.
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
            if ch=='*' and nxt=='/': state='code'; i+=1
        elif state=='string':
            if escape: escape=False
            elif ch=='\\\\': escape=True
            elif ch==quote: state='code'
        else:
            if ch=='/' and nxt=='/': state='line_comment'; i+=1
            elif ch=='/' and nxt=='*': state='block_comment'; i+=1
            elif ch in ('"', "'"): state='string'; quote=ch; escape=False
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return start,i+1,text[start:i+1]
        i+=1
    raise SystemExit('unterminated Java method: '+marker)
'''
if text.count(old_outer_extractor) != 1:
    raise SystemExit('PRIMARYFREEZE1D outer extractor block missing/non-unique')
text = text.replace(old_outer_extractor, new_outer_extractor, 1)

needle = "# Execute the transformed additive scaffolding against the assembled Photon tree.\n"
if text.count(needle) != 1:
    raise SystemExit('FIXEDGAIN1A execution anchor missing/non-unique')

# Patch the prospective source text immediately before compile/exec.
insert = '''# SCAFFOLDHASH1A: remove obsolete prospective self-check only.
old_scaffold_hash = """_, _, frozen_after = extract_method(renderer, '    private static RenderCore renderCore(')\nif hashlib.sha256(frozen_after.encode('utf-8')).hexdigest() != frozen_render_core_sha:\n    raise SystemExit('NATIVEPROSPECTIVE1A unexpectedly changed frozen renderCore')\n"""
if text.count(old_scaffold_hash) != 1:
    raise SystemExit('SCAFFOLDHASH1A old prospective hash block missing/non-unique')
text = text.replace(old_scaffold_hash, '', 1)

# CAMERA2TYPE1A: SENSOR_REFERENCE_ILLUMINANT2 is Key<Byte> in the Android API.
# The historical additive scaffold declared it as Integer, which reaches javac only
# after the freeze/insertion problems are fixed. Correct the prospective source only.
old_ref2_decl = "        Integer ref2Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2);"
new_ref2_decl = "        Byte ref2Obj = characteristics.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2);"
if text.count(old_ref2_decl) != 1:
    raise SystemExit('CAMERA2TYPE1A SENSOR_REFERENCE_ILLUMINANT2 declaration missing/non-unique')
text = text.replace(old_ref2_decl, new_ref2_decl, 1)

# SCAFFOLDINSERT1A: NATIVEPROSPECTIVE1A captured orig_end before adding imports,
# then used that stale character offset after the imports changed renderer length.
# Recompute the exact production-method location from its frozen byte sequence at the
# moment of insertion. This is the root cause of the run-8 splice into renderCore.finally.
old_insert_line = "renderer = renderer[:orig_end] + '\\\\n\\\\n' + prospective + renderer[orig_end:]"
new_insert_block = """actual_primary_start = renderer.find(frozen_render_core)
if actual_primary_start < 0:
    raise SystemExit('NATIVEPROSPECTIVE1A frozen primary renderCore bytes missing before sibling insertion')
actual_primary_end = actual_primary_start + len(frozen_render_core)
renderer = renderer[:actual_primary_end] + chr(10) + chr(10) + prospective + renderer[actual_primary_end:]"""
if text.count(old_insert_line) != 1:
    raise SystemExit('SCAFFOLDINSERT1A stale insertion line missing/non-unique')
text = text.replace(old_insert_line, new_insert_block, 1)

'''
text = text.replace(needle, insert + needle, 1)

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
    import difflib
    primary_diff = ''.join(difflib.unified_diff(
            primary_render_core_before.splitlines(True),
            primary_render_core_after.splitlines(True),
            fromfile='primary_renderCore_before', tofile='primary_renderCore_after', n=3))
    print('PRIMARYFREEZE1D_DIFF_BEGIN')
    print(primary_diff[:16000])
    print('PRIMARYFREEZE1D_DIFF_END')
    raise SystemExit('NATIVEAB1A changed frozen primary renderCore: before='
                     + primary_render_core_sha + ' after=' + primary_render_core_after_sha)
'''
if text.count(old_final) != 1:
    raise SystemExit('PRIMARYFREEZE1D final hash block missing/non-unique')
text = text.replace(old_final, new_final, 1)

# APKNAME1A: retain the full versionName for provenance/verifiers, but decouple the
# physical APK filename from that ever-growing experiment suffix. Linux filesystems
# reject a single filename >255 bytes; the prior JSONSAFE1A build compiled cleanly
# and failed only at :app:packageDebug for that reason.
apkname_anchor = "write(gradle_rel, gradle)\nwrite(renderer_rel, renderer)"
apkname_replacement = '''# APKNAME1A: compact output filename only; Android versionName stays fully descriptive.
output_name_re = re.compile(r'outputFileName\\s*=\\s*"[^"\\n]*\\$\\{versionName\\}[^"\\n]*"')
output_name_matches = output_name_re.findall(gradle)
if len(output_name_matches) != 1:
    raise SystemExit('APKNAME1A expected one versionName-derived outputFileName, got ' + str(len(output_name_matches)))
gradle = output_name_re.sub(
        'outputFileName = "M9Cam-NAB1-${versionBuild}-${variant.name}.apk"', gradle, count=1)
write(gradle_rel, gradle)
write(renderer_rel, renderer)'''
if text.count(apkname_anchor) != 1:
    raise SystemExit('APKNAME1A gradle write anchor missing/non-unique')
text = text.replace(apkname_anchor, apkname_replacement, 1)

p.write_text(text)
print('FIXEDGAIN1A SCAFFOLDHASH1A + SCAFFOLDINSERT1A + PRIMARYFREEZE1D + CAMERA2TYPE1A + APKNAME1A applied')
print(' - prospective sibling insertion offset is recomputed after import edits')
print(' - prospective separator uses chr(10), avoiding nested string escaping')
print(' - production renderCore is protected by balanced-brace before/after SHA')
print(' - SENSOR_REFERENCE_ILLUMINANT2 prospective declaration uses Android Key<Byte>')
print(' - obsolete historical boundary self-check removed only inside scaffold')
print(' - APK output filename is compact; full Android versionName/provenance remains intact')