"""Run complete production Auto/tap classes on background qualification and inherited recovery probes."""
from pathlib import Path
import argparse, ast, hashlib, json, subprocess
p=argparse.ArgumentParser()
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--output',type=Path,required=True);p.add_argument('--json-jar',type=Path);a=p.parse_args()
here=Path(__file__).resolve().parent;repo=here.parents[1]
pkg='com/particlesdevs/photoncamera/m9/preview/'
stubs={
 'org/json/JSONException.java':'package org.json;public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json;public class JSONObject {public static final Object NULL=new Object();public JSONObject put(String k,Object v)throws JSONException{return this;}public String toString(){return "{}";}}',
 'org/json/JSONArray.java':'package org.json;public class JSONArray {public JSONArray put(Object v){return this;}}'
}
def literal(path,name):
 for n in ast.parse(path.read_text()).body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):return ast.literal_eval(n.value)
 raise RuntimeError(name)
rev='M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A'
inherited={
 'PolicyTest.java':literal(repo/'patches/autoexposurefinish1l/test.py','source').replace('M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',rev),
 'HighlightGrandfatherTest.java':literal(repo/'patches/autoexposurefinish1m/test.py','runner').replace('M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',rev),
 'SubjectHeadroomTest.java':literal(repo/'patches/autoexposurefinish1n/test.py','extra')
}
report={'status':'PASS','scope':'full production Auto/tap classes, recorded room bracket with synthetic temporal perturbations; no device measurements','jsonSerialization':'org.json 20250517 host implementation' if a.json_jar else 'stubbed','versions':{}}
for name,source in [('parent',a.parent),('candidate',a.candidate)]:
 out=a.output.resolve()/name;out.mkdir(parents=True,exist_ok=True)
 hashes={}
 files=({} if a.json_jar else dict(stubs))|inherited|{'SustainedRecoveryTest.java':(here.parent/'previewrecover1b/SustainedRecoveryTest.java').read_text(),'SettlingTest.java':(here.parent/'previewsettle1a/SettlingTest.java').read_text(),'ReferenceGapRepro.java':(here.parent/'previewbridge1a/ReferenceGapRepro.java').read_text(),'BridgeTest.java':(here.parent/'previewbridge1a/BridgeTest.java').read_text(),'RecoveryTest.java':(here.parent/'previewrecover1a/RecoveryTest.java').read_text()}
 for fixture in ['RecordedRoomFixture.java','RecordedRoomTest.java']: files[fixture]=(here/fixture).read_text()
 if name=='candidate': files['BackgroundQualificationTest.java']=(here/'BackgroundQualificationTest.java').read_text()
 if name=='candidate' and a.json_jar: files['HistoryTest.java']=(here/'HistoryTest.java').read_text()
 for cls in ['M9AutoExposure2D','M9TapMeter1A']+(['M9BackgroundQualification1A','M9MeterDecisionHistory1A'] if name=='candidate' else []):
  path=pkg+cls+'.java';raw=(source/'app/src/main/java'/path).read_bytes()
  files[path]=raw.decode();hashes[path]=hashlib.sha256(raw).hexdigest()
 for path,content in files.items():
  dst=out/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(content)
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main',*(['-cp',str(a.json_jar.resolve())] if a.json_jar else []),'-d',str(out/'classes'),*[str(out/f) for f in files]],check=True)
 tests={}
 for cls in ['PolicyTest','HighlightGrandfatherTest','com.particlesdevs.photoncamera.m9.preview.SubjectHeadroomTest','SettlingTest','com.particlesdevs.photoncamera.m9.preview.RecoveryTest','com.particlesdevs.photoncamera.m9.preview.BridgeTest','com.particlesdevs.photoncamera.m9.preview.ReferenceGapRepro','com.particlesdevs.photoncamera.m9.preview.SustainedRecoveryTest','com.particlesdevs.photoncamera.m9.preview.RecordedRoomTest']+(['com.particlesdevs.photoncamera.m9.preview.BackgroundQualificationTest'] if name=='candidate' else [])+(['com.particlesdevs.photoncamera.m9.preview.HistoryTest'] if name=='candidate' and a.json_jar else []):
  cmd=['java','-ea','-cp',str(out/'classes')+(':'+str(a.json_jar.resolve()) if a.json_jar else ''),cls]
  if cls=='SettlingTest':cmd.append('true')
  if cls=='com.particlesdevs.photoncamera.m9.preview.RecoveryTest':cmd.append('true')
  if cls.endswith('BridgeTest'):cmd.append('true')
  if cls.endswith('RecordedRoomTest'):cmd.append(str(name=='candidate').lower())
  if cls.endswith('SustainedRecoveryTest'):cmd.append('true')
  text=subprocess.check_output(cmd,text=True);tests[cls]=text
  (out/(cls.rsplit('.',1)[-1]+'.log')).write_text(text)
 report['versions'][name]={'sourceSha256':hashes,'results':tests}
if a.json_jar: report['jsonJarSha256']=hashlib.sha256(a.json_jar.read_bytes()).hexdigest()
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({name:{cls:log.splitlines()[-1] for cls,log in info['results'].items()} for name,info in report['versions'].items()},indent=2))
