"""Run complete production Auto/tap classes on synthetic sustained-recovery probes."""
from pathlib import Path
import argparse, ast, hashlib, json, subprocess
p=argparse.ArgumentParser()
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
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
report={'status':'PASS','scope':'synthetic probes through full production Auto/tap classes; JSON serialization stubbed; no device measurements','versions':{}}
for name,source in [('parent',a.parent),('candidate',a.candidate)]:
 out=a.output.resolve()/name;out.mkdir(parents=True,exist_ok=True)
 hashes={}
 files=dict(stubs)|inherited|{'SustainedRecoveryTest.java':(here/'SustainedRecoveryTest.java').read_text(),'SettlingTest.java':(here.parent/'previewsettle1a/SettlingTest.java').read_text(),'ReferenceGapRepro.java':(here.parent/'previewbridge1a/ReferenceGapRepro.java').read_text(),'BridgeTest.java':(here.parent/'previewbridge1a/BridgeTest.java').read_text(),'RecoveryTest.java':(here.parent/'previewrecover1a/RecoveryTest.java').read_text()}
 for cls in ['M9AutoExposure2D','M9TapMeter1A']:
  path=pkg+cls+'.java';raw=(source/'app/src/main/java'/path).read_bytes()
  files[path]=raw.decode();hashes[path]=hashlib.sha256(raw).hexdigest()
 for path,content in files.items():
  dst=out/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(content)
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out/'classes'),*[str(out/f) for f in files]],check=True)
 tests={}
 for cls in ['PolicyTest','HighlightGrandfatherTest','com.particlesdevs.photoncamera.m9.preview.SubjectHeadroomTest','SettlingTest','com.particlesdevs.photoncamera.m9.preview.RecoveryTest','com.particlesdevs.photoncamera.m9.preview.BridgeTest','com.particlesdevs.photoncamera.m9.preview.ReferenceGapRepro','com.particlesdevs.photoncamera.m9.preview.SustainedRecoveryTest']:
  cmd=['java','-ea','-cp',str(out/'classes'),cls]
  if cls=='SettlingTest':cmd.append('true')
  if cls=='com.particlesdevs.photoncamera.m9.preview.RecoveryTest':cmd.append('true')
  if cls.endswith('BridgeTest'):cmd.append('true')
  if cls.endswith('SustainedRecoveryTest'):cmd.append(str(name=='candidate').lower())
  text=subprocess.check_output(cmd,text=True);tests[cls]=text
  (out/(cls.rsplit('.',1)[-1]+'.log')).write_text(text)
 report['versions'][name]={'sourceSha256':hashes,'results':tests}
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({name:{cls:log.splitlines()[-1] for cls,log in info['results'].items()} for name,info in report['versions'].items()},indent=2))
