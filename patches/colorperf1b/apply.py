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

def patch_target_method(render):
    if 'M9COLORPERF1B_TARGETACTIVE_EXACT' in render:
        raise SystemExit('COLORPERF1B already applied without proof')

    ms,me=method_bounds(render,TARGET_MARKER)
    method=render[ms:me]

    # The active TARGETINPUT core can inherit a different colour transport
    # generation from the frozen prospective copy. Detect the actual transport
    # before changing anything.
    persistent_marker='M9NativeColorCore.renderFramePersistentDirectBitmap('
    existing_persistent=(persistent_marker in method)

    if existing_persistent:
        # COLORPERF1A already reached this copied target method. Do not nest a
        # second persistent scheduler; add active-route diagnostics only.
        gain='already_bound_in_existing_COLORPERF1A_target_call'
    else:
        # Otherwise find the target method's real block colour call rather than
        # assuming the legacy M9NativeColorCore spelling.
        call_markers=[
            'M9NativeColorCore.renderBlockParallelDirectBitmap(',
            'M9ColourTrial1C.renderBitmap(',
            'M9ColourTrial1C.renderBlockParallelDirectBitmap(',
            'M9ColourTrial1C.renderDirect(',
        ]
        call_marker=None;call_rel=-1
        for candidate in call_markers:
            p=method.find(candidate)
            if p>=0:
                if method.find(candidate,p+1)>=0:
                    raise SystemExit('COLORPERF1B target colour call ambiguous for '+candidate)
                call_marker=candidate;call_rel=p;break

        if call_rel<0:
            interesting=[]
            for line in method.splitlines():
                if ('nativeColor' in line or 'renderBlock' in line or
                    'renderBitmap' in line or 'renderDirect' in line or
                    'M9Colour' in line or
                    ('for (' in line and ('height' in line or 'BLOCK' in line))):
                    interesting.append(line.strip())
            raise SystemExit('COLORPERF1B target colour call missing; active method map='
                             +repr(interesting[-160:]))

        import re
        enclosing=[]
        for m in re.finditer(r'\\bfor\\s*\\(',method[:call_rel]):
            abs_start=ms+m.start()
            brace=render.find('{',abs_start,ms+call_rel)
            if brace<0: continue
            try:
                e=brace_block_end(render,abs_start)
            except SystemExit:
                continue
            if brace < ms+call_rel < e:
                enclosing.append((abs_start,e,render[abs_start:brace]))
        if not enclosing:
            context=method[max(0,call_rel-1600):min(len(method),call_rel+1000)]
            raise SystemExit('COLORPERF1B could not find enclosing target colour loop; context='+repr(context))

        loop_start,loop_end,loop_header=max(enclosing,key=lambda x:x[0])
        old_loop=render[loop_start:loop_end]
        if 'NATIVE_COLOR_BLOCK_ROWS' not in old_loop[:min(len(old_loop),1500)]:
            candidates=' | '.join(h.strip().replace('\\n',' ') for _,_,h in enclosing[-4:])
            raise SystemExit('COLORPERF1B enclosing target loop lacks frozen block geometry: '+candidates)

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

            // COLORPERF1B TARGETACTIVE1A: same proven native colour core, now on
            // the production TARGETINPUT renderer. Pixel math and partitions frozen.
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
            d.put("nativeColorPersistentFrameAttempted",
                    nativeColorCvDirectEligible && nativeColorBitmapDirectEligible);
            d.put("nativeColorPersistentFrameActive", nativeColorPersistentFrameActive);
            d.put("nativeColorWorkerTeamLaunches", nativeColorPersistentFrameActive ? 1 : nativeColorCalls);
            d.put("nativeColorBitmapLockCount", nativeColorPersistentFrameActive ? 1 : nativeColorBitmapDirectBlocks);
            d.put("nativeColorPersistentExpectedBlocks",
                    (height + NATIVE_COLOR_BLOCK_ROWS - 1) / NATIVE_COLOR_BLOCK_ROWS);'''
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
      'fallback retained':('renderBlockParallelDirectBitmap' in target
                           or 'M9ColourTrial1C.renderBitmap' in target
                           or 'M9ColourTrial1C.renderDirect' in target
                           or 'renderFramePersistentDirectBitmap' in target),
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
