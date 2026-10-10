"""Reuse the shipped full-spool harness, adding the real Monochrom adapter scenario."""
from pathlib import Path
import argparse, subprocess, shutil, json
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
here=Path(__file__).resolve().parent;old=here.parent/'shutterexport1a'
work=a.output.resolve();work.mkdir(parents=True,exist_ok=True)
runner=(old/'host_test.py').read_text()
runner=runner.replace("for name in ['SpoolTest.java','SimpleStorageHelper.java']:","for name in ['SpoolTest.java','SimpleStorageHelper.java','MonoSpoolScenario.java']:")
runner=runner.replace("java=['java'",'''name='com/particlesdevs/photoncamera/monochrom/M9DiagnosticBurstSpool.java'
target=src/name;target.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(a.source/'app/src/main/java'/name,target)
target=src/'com/particlesdevs/photoncamera/settings/PreferenceKeys.java';target.parent.mkdir(parents=True,exist_ok=True)
target.write_text('package com.particlesdevs.photoncamera.settings; public class PreferenceKeys { public static volatile boolean enabled=true; public static boolean isMonoDiagnosticsEnabled(){return enabled;} }')
java=['java' ''')
runner=runner.replace("['backlog','coalesce','retry','lifecycle']","['monochrom']")
(work/'host_test.py').write_text(runner)
probe=(old/'SpoolTest.java').read_text().replace('case "backlog"->backlog();','case "monochrom"->MonoSpoolScenario.run();case "backlog"->backlog();')
(work/'SpoolTest.java').write_text(probe)
for name,source in [('SimpleStorageHelper.java',old),('MonoSpoolScenario.java',here)]:shutil.copyfile(source/name,work/name)
subprocess.run(['python3',str(work/'host_test.py'),str(a.source.resolve()),'--output',str(work/'run')],check=True)
report=json.loads((work/'run/HOST_VERIFICATION.json').read_text());report['productionAdapter']='monochrom.M9DiagnosticBurstSpool';report['preferenceReadAdapterStubbed']=True
(here/'TRANSPORT_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
