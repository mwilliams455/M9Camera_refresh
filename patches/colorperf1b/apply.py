#!/usr/bin/env python3
"""Promote the already-proven COLORPERF1A persistent colour core onto the
actual production TARGETINPUT/native-source renderer.

1.94 proved the native core and packaged it, but its Java call site was inserted
only in the legacy renderCore. Current production uses renderNativeProspectiveCore
through TARGETINPUTADAPTER1A, so phone captures correctly remained on 8 PERF3I
block calls. This patch changes orchestration only; native colour math is untouched.
"""
from pathlib import Path
import json,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

_parent_spec=importlib.util.spec_from_file_location(
    'm9_colorperf1a_apply',REPO/'patches/colorperf1a/apply.py')
_parent_mod=importlib.util.module_from_spec(_parent_spec);_parent_spec.loader.exec_module(_parent_mod)
parent_verify=_parent_mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
CPP='app/src/main/cpp/m9color_jni.cpp'
CORE='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
ID='M9COLORPERF1B'
CHANGED={RENDER,GRADLE}
VERSION='1.95-m9colorperf1b-targetactive-colorperf1a-phasenoiseperf1c-tg1'
CODE=26715

TARGET_MARKER='    private static RenderCore renderNativeProspectiveCore(ByteBuffer rawBuffer,'

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def method_bounds(text,marker):
    start=text.find(marker)
    if start<0: raise SystemExit('COLORPERF1B target method missing: '+marker.strip())
    brace=text.find('{',start)
    if brace<0: raise SystemExit('COLORPERF1B target method opening brace missing')
    depth=0
    i=brace
    state='code'
    quote=''
    esc=False
    while i<len(text):
        ch=text[i]
        nxt=text[i+1] if i+1<len(text) else ''
        if state=='line':
            if ch=='\n': state='code'
        elif state=='block':
            if ch=='*' and nxt=='/':
                state='code'; i+=1
        elif state=='string':
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch==quote: state='code'
        else:
            if ch=='/' and nxt=='/':
                state='line'; i+=1
            elif ch=='/' and nxt=='*':
                state='block'; i+=1
            elif ch in ('"',"'"):
                state='string'; quote=ch; esc=False
            elif ch=='{':
                depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:
                    return start,i+1
        i+=1
    raise SystemExit('COLORPERF1B target method unterminated')

def brace_block_end(text,start):
    brace=text.find('{',start)
    if brace<0: raise SystemExit('COLORPERF1B block opening brace missing')
    depth=0
    i=brace
    in_string=False; quote=''; escape=False
    while i<len(text):
        ch=text[i]
        if in_string:
            if escape: escape=False
            elif ch=='\\': escape=True
            elif ch==quote: in_string=False
        else:
            if ch in ('"',"'"): in_string=True;quote=ch
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:return i+1
        i+=1
    raise SystemExit('COLORPERF1B unterminated block')

def rendercore_spans(text):
    import re
    spans=[]
    for m in re.finditer(r'(?m)^\s*private\s+static\s+RenderCore\s+([A-Za-z0-9_]+)\s*\(',text):
        method_name=m.group(1)
        method_start=m.start()
        brace=text.find('{',m.end())
        if brace<0:
            continue
        depth=0;i=brace;state='code';quote='';esc=False
        while i<len(text):
            ch=text[i];nxt=text[i+1] if i+1<len(text) else ''
            if state=='line':
                if ch=='\n': state='code'
            elif state=='block':
                if ch=='*' and nxt=='/': state='code';i+=1
            elif state=='string':
                if esc: esc=False
                elif ch=='\\': esc=True
                elif ch==quote: state='code'
            else:
                if ch=='/' and nxt=='/': state='line';i+=1
                elif ch=='/' and nxt=='*': state='block';i+=1
                elif ch in ('"',"'"): state='string';quote=ch;esc=False
                elif ch=='{': depth+=1
                elif ch=='}':
                    depth-=1
                    if depth==0:
                        spans.append((method_name,method_start,i+1))
                        break
            i+=1
    return spans

def find_active_color_owner(render):
    # COLORPERF1A surgically replaced one historical PERF3I loop but deliberately
    # left every later assembled method intact. Find every RenderCore method that
    # still owns the frozen 384-row colour loop, then identify the production
    # TARGETINPUT owner from its target-input state/telemetry rather than a method name.
    loop_marker='for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS)'
    owners=[]
    for name,a,b in rendercore_spans(render):
        method=render[a:b]
        if loop_marker not in method:
            continue
        owners.append({
            'name':name,'start':a,'end':b,
            'targetState':('targetInputAdapter1AApplied' in method
                           or 'targetInputAdapter1AProduction' in method
                           or 'TARGETINPUTADAPTER1A' in method),
            'already1A':('M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in method
                         or 'renderFramePersistentDirectBitmap(' in method),
            'effectiveGain':('effectiveRenderGain' in method),
            'bitmapDirect':('nativeColorBitmapDirectEligible' in method),
            'cvDirect':('nativeColorCvDirectEligible' in method),
        })

    target=[o for o in owners if o['targetState'] and not o['already1A']]
    if len(target)!=1:
        # Some later source patches move TARGETINPUT telemetry to the wrapper but
        # leave the inner pixel core anonymous. In that case the still-unpatched
        # colour owner is uniquely the method with the complete direct-Bitmap
        # transport and without COLORPERF1A's persistent call.
        target=[o for o in owners if (not o['already1A']
                                      and o['bitmapDirect'] and o['cvDirect']
                                      and o['effectiveGain'])]
    if len(target)!=1:
        raise SystemExit('COLORPERF1B could not uniquely identify active colour owner: '
                         +json.dumps(owners,sort_keys=True))
    return target[0],owners

def patch_target_method(render):
    if 'M9COLORPERF1B_TARGETACTIVE_EXACT' in render:
        raise SystemExit('COLORPERF1B already applied without proof')

    owner,owners=find_active_color_owner(render)
    ms,me=owner['start'],owner['end']
    method=render[ms:me]
    loop_marker='for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS)'
    rel=method.find(loop_marker)
    if rel<0 or method.find(loop_marker,rel+1)>=0:
        raise SystemExit('COLORPERF1B active colour loop missing/ambiguous in '+owner['name'])

    # Include leading indentation when replacing the exact for block.
    line_start=method.rfind('\n',0,rel)+1
    loop_start=ms+line_start
    loop_end=brace_block_end(render,ms+rel)
    old_loop=render[loop_start:loop_end]

    if 'renderBlockParallelDirectBitmap(' not in old_loop:
        raise SystemExit('COLORPERF1B selected loop is not PERF3I direct-Bitmap path')
    if 'effectiveRenderGain' in old_loop:
        gain='effectiveRenderGain'
    elif 'meter.gain' in old_loop:
        gain='meter.gain'
    else:
        raise SystemExit('COLORPERF1B cannot identify frozen target render-gain expression')

    indent=method[line_start:rel]
    prefix=f'''{indent}final int nativeColorPersistentBlockCount =
{indent}        (height + NATIVE_COLOR_BLOCK_ROWS - 1) / NATIVE_COLOR_BLOCK_ROWS;
{indent}boolean nativeColorPersistentFrameAttempted = false;
{indent}boolean nativeColorPersistentFrameActive = false;
{indent}long nativeColorPersistentAttemptElapsedNs = 0L;

{indent}// COLORPERF1B TARGETACTIVE1A: same byte-exact COLORPERF1A native core,
{indent}// now bound to the unpatched production colour owner discovered from
{indent}// assembled TARGETINPUT/direct-Bitmap state. Pixel math and partitions frozen.
{indent}if (nativeColorCvDirectEligible && nativeColorBitmapDirectEligible) {{
{indent}    nativeColorPersistentFrameAttempted = true;
{indent}    final long persistentStartedNs = System.nanoTime();
{indent}    nativeColorPersistentFrameActive =
{indent}            M9NativeColorCore.renderFramePersistentDirectBitmap(
{indent}                    nativeContextForFrame,
{indent}                    nativeColorCvBaseAddress,
{indent}                    width,
{indent}                    height,
{indent}                    oriented,
{indent}                    NATIVE_COLOR_BLOCK_ROWS,
{indent}                    {gain},
{indent}                    tgCbGain,
{indent}                    tgCrGain,
{indent}                    rotation,
{indent}                    NATIVE_COLOR_WORKERS,
{indent}                    nativeStats);
{indent}    nativeColorPersistentAttemptElapsedNs =
{indent}            System.nanoTime() - persistentStartedNs;
{indent}    nativeColorJniElapsedNsSum += nativeColorPersistentAttemptElapsedNs;
{indent}    if (nativeColorPersistentFrameActive) {{
{indent}        nativeColorCalls = 1;
{indent}        even = nativeStats[0];
{indent}        edge = nativeStats[1];
{indent}        nearWhite = nativeStats[2];
{indent}        nativeColorTaskElapsedNsSum = nativeStats[3];
{indent}        nativeColorWorkersUsed = nativeStats[4];
{indent}        nativeColorScratchPrepElapsedNs = nativeStats[5];
{indent}        nativeColorInputCopyElapsedNs = nativeStats[6];
{indent}        nativeColorWorkerWallElapsedNs = nativeStats[7];
{indent}        nativeColorWorkerMaxElapsedNsSum = nativeStats[8];
{indent}        nativeColorOrientationElapsedNs = nativeStats[9];
{indent}        nativeColorOutputCopyElapsedNs = nativeStats[10];
{indent}        nativeColorNativeTotalElapsedNs = nativeStats[11];
{indent}        nativeColorCvDirectBlocks = nativeColorPersistentBlockCount;
{indent}        nativeColorBitmapDirectBlocks = nativeColorPersistentBlockCount;
{indent}    }}
{indent}}}

{indent}if (!nativeColorPersistentFrameActive) {{
'''
    wrapped=prefix+old_loop+'\n'+indent+'}'
    render=render[:loop_start]+wrapped+render[loop_end:]

    # Re-discover the owner after insertion so offsets are current.
    spans=rendercore_spans(render)
    matches=[]
    for name,a,b in spans:
        method2=render[a:b]
        if ('M9NativeColorCore.renderFramePersistentDirectBitmap(' in method2
                and 'renderBlockParallelDirectBitmap(' in method2
                and (name==owner['name'] or 'targetInputAdapter1AApplied' in method2
                     or 'effectiveRenderGain' in method2)):
            matches.append((name,a,b))
    # Legacy COLORPERF1A also has the persistent call, so select the method that
    # now contains our unique attempt variable.
    matches=[m for m in matches if 'nativeColorPersistentAttemptElapsedNs' in render[m[1]:m[2]]]
    if len(matches)!=1:
        raise SystemExit('COLORPERF1B post-insert active owner ambiguous: '+repr([m[0] for m in matches]))
    owner_name,ms,me=matches[0]
    method=render[ms:me]

    diag='d.put("nativeColorBitmapRowBytes", oriented.getRowBytes());'
    rel=method.find(diag)
    if rel<0 or method.find(diag,rel+1)>=0:
        raise SystemExit('COLORPERF1B active diagnostic anchor missing/ambiguous in '+owner_name)
    pos=ms+rel+len(diag)
    diag_indent=method[method.rfind('\n',0,rel)+1:rel]
    extra=f'''
{diag_indent}d.put("colorPerfRevision", "M9COLORPERF1B_TARGETACTIVE_EXACT");
{diag_indent}d.put("colorPerfParentRevision", "M9COLORPERF1A_PERSISTENTBLOCKS_EXACT");
{diag_indent}d.put("nativeColorPersistentTargetRoute", "{owner_name}");
{diag_indent}d.put("nativeColorPersistentFrameAttempted", nativeColorPersistentFrameAttempted);
{diag_indent}d.put("nativeColorPersistentFrameActive", nativeColorPersistentFrameActive);
{diag_indent}d.put("nativeColorPersistentAttemptElapsedMs", nativeColorPersistentAttemptElapsedNs / 1_000_000.0);
{diag_indent}d.put("nativeColorWorkerTeamLaunches", nativeColorPersistentFrameActive ? 1 : nativeColorCalls);
{diag_indent}d.put("nativeColorBitmapLockCount", nativeColorPersistentFrameActive ? 1 : nativeColorBitmapDirectBlocks);
{diag_indent}d.put("nativeColorPersistentExpectedBlocks", nativeColorPersistentBlockCount);'''
    render=render[:pos]+extra+render[pos:]
    return render,gain,owner_name,owners

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('COLORPERF1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))

    r=(root/RENDER).read_text();g=(root/GRADLE).read_text()
    c=(root/CPP).read_text();j=(root/CORE).read_text()
    active=[]
    for name,a,b in rendercore_spans(r):
        method=r[a:b]
        if 'M9COLORPERF1B_TARGETACTIVE_EXACT' in method:
            active.append((name,method))
    if len(active)!=1:
        raise SystemExit('COLORPERF1B verify active-owner count='+str(len(active)))
    owner_name,target=active[0]
    checks={
      'target revision':'M9COLORPERF1B_TARGETACTIVE_EXACT' in target,
      'target call':'M9NativeColorCore.renderFramePersistentDirectBitmap' in target,
      'target attempted diag':'nativeColorPersistentFrameAttempted' in target,
      'target active diag':'nativeColorPersistentFrameActive' in target,
      'fallback retained':'renderBlockParallelDirectBitmap' in target,
      'direct transport':'nativeColorBitmapDirectEligible' in target and 'nativeColorCvDirectEligible' in target,
      'native 1a core retained':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in c,
      'jni retained':'renderFramePersistentDirectBitmap' in j,
      'phase 1c retained':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in
              (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java').read_text(),
      'prep 1b retained':'M9PREPPERF1B_PERSISTENT8_EXACT' in
              (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java').read_text(),
      'target input provenance':('targetInputAdapter1AApplied' in r
                                 and 'm9cam.renderer.targetinputadapter' in r),
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('COLORPERF1B verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('COLORPERF1B version mismatch')
    return {
      'revision':'M9COLORPERF1B_TARGETACTIVE_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.94_M9COLORPERF1A_PERSISTENTBLOCKS_EXACT',
      'changed':sorted(CHANGED),
      'activeProductionMethod':owner_name,
      'persistentNativeCoreChanged':False,
      'scalarColourMathChanged':False,
      'workerRowPartitionChanged':False,
      'colorBlockRowsChanged':False,
      'orientationMappingChanged':False,
      'bt601PairingChanged':False,
      'sat2Curve02Tg1Changed':False,
      'phaseNoiseChanged':False,
      'prepChanged':False,
      'autoExposureChanged':False,
      'fallbackRetained':True,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    # 1.94 must already be assembled and verified first.
    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.94-m9colorperf1a-persistentblocks-phasenoiseperf1c-tg1'" not in gradle or 'versionCode 26714' not in gradle:
        raise SystemExit('COLORPERF1B requires exact 1.94 assembled parent identity')

    before=inventory(root)
    render=(root/RENDER).read_text()
    render,gain,owner_name,owners=patch_target_method(render)
    (root/RENDER).write_text(render)

    gradle=one(gradle,'versionCode 26714',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.94-m9colorperf1a-persistentblocks-phasenoiseperf1c-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({
      'revision':ID,'gainExpressionRetained':gain,'activeColorOwner':owner_name,'discoveredColorOwners':owners,'before':before,'after':after
    },indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
