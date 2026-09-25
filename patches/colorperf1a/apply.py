#!/usr/bin/env python3
"""Apply exact COLORPERF1A surgically after the fully assembled accepted 1.93 tree."""
from pathlib import Path
import json,sys,importlib.util
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

_parent_spec=importlib.util.spec_from_file_location(
    'm9_phasenoiseperf1c_apply',REPO/'patches/phasenoiseperf1c/apply.py')
_parent_mod=importlib.util.module_from_spec(_parent_spec);_parent_spec.loader.exec_module(_parent_mod)
parent_verify=_parent_mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

CPP='app/src/main/cpp/m9color_jni.cpp'
CORE='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
ID='M9COLORPERF1A'
CHANGED={CPP,CORE,RENDER,GRADLE}
VERSION='1.94-m9colorperf1a-persistentblocks-phasenoiseperf1c-tg1'
CODE=26714

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def candidate_render_block():
    t=(HERE/'M9R35Renderer.java').read_text()
    a=t.index('            final int nativeColorBlockCount =')
    b=t.index('            cam16.release();',a)
    return t[a:b]

def candidate_core_declaration():
    t=(HERE/'M9NativeColorCore.java').read_text()
    marker='    static native boolean renderFramePersistentDirectBitmap('
    a=t.index(marker)
    # Declaration ends at the first ");" following the marker.
    b=t.index(');',a)+2
    return t[a:b]+'\n'

def apply_sources(root):
    # C++: preserve every assembled native change and append only COLORPERF1A.
    cpp=(root/CPP).read_text()
    if 'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in cpp:
        raise SystemExit('COLORPERF1A native source already applied without proof')
    cpp=one(cpp,'#include <thread>\n',
            '#include <thread>\n#include <mutex>\n#include <condition_variable>\n',
            'native includes')
    cpp=cpp.rstrip()+'\n\n'+(HERE/'native_append.inc').read_text().rstrip()+'\n'
    (root/CPP).write_text(cpp)

    # Java JNI bridge: insert one declaration into the assembled class; never
    # replace the class because later preview/source patches also own this file.
    core=(root/CORE).read_text()
    if 'renderFramePersistentDirectBitmap' in core:
        raise SystemExit('COLORPERF1A JNI declaration already applied without proof')
    close=core.rfind('\n}')
    if close<0: raise SystemExit('M9NativeColorCore class close missing')
    core=core[:close]+'\n\n'+candidate_core_declaration()+core[close:]
    (root/CORE).write_text(core)

    # Renderer: replace only the promoted PERF3I eight-block execution loop.
    # Everything before/after it (including live preview methods added by GL2*)
    # remains exactly as assembled by the accepted parent chain.
    render=(root/RENDER).read_text()
    if 'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in render:
        raise SystemExit('COLORPERF1A renderer already applied without proof')
    a=render.index('            for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS) {')
    b=render.index('            cam16.release();',a)
    render=render[:a]+candidate_render_block()+render[b:]

    diag='            d.put("nativeColorBitmapFallbackBlocks", nativeColorBitmapFallbackBlocks);\n            d.put("nativeColorBitmapRowBytes", oriented.getRowBytes());'
    diag_new=diag+'''\n            d.put("colorPerfRevision", "M9COLORPERF1A_PERSISTENTBLOCKS_EXACT");
            d.put("nativeColorPersistentFrameActive", nativeColorPersistentFrameActive);
            d.put("nativeColorPersistentWorkerTeam", nativeColorPersistentFrameActive);
            d.put("nativeColorWorkerTeamLaunches", nativeColorPersistentFrameActive ? 1 : nativeColorCalls);
            d.put("nativeColorBitmapLockCount", nativeColorPersistentFrameActive ? 1 : nativeColorBitmapDirectBlocks);'''
    render=one(render,diag,diag_new,'renderer diagnostics')
    (root/RENDER).write_text(render)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('COLORPERF1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))

    c=(root/CPP).read_text();j=(root/CORE).read_text();r=(root/RENDER).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in c,
      'persistent core':'renderFramePersistentCoreExact' in c,
      'barriers':'blockDone.wait();' in c and 'blockStatsConsumed.wait();' in c,
      'scalar colour retained':'renderStripScalar(ctx,' in c,
      'orientation mapping retained':'writeCompletedSubrangeToBitmap(argbBase, bitmapBase' in c,
      'perf3i retained':'M9NativeColorCore_renderBlockParallelDirectBitmap' in c,
      'jni declaration':'renderFramePersistentDirectBitmap' in j,
      'production call':'M9NativeColorCore.renderFramePersistentDirectBitmap' in r,
      'fallback retained':'M9NativeColorCore.renderBlockParallelDirectBitmap' in r,
      'diagnostics':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in r and 'nativeColorPersistentFrameActive' in r,
      # Critical regression guards for the compile failure that exposed stale replacement.
      'preview context retained':'exportPreviewContext2A' in r,
      'wysiwyg marker retained':'markM9LiveWysiwygDisplayed1A' in r,
      'live preview retained':'renderLivePreview1A' in r,
      'sourcecal retained':'SOURCECAL2A' in r,
      'phase 1c retained':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java').read_text(),
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('COLORPERF1A verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('COLORPERF1A version mismatch')
    return {
      'revision':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.93_M9PHASENOISEPERF1C_ADAPTIVE128_EXACT',
      'changed':sorted(CHANGED),
      'applicationMode':'surgical_on_fully_assembled_parent',
      'previewMethodsRetained':True,
      'colorBlockRows':384,'workers':8,
      'persistentWorkerTeam':True,'persistentBitmapLock':True,
      'workerRowPartitionChanged':False,'scalarColourMathChanged':False,
      'orientationMappingChanged':False,'bt601PairingChanged':False,
      'sat2Curve02Tg1Changed':False,'phaseNoise1CChanged':False,
      'prepPerf1BChanged':False,'amazeChanged':False,'autoExposureChanged':False,
      'fallbackRetained':True,'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1'" not in gradle or 'versionCode 26713' not in gradle:
        raise SystemExit('COLORPERF1A requires exact 1.93 parent identity')

    # Ensure the live-preview APIs already exist before touching the assembled renderer.
    parent_render=(root/RENDER).read_text()
    for marker in ['exportPreviewContext2A','markM9LiveWysiwygDisplayed1A','renderLivePreview1A']:
        if marker not in parent_render:
            raise SystemExit('COLORPERF1A assembled parent missing '+marker)

    before=inventory(root)
    apply_sources(root)

    gradle=one(gradle,'versionCode 26713',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
