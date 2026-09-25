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
    nxt=text.find('\n    private static ',start+len(marker))
    if nxt<0: raise SystemExit('COLORPERF1B next top-level method boundary missing')
    return start,nxt

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

def patch_target_method(render):
    if 'M9COLORPERF1B_TARGETACTIVE_EXACT' in render:
        raise SystemExit('COLORPERF1B already applied without proof')

    ms,me=method_bounds(render,TARGET_MARKER)
    method=render[ms:me]

    # The promoted TARGETINPUT method was generated from a later renderer and its
    # whitespace/header spelling is not guaranteed to match the legacy renderCore.
    # Bind to the actual PERF3I call, then select the nearest enclosing for-loop.
    call_marker='M9NativeColorCore.renderBlockParallelDirectBitmap('
    call_rel=method.find(call_marker)
    if call_rel<0:
        raise SystemExit('COLORPERF1B target PERF3I call missing')
    if method.find(call_marker,call_rel+1)>=0:
        raise SystemExit('COLORPERF1B target PERF3I call ambiguous')

    import re
    enclosing=[]
    for m in re.finditer(r'\\bfor\\s*\\(',method[:call_rel]):
        rel_start=m.start()
        abs_start=ms+rel_start
        brace=render.find('{',abs_start,ms+call_rel)
        if brace<0:
            continue
        try:
            end=brace_block_end(render,abs_start)
        except SystemExit:
            continue
        if brace < ms+call_rel < end:
            header=render[abs_start:brace]
            enclosing.append((abs_start,end,header))
    if not enclosing:
        context=method[max(0,call_rel-1600):min(len(method),call_rel+800)]
        raise SystemExit('COLORPERF1B could not find enclosing PERF3I for-loop; context='+repr(context))

    # The innermost enclosing for-loop is the exact block loop containing the
    # PERF3I call. Require its header to reference the frozen color block size;
    # if a generated wrapper adds an inner loop later, fail closed.
    loop_start,loop_end,loop_header=max(enclosing,key=lambda x:x[0])
    if 'NATIVE_COLOR_BLOCK_ROWS' not in loop_header:
        candidates=' | '.join(h.strip().replace('\\n',' ') for _,_,h in enclosing[-4:])
        raise SystemExit('COLORPERF1B enclosing PERF3I loop is not the frozen color-block loop: '+candidates)
    old_loop=render[loop_start:loop_end]

    # TARGETINPUT/FIXEDGAIN routes restore shading representation scale at the same
    # pre-existing render-gain boundary. Retain whichever exact expression the
    # assembled parent already uses in its eight-call fallback.
    if 'effectiveRenderGain' in old_loop:
        gain='effectiveRenderGain'
    elif 'meter.gain' in old_loop:
        gain='meter.gain'
    else:
        raise SystemExit('COLORPERF1B cannot identify frozen target render-gain expression')

    prefix=f'''            final int nativeColorPersistentBlockCount =
                    (height + NATIVE_COLOR_BLOCK_ROWS - 1) / NATIVE_COLOR_BLOCK_ROWS;
            boolean nativeColorPersistentFrameAttempted = false;
            boolean nativeColorPersistentFrameActive = false;
            long nativeColorPersistentAttemptElapsedNs = 0L;

            // COLORPERF1B TARGETACTIVE1A: apply the already byte-exact COLORPERF1A
            // native scheduler to the actual promoted TARGETINPUT renderer.
            // The 384-row geometry, 8-way worker row partitions and scalar colour
            // kernel are unchanged. False returns before mutation and uses the
            // original PERF3I eight-block loop below.
            if (nativeColorCvDirectEligible && nativeColorBitmapDirectEligible) {{
                nativeColorPersistentFrameAttempted = true;
                final long persistentStartedNs = System.nanoTime();
                nativeColorPersistentFrameActive =
                        M9NativeColorCore.renderFramePersistentDirectBitmap(
                                nativeContextForFrame,
                                nativeColorCvBaseAddress,
                                width,
                                height,
                                oriented,
                                NATIVE_COLOR_BLOCK_ROWS,
                                {gain},
                                tgCbGain,
                                tgCrGain,
                                rotation,
                                NATIVE_COLOR_WORKERS,
                                nativeStats);
                nativeColorPersistentAttemptElapsedNs =
                        System.nanoTime() - persistentStartedNs;
                nativeColorJniElapsedNsSum += nativeColorPersistentAttemptElapsedNs;
                if (nativeColorPersistentFrameActive) {{
                    nativeColorCalls = 1;
                    even = nativeStats[0];
                    edge = nativeStats[1];
                    nearWhite = nativeStats[2];
                    nativeColorTaskElapsedNsSum = nativeStats[3];
                    nativeColorWorkersUsed = nativeStats[4];
                    nativeColorScratchPrepElapsedNs = nativeStats[5];
                    nativeColorInputCopyElapsedNs = nativeStats[6];
                    nativeColorWorkerWallElapsedNs = nativeStats[7];
                    nativeColorWorkerMaxElapsedNsSum = nativeStats[8];
                    nativeColorOrientationElapsedNs = nativeStats[9];
                    nativeColorOutputCopyElapsedNs = nativeStats[10];
                    nativeColorNativeTotalElapsedNs = nativeStats[11];
                    nativeColorCvDirectBlocks = nativeColorPersistentBlockCount;
                    nativeColorBitmapDirectBlocks = nativeColorPersistentBlockCount;
                }}
            }}

            if (!nativeColorPersistentFrameActive) {{
'''
    wrapped=prefix+old_loop+'\n            }'
    render=render[:loop_start]+wrapped+render[loop_end:]

    # Scope diagnostics to the same active target method, not the legacy renderCore.
    ms,me=method_bounds(render,TARGET_MARKER)
    method=render[ms:me]
    diag='            d.put("nativeColorBitmapRowBytes", oriented.getRowBytes());'
    rel=method.find(diag)
    if rel<0: raise SystemExit('COLORPERF1B target diagnostic anchor missing')
    if method.find(diag,rel+1)>=0: raise SystemExit('COLORPERF1B target diagnostic anchor ambiguous')
    pos=ms+rel+len(diag)
    extra='''
            d.put("colorPerfRevision", "M9COLORPERF1B_TARGETACTIVE_EXACT");
            d.put("colorPerfParentRevision", "M9COLORPERF1A_PERSISTENTBLOCKS_EXACT");
            d.put("nativeColorPersistentTargetRoute", "renderNativeProspectiveCore_TARGETINPUTADAPTER1A");
            d.put("nativeColorPersistentFrameAttempted", nativeColorPersistentFrameAttempted);
            d.put("nativeColorPersistentFrameActive", nativeColorPersistentFrameActive);
            d.put("nativeColorPersistentAttemptElapsedMs", nativeColorPersistentAttemptElapsedNs / 1_000_000.0);
            d.put("nativeColorWorkerTeamLaunches", nativeColorPersistentFrameActive ? 1 : nativeColorCalls);
            d.put("nativeColorBitmapLockCount", nativeColorPersistentFrameActive ? 1 : nativeColorBitmapDirectBlocks);
            d.put("nativeColorPersistentExpectedBlocks", nativeColorPersistentBlockCount);'''
    render=render[:pos]+extra+render[pos:]
    return render,gain

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('COLORPERF1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))

    r=(root/RENDER).read_text();g=(root/GRADLE).read_text()
    c=(root/CPP).read_text();j=(root/CORE).read_text()
    ms,me=method_bounds(r,TARGET_MARKER)
    target=r[ms:me]
    checks={
      'target revision':'M9COLORPERF1B_TARGETACTIVE_EXACT' in target,
      'target call':'M9NativeColorCore.renderFramePersistentDirectBitmap' in target,
      'target attempted diag':'nativeColorPersistentFrameAttempted' in target,
      'target active diag':'nativeColorPersistentFrameActive' in target,
      'fallback retained':'M9NativeColorCore.renderBlockParallelDirectBitmap' in target,
      'target adapter retained':'targetInputAdapter1AApplied' in target,
      'native 1a core retained':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in c,
      'jni retained':'renderFramePersistentDirectBitmap' in j,
      'phase 1c retained':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in r,
      'prep 1b retained':'M9PREPPERF1B_PERSISTENT8_EXACT' in r,
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
      'activeProductionMethod':'renderNativeProspectiveCore',
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
    render,gain=patch_target_method(render)
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
      'revision':ID,'gainExpressionRetained':gain,'before':before,'after':after
    },indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
