"""Run inherited production-controller tests plus recorded-boundary regressions."""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys
p=argparse.ArgumentParser()
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--output',type=Path,required=True);p.add_argument('--json-jar',type=Path,required=True)
a=p.parse_args();here=Path(__file__).resolve().parent;out=a.output.resolve();jar=a.json_jar.resolve()
assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
subprocess.run([sys.executable,str(here/'inherited_host_test.py'),str(a.parent),str(a.candidate),
 '--json-jar',str(jar),'--output',str(out/'inherited')],check=True)
report={'status':'PASS','scope':'Gate-level regression and full production controller with synthetic timing and missing bracket steps; not a complete camera replay','versions':{}}
for version in ['parent','candidate']:
 classes=out/'inherited'/version/'classes';cp=str(jar)+':'+str(classes)
 tests=['RegionalFixture.java','RegionalControllerTest.java']+(['RegionalClipTest.java'] if version=='candidate' else [])
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',cp,'-d',str(classes),*[str(here/t) for t in tests]],check=True)
 results={}
 for test in ['RegionalControllerTest']+(['RegionalClipTest'] if version=='candidate' else []):
  result=subprocess.run(['java','-ea','-cp',cp,'com.particlesdevs.photoncamera.m9.preview.'+test,
   str(here/'RecordedRegionalRows.json'),str(version=='candidate').lower()],capture_output=True,text=True)
  results[test]={'exitCode':result.returncode,'output':result.stdout+result.stderr}
  if result.returncode:report['status']='FAIL'
 report['versions'][version]=results
(out/'REGIONAL_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='PASS' else 1)
