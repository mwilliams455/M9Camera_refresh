"""Apply M9PREVIEWHEAP1A to the exact assembled 1.73 preview-stability parent."""
from pathlib import Path
import json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
TRACE='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9RootCauseTrace1A.java'
ID='M9PREVIEWHEAP1A'
CHANGED={GRADLE,TRACE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root); before=proof['before']
    if now!=proof['after']: raise SystemExit('PREVIEWHEAP assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before); removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))

    trace=(root/TRACE).read_text()
    checks={
      'heap marker':'M9PREVIEWHEAP1A' in trace,
      'no full tone curve copy':'copyColorCurve' not in trace,
      'no live float curve array':'new float[' not in trace,
      'no full tone curve JSON':'toneCurvesRgb' not in trace,
      'compact point counts':'toneCurvePointCountsRgb' in trace,
      'context 2Hz':'CONTEXT_PERIOD_NS=500000000L' in trace,
      'OOM diagnostic fail-safe':'catch(OutOfMemoryError e)' in trace and 'dropForMemory();' in trace,
      'per-frame scalar history retained':'rows.addLast(new Row(now,timestamp,result.getFrameNumber(),v,lastCompactContext));' in trace,
      'range API retained':'public static JSONObject range(long startNs,long endNs,String cameraId)' in trace,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREVIEWHEAP verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.74-m9previewheap1a-tg1'" not in gradle or 'versionCode 26694' not in gradle:
        raise SystemExit('PREVIEWHEAP build identity mismatch')

    # This repair is diagnostic-only. Verify all photographic/capture/preview seams are byte-frozen.
    frozen=[
      'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]
    for rel in frozen:
        if before[rel]!=now[rel]: raise SystemExit('frozen photographic seam changed '+rel)

    return {
      'revision':ID,'version':'1.74-m9previewheap1a-tg1','versionCode':26694,
      'changed':sorted(CHANGED),
      'fullPerFrameToneCurvePayloadRemoved':True,
      'compactContextPeriodMs':500,
      'perFrameScalarMetadataRetained':True,
      'diagnosticOomFailSafe':True,
      'auto_JPEG_DNG_preview_shader_TC20_shutterDrawLock_frozen':True,
      'deviceValidationPending':True,
    }

def main(root):
    root=root.resolve(); receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2)); return

    gradle=(root/GRADLE).read_text()
    if "versionName '1.73-m9previewstability1a-tg1'" not in gradle or 'versionCode 26693' not in gradle:
        raise SystemExit('PREVIEWHEAP requires exact 1.73 parent identity')

    # Exact diagnostic parent: no later patch is allowed to have silently edited this collector.
    parent=(REPO/'patches/shuttertrace1a/M9RootCauseTrace1A.java').read_bytes()
    if (root/TRACE).read_bytes()!=parent:
        raise SystemExit('PREVIEWHEAP root-cause collector parent mismatch')

    before=inventory(root)
    shutil.copyfile(HERE/'M9RootCauseTrace1A.java',root/TRACE)
    gradle=one(gradle,'versionCode 26693','versionCode 26694','version code')
    gradle=one(gradle,"versionName '1.73-m9previewstability1a-tg1'",
               "versionName '1.74-m9previewheap1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
