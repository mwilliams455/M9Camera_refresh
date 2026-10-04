#!/usr/bin/env python3
"""Apply PRIMARYEXPORT1B fresh-first transport after exact 1.84 PRIMARYEXPORT1A."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

SPOOL='app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
GRADLE='app/build.gradle'
ID='M9PRIMARYEXPORT1B'
CHANGED={SPOOL,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PRIMARYEXPORT1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/SPOOL).read_bytes()!=(HERE/'M9DiagnosticBurstSpool.java').read_bytes():
        raise SystemExit('PRIMARYEXPORT1B spool source mismatch')
    s=(root/SPOOL).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9PRIMARYEXPORT1B_FRESHFIRST' in s,
      'fresh exporter':'M9DiagPrimaryFreshIO' in s,
      'backfill exporter':'M9DiagPrimaryBackfillIO' in s,
      'fresh delay':'PRIMARY_TIMING_EXPORT_DELAY_MS = 100L' in s,
      'backfill delay':'RECOVERED_PRIMARY_EXPORT_DELAY_MS = 1000L' in s,
      'fresh schedule':'exportIndividual(entry, true, false)' in s,
      'recovered schedule':'exportIndividual(e, false, true)' in s,
      'private first retained':'Files.write(privatePath, bytes)' in s and 'persistManifest(entry)' in s,
      'normal export retained':'INDIVIDUAL_DELAY_MS = 12000L' in s,
      'streaming retained':'streamPublic(entry.publicPath, entry.privatePath)' in s,
      '64k retained':'COPY_BUFFER_BYTES = 64 * 1024' in s,
      'fresh telemetry':'freshPrimaryWrites' in s and 'primaryTimingFreshFirstIsolation' in s,
      'failure retention':'individual stream export failed; private stage retained' in s,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PRIMARYEXPORT1B verify failed: '+name)
    if "versionName '1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1'" not in g or 'versionCode 26705' not in g:
        raise SystemExit('PRIMARYEXPORT1B version mismatch')

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
      'version':'1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1',
      'versionCode':26705,
      'changed':sorted(CHANGED),
      'parent':'1.84_M9PRIMARYEXPORT1A',
      'diagnosis':'fresh_PRIMARY_blocked_by_recovered_PRIMARY_backlog',
      'freshPrimaryExportDelayMs':100,
      'recoveredPrimaryExportDelayMs':1000,
      'freshPrimaryExporterIsolated':True,
      'recoveredPrimaryBackfillIsolated':True,
      'privateFirstDurabilityPreserved':True,
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

    parent=REPO/'patches/primaryexport1a/M9DiagnosticBurstSpool.java'
    if (root/SPOOL).read_bytes()!=parent.read_bytes():
        raise SystemExit('PRIMARYEXPORT1B requires exact PRIMARYEXPORT1A source')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.84-m9primaryexport1a-noisecancel1a-tg1'" not in gradle or 'versionCode 26704' not in gradle:
        raise SystemExit('PRIMARYEXPORT1B requires exact 1.84 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9DiagnosticBurstSpool.java',root/SPOOL)
    gradle=one(gradle,'versionCode 26704','versionCode 26705','version code')
    gradle=one(gradle,
        "versionName '1.84-m9primaryexport1a-noisecancel1a-tg1'",
        "versionName '1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
