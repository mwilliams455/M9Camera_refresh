"""Run complete production Auto/tap classes on coordinated exposure settling and inherited recovery probes."""
from pathlib import Path
import argparse, ast, hashlib, json, subprocess
p=argparse.ArgumentParser()
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--output',type=Path,required=True);p.add_argument('--json-jar',type=Path,required=True);a=p.parse_args()
stage=Path(__file__).resolve().parent;here=stage.parent/'exposuresettle1a';repo=here.parents[1]
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
report={'status':'PASS','scope':'full production Auto/tap classes, unchanged 2.66 inherited tests on parent and regional clip candidate; no device measurements','jsonSerialization':'org.json 20250517 host implementation' if a.json_jar else 'stubbed','versions':{}}
for name,source in [('parent',a.parent),('candidate',a.candidate)]:
 out=a.output.resolve()/name;out.mkdir(parents=True,exist_ok=True)
 hashes={}
 files=({} if a.json_jar else dict(stubs))|inherited|{'SustainedRecoveryTest.java':(here.parent/'previewrecover1b/SustainedRecoveryTest.java').read_text(),'SettlingTest.java':(here.parent/'previewsettle1a/SettlingTest.java').read_text(),'ReferenceGapRepro.java':(here.parent/'previewbridge1a/ReferenceGapRepro.java').read_text(),'BridgeTest.java':(here.parent/'previewbridge1a/BridgeTest.java').read_text(),'RecoveryTest.java':(here.parent/'previewrecover1a/RecoveryTest.java').read_text()}
 for fixture in ['RecordedRoomFixture.java','RecordedRoomTest.java']: files[fixture]=(here.parent/'backgroundsettle1a'/fixture).read_text()
 for fixture in ['RecordedAnchorFixture.java','RecordedAnchorTest.java']: files[fixture]=(here.parent/'anchorsettle1a'/fixture).read_text()
 files['BackgroundQualificationTest.java']=(here.parent/'backgroundsettle1a/BackgroundQualificationTest.java').read_text()
 files['OpenAnchorQualificationTest.java']=(here.parent/'anchorsettle1a/OpenAnchorQualificationTest.java').read_text()
 if True:
  for test in ['SettlingTest','RecoveryTest','SustainedRecoveryTest','RecordedAnchorTest','ExposureRiseTest','ToneContinuityTest','CoordinatedExposureTest','RecordedTvFixture','RecordedTvTest','RecordedToneTest']:
   files[test+'.java']=(here/(test+'.java')).read_text()
 if a.json_jar: files['HistoryTest.java']=(here/'HistoryTest.java').read_text()
 for cls in ['M9AutoExposure2D','M9TapMeter1A','M9BackgroundQualification1A','M9MeterDecisionHistory1A']+['M9OpenAnchorQualification1A']+(['M9ExposureRise1A','M9PreviewToneContinuity1A','M9PreviewTc20Math1A'] if True else []):
  path=pkg+cls+'.java';raw=(source/'app/src/main/java'/path).read_bytes()
  files[path]=raw.decode();hashes[path]=hashlib.sha256(raw).hexdigest()
 if name=='candidate':
  files[pkg+'M9RegionalClipQualification1A.java']=(source/'app/src/main/java'/pkg/'M9RegionalClipQualification1A.java').read_text()
 for path,content in files.items():
  dst=out/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(content)
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main',*(['-cp',str(a.json_jar.resolve())] if a.json_jar else []),'-d',str(out/'classes'),*[str(out/f) for f in files]],check=True)
 tests={}
 for cls in ['PolicyTest','HighlightGrandfatherTest','com.particlesdevs.photoncamera.m9.preview.SubjectHeadroomTest','SettlingTest','com.particlesdevs.photoncamera.m9.preview.RecoveryTest','com.particlesdevs.photoncamera.m9.preview.BridgeTest','com.particlesdevs.photoncamera.m9.preview.ReferenceGapRepro','com.particlesdevs.photoncamera.m9.preview.SustainedRecoveryTest','com.particlesdevs.photoncamera.m9.preview.RecordedRoomTest']+['com.particlesdevs.photoncamera.m9.preview.BackgroundQualificationTest','com.particlesdevs.photoncamera.m9.preview.RecordedAnchorTest']+['com.particlesdevs.photoncamera.m9.preview.OpenAnchorQualificationTest']+(['com.particlesdevs.photoncamera.m9.preview.ExposureRiseTest','com.particlesdevs.photoncamera.m9.preview.ToneContinuityTest','com.particlesdevs.photoncamera.m9.preview.CoordinatedExposureTest','com.particlesdevs.photoncamera.m9.preview.RecordedTvTest','com.particlesdevs.photoncamera.m9.preview.RecordedToneTest'] if True else [])+(['com.particlesdevs.photoncamera.m9.preview.HistoryTest'] if a.json_jar else []):
  cmd=['java','-ea','-cp',str(out/'classes')+(':'+str(a.json_jar.resolve()) if a.json_jar else ''),cls]
  if cls.endswith('RecordedToneTest'): cmd.append(str(here/'RecordedToneRows.json'))
  if cls=='SettlingTest':cmd.append('true')
  if cls=='com.particlesdevs.photoncamera.m9.preview.RecoveryTest':cmd.append('true')
  if cls.endswith('BridgeTest'):cmd.append('true')
  if cls.endswith('RecordedRoomTest'):cmd.append('true')
  if cls.endswith('RecordedAnchorTest'):cmd.append('true')
  if cls.endswith('SustainedRecoveryTest'):cmd.append('true')
  result=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  text=result.stdout;tests[cls]=text
  if result.returncode: report['status']='FAIL'
  (out/(cls.rsplit('.',1)[-1]+'.log')).write_text(text)
 report['versions'][name]={'sourceSha256':hashes,'results':tests}
if a.json_jar: report['jsonJarSha256']=hashlib.sha256(a.json_jar.read_bytes()).hexdigest()
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({name:{cls:log.splitlines()[-1] for cls,log in info['results'].items()} for name,info in report['versions'].items()},indent=2))

raise SystemExit(0 if report['status']=='PASS' else 1)
