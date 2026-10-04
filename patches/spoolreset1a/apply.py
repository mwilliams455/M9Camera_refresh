#!/usr/bin/env python3
"""1.98 M9SPOOLRESET1A.

One-time purge of only the app-private diagnostic spool backlog before restart
recovery runs. This prevents hundreds of recovered sidecars from being exported
minutes or hours after the capture that created them.

No public DCIM files, photographs, DNGs, settings, renderer pixels, exposure,
colour, TC20, SAT2, curve02, TG1 or performance path are changed.
"""
from pathlib import Path
import json,shutil,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_ae1j_apply',REPO/'patches/autoexposurefinish1j/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
SPOOL=BASE+'m9/M9DiagnosticBurstSpool.java'
GRADLE='app/build.gradle'
ID='M9SPOOLRESET1A'
CHANGED={SPOOL,GRADLE}
VERSION='1.98-m9spoolreset1a-ae1j-perf3i-tg1'
CODE=26718

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('M9SPOOLRESET1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('M9SPOOLRESET1A unexpected changed files: '+repr(sorted(changed)))
    if (root/SPOOL).read_bytes()!=(HERE/'M9DiagnosticBurstSpool.java').read_bytes():
        raise SystemExit('M9SPOOLRESET1A spool source mismatch')

    src=(root/SPOOL).read_text()
    checks={
      'revision':'M9SPOOLRESET1A_ONCE' in src,
      'marker outside spool':'filesRoot.resolve(SPOOL_RESET_MARKER)' in src,
      'private spool scope':'filesRoot.resolve("m9diag_spool")' in src,
      'purge before recovery':'purgeLegacyBacklogOnce();\n                recoverPrivate();' in src,
      'one-shot atomic':'SPOOL_RESET_ATTEMPTED.compareAndSet(false, true)' in src,
      'marker after purge':'Files.move(tmp, marker, StandardCopyOption.REPLACE_EXISTING)' in src,
      'public paths not deleted':'Files.deleteIfExists(e.publicPath)' not in src,
      'pending maps cleared':'INDIVIDUAL_PENDING.clear();' in src and 'BUNDLE_PENDING.clear();' in src,
      'export queues cleared':'RECOVERED_PRIMARY_EXPORTER.getQueue().clear();' in src,
      'telemetry':'spoolResetDeletedBytes' in src and 'spoolResetCompleted' in src,
      'fresh primary retained':'M9PRIMARYEXPORT1B_FRESHFIRST' in src,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('M9SPOOLRESET1A verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('M9SPOOLRESET1A version mismatch')

    return {
      'revision':'M9SPOOLRESET1A_ONCE',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'1.97_M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A',
      'changed':sorted(CHANGED),
      'privateSpoolDirectory':'filesDir/m9diag_spool',
      'publicDcimDiagnosticsDeleted':False,
      'jpegDeleted':False,
      'dngDeleted':False,
      'preferencesChanged':False,
      'runsOncePerAppData':True,
      'resetBeforeRecovery':True,
      'freshPrimaryExporterPreserved':True,
      'rendererChanged':False,
      'captureExposureChanged':False,
      'tc20Changed':False,
      'sat2Changed':False,
      'curve02Changed':False,
      'tg1Changed':False,
      'phone_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    parent_spool=REPO/'patches/primaryexport1b/M9DiagnosticBurstSpool.java'
    if (root/SPOOL).read_bytes()!=parent_spool.read_bytes():
        raise SystemExit('M9SPOOLRESET1A requires exact PRIMARYEXPORT1B spool source at final parent')

    gradle=(root/GRADLE).read_text()
    parent_version='1.97-m9ae1j-bodylockrel1a-perf3i-tg1'
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26717' not in gradle:
        raise SystemExit('M9SPOOLRESET1A requires exact 1.97 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9DiagnosticBurstSpool.java',root/SPOOL)
    gradle=one(gradle,'versionCode 26717',f'versionCode {CODE}','version code')
    gradle=one(gradle,f"versionName '{parent_version}'",f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('M9SPOOLRESET1A unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
