"""Apply streaming diagnostic spool on the exact 1.74 M9PREVIEWHEAP1A assembly."""
from pathlib import Path
import json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
SPOOL='app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
ID='M9SPOOLSTREAM1A'
CHANGED={GRADLE,SPOOL}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root);before=proof['before']
    if now!=proof['after']: raise SystemExit('SPOOLSTREAM assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before);removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))
    if (root/SPOOL).read_bytes()!=(HERE/'M9DiagnosticBurstSpool.java').read_bytes():
        raise SystemExit('SPOOLSTREAM candidate mismatch')

    s=(root/SPOOL).read_text()
    checks={
      'revision marker':'M9SPOOLSTREAM1A' in s,
      'recovery metadata only':'Files.size(source)' in s and 'RECOVERED_BYTES_REFERENCED.addAndGet(size)' in s,
      'no recovery readAllBytes':'Files.readAllBytes(source)' not in s,
      'entry has no byte array':'final byte[] bytes' not in s,
      'manifest bundle':'bounded_manifest_payloads_streamed_individually' in s,
      'bundle no inline payload':'payloadBytesMaterializedForBundle", 0' in s,
      'individual stream':'individualExportMode", "64KiB_stream' in s,
      'stream buffer':'COPY_BUFFER_BYTES = 64 * 1024' in s,
      'recovery heap telemetry':'recoveredPayloadBytesHeldInJavaHeap", 0' in s,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('SPOOLSTREAM verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.75-m9spoolstream1a-tg1'" not in gradle or 'versionCode 26695' not in gradle:
        raise SystemExit('SPOOLSTREAM build identity mismatch')

    # Photographic and live-preview behavior are byte-frozen.
    for rel in [
      'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]:
        if before[rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)

    return {
      'revision':ID,'version':'1.75-m9spoolstream1a-tg1','versionCode':26695,
      'changed':sorted(CHANGED),
      'recoveryReadsPayloadIntoHeap':False,
      'bundleContainsPayloadCopies':False,
      'individualExport':'64KiB_stream',
      'oldPrivateStagesPreserved':True,
      'auto_JPEG_DNG_preview_TC20_shutterDrawLock_frozen':True,
      'deviceValidationPending':True,
    }

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    gradle=(root/GRADLE).read_text()
    if "versionName '1.74-m9previewheap1a-tg1'" not in gradle or 'versionCode 26694' not in gradle:
        raise SystemExit('SPOOLSTREAM requires exact 1.74 parent identity')

    parent=REPO/'patches/colourtrial1e/M9DiagnosticBurstSpool.java'
    if not parent.exists(): raise SystemExit('SPOOLSTREAM parent spool source missing')
    if (root/SPOOL).read_bytes()!=parent.read_bytes():
        raise SystemExit('SPOOLSTREAM exact parent spool mismatch')

    before=inventory(root)
    shutil.copyfile(HERE/'M9DiagnosticBurstSpool.java',root/SPOOL)
    gradle=one(gradle,'versionCode 26694','versionCode 26695','version code')
    gradle=one(gradle,"versionName '1.74-m9previewheap1a-tg1'",
               "versionName '1.75-m9spoolstream1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
