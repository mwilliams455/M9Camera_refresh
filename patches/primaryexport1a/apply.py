#!/usr/bin/env python3
"""Apply PRIMARYEXPORT1A priority transport after exact 1.83 NOISECANCEL1A."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

SPOOL='app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
GRADLE='app/build.gradle'
ID='M9PRIMARYEXPORT1A'
CHANGED={SPOOL,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PRIMARYEXPORT1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/SPOOL).read_bytes()!=(HERE/'M9DiagnosticBurstSpool.java').read_bytes():
        raise SystemExit('PRIMARYEXPORT1A spool source mismatch')

    s=(root/SPOOL).read_text();g=(root/GRADLE).read_text()
    checks={
      'priority marker':'PRIMARYEXPORT1A' in s,
      'private first retained':'Files.write(privatePath, bytes)' in s and 'persistManifest(entry)' in s,
      'normal exporter retained':'M9DiagIndividualIO' in s and 'INDIVIDUAL_DELAY_MS = 12000L' in s,
      'primary exporter':'M9DiagPrimaryIO' in s,
      'priority role':'PRIORITY_ROLE = "primary_timing"' in s,
      'priority delay':'PRIMARY_TIMING_EXPORT_DELAY_MS = 250L' in s,
      'stage priority':'if (isPriorityRole(entry.role))' in s,
      'restart priority':'if (isPriorityRole(e.role))' in s,
      'streaming retained':'streamPublic(entry.publicPath, entry.privatePath)' in s,
      '64k retained':'COPY_BUFFER_BYTES = 64 * 1024' in s,
      'manifest payload remains bounded':'payloadBytesMaterializedForBundle", 0' in s,
      'failure retains private':'individual stream export failed; private stage retained' in s,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PRIMARYEXPORT1A verify failed: '+name)

    if "versionName '1.84-m9primaryexport1a-noisecancel1a-tg1'" not in g or 'versionCode 26704' not in g:
        raise SystemExit('PRIMARYEXPORT1A version mismatch')

    frozen=[
      'app/src/main/cpp/m9detail1h_guard.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)

    return {
      'revision':ID,
      'version':'1.84-m9primaryexport1a-noisecancel1a-tg1',
      'versionCode':26704,
      'changed':sorted(CHANGED),
      'parent':'1.83_M9NOISECANCEL1A_QUIETCHROMA',
      'diagnosis':'PRIMARY_already_private_staged_public_export_backlog',
      'primaryRole':'primary_timing',
      'primaryExportDelayMs':250,
      'normalDiagnosticExportDelayMs':12000,
      'dedicatedPrimaryExporter':True,
      'restartRecoveryPriorityPreserved':True,
      'privateFirstDurabilityPreserved':True,
      'bundleManifestPolicyChanged':False,
      'renderingChanged':False,
      'noisePolicyChanged':False,
      'autoExposureChanged':False,
      'JPEG_DNG_preview_changed':False,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent=REPO/'patches/spoolstream1a/M9DiagnosticBurstSpool.java'
    if (root/SPOOL).read_bytes()!=parent.read_bytes():
        raise SystemExit('PRIMARYEXPORT1A requires exact M9SPOOLSTREAM1A source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.83-m9noisecancel1a-quietchroma-tg1'" not in gradle or 'versionCode 26703' not in gradle:
        raise SystemExit('PRIMARYEXPORT1A requires exact 1.83 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9DiagnosticBurstSpool.java',root/SPOOL)
    gradle=one(gradle,'versionCode 26703','versionCode 26704','version code')
    gradle=one(gradle,
        "versionName '1.83-m9noisecancel1a-quietchroma-tg1'",
        "versionName '1.84-m9primaryexport1a-noisecancel1a-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
