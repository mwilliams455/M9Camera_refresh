#!/usr/bin/env python3
"""1.96 COLORPERFROLLBACK1A.

Disable only the COLORPERF1B persistent full-frame scheduling attempt and force
its already-retained PERF3I eight-block fallback. This is a surgical rollback
after a phone colour regression. All photographic math and all earlier accepted
performance stages stay frozen.
"""
from pathlib import Path
import json,sys,importlib.util,re

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_colorperf1b_apply',REPO/'patches/colorperf1b/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
ID='M9COLORPERFROLLBACK1A'
CHANGED={RENDER,GRADLE}
VERSION='1.96-m9colorperfrollback1a-perf3i-phasenoiseperf1c-tg1'
CODE=26716

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def method_span_with(text,needle):
    pos=text.find(needle)
    if pos<0: raise SystemExit('rollback target marker missing: '+needle)
    starts=[]
    for m in re.finditer(r'(?m)^\s*private\s+static\s+RenderCore\s+[A-Za-z0-9_]+\s*\(',text):
        if m.start()<pos: starts.append(m.start())
    if not starts: raise SystemExit('rollback enclosing RenderCore missing')
    start=starts[-1]
    brace=text.find('{',start)
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
            elif ch in ('"',"'"): state='string';quote=ch
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:return start,i+1
        i+=1
    raise SystemExit('rollback target method unterminated')

def patch_renderer(text):
    marker='"M9COLORPERF1B_TARGETACTIVE_EXACT"'
    ms,me=method_span_with(text,marker)
    method=text[ms:me]

    if 'nativeColorPersistentFrameEnabled' in method:
        raise SystemExit('rollback already applied without proof')

    # Bind to the exact persistent attempt in the active 1.95 method.
    old='''            if (nativeColorCvDirectEligible && nativeColorBitmapDirectEligible) {
                nativeColorPersistentFrameAttempted = true;'''
    new='''            // COLORPERFROLLBACK1A: phone validation exposed a severe colour
            // regression only when the 1.95 persistent full-frame scheduler was active.
            // Keep the native core and fallback intact, but force the byte-proven PERF3I
            // eight-block path while the persistent scheduler is investigated offline.
            final boolean nativeColorPersistentFrameEnabled = false;
            if (nativeColorPersistentFrameEnabled
                    && nativeColorCvDirectEligible && nativeColorBitmapDirectEligible) {
                nativeColorPersistentFrameAttempted = true;'''
    if method.count(old)!=1:
        raise SystemExit('rollback persistent-attempt anchor count='+str(method.count(old)))
    method=method.replace(old,new,1)

    # Replace only the 1.95 route label in this method. Keep the original fields
    # so phone diagnostics can show attempted=false / active=false.
    olddiag='''            d.put("colorPerfRevision", "M9COLORPERF1B_TARGETACTIVE_EXACT");'''
    newdiag='''            d.put("colorPerfRevision", "M9COLORPERFROLLBACK1A_PERF3I_EXACT");
            d.put("colorPerfParentRevision", "M9COLORPERF1B_TARGETACTIVE_EXACT");
            d.put("nativeColorPersistentFrameEnabled", nativeColorPersistentFrameEnabled);
            d.put("colorPerfRollbackReason", "phone_colour_regression_20260926");
            d.put("colorPerfRollbackExpectedNativeCalls", nativeColorPersistentFrameEnabled ? 1 : 8);'''
    if method.count(olddiag)!=1:
        raise SystemExit('rollback diagnostic anchor count='+str(method.count(olddiag)))
    method=method.replace(olddiag,newdiag,1)

    return text[:ms]+method+text[me:]

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('COLORPERFROLLBACK1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('rollback unexpected changed files: '+repr(sorted(changed)))

    r=(root/RENDER).read_text();g=(root/GRADLE).read_text()
    ms,me=method_span_with(r,'"M9COLORPERFROLLBACK1A_PERF3I_EXACT"')
    target=r[ms:me]
    checks={
      'rollback revision':'M9COLORPERFROLLBACK1A_PERF3I_EXACT' in target,
      'persistent disabled':'final boolean nativeColorPersistentFrameEnabled = false;' in target,
      'persistent call retained for future investigation':'renderFramePersistentDirectBitmap' in target,
      'PERF3I fallback retained':'renderBlockParallelDirectBitmap' in target,
      'SAT2 telemetry retained':'nativeSaturationMode1A' in r and 'SAT2_STANDARD_M04_M05' in r,
      'SAT2 selected bank telemetry retained':'nativeSaturationBankActuallySelected' in r,
      'phase 1c retained':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in
         (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java').read_text(),
      'prep 1b retained':'M9PREPPERF1B_PERSISTENT8_EXACT' in
         (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java').read_text(),
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('COLORPERFROLLBACK1A verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('COLORPERFROLLBACK1A version mismatch')
    return {
      'revision':'M9COLORPERFROLLBACK1A_PERF3I_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.95_M9COLORPERF1B_TARGETACTIVE_EXACT',
      'changed':sorted(CHANGED),
      'persistentFullFrameSchedulerEnabled':False,
      'expectedNativeColorCallsAt12MP':8,
      'restoredColorExecutionPath':'PERF3I_BITMAPDIRECT1A_eight_384row_blocks',
      'scalarColourMathChanged':False,
      'sat2Changed':False,
      'curve02Changed':False,
      'bt601Changed':False,
      'tg1Changed':False,
      'orientationMappingChanged':False,
      'phaseNoiseChanged':False,
      'prepChanged':False,
      'amazeChanged':False,
      'autoExposureChanged':False,
      'phone_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.95-m9colorperf1b-targetactive-colorperf1a-phasenoiseperf1c-tg1'" not in gradle or 'versionCode 26715' not in gradle:
        raise SystemExit('rollback requires exact 1.95 assembled parent identity')

    before=inventory(root)
    renderer=(root/RENDER).read_text()
    (root/RENDER).write_text(patch_renderer(renderer))

    gradle=one(gradle,'versionCode 26715',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.95-m9colorperf1b-targetactive-colorperf1a-phasenoiseperf1c-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('rollback unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
