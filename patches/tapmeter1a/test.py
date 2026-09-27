#!/usr/bin/env python3
"""Complete-class tap tests plus unmodified inherited test bodies. No private photo fixtures."""
from pathlib import Path
import ast,json,re,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(HERE))
from apply import load
REV='M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A'
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
app=Path(sys.argv[2]).resolve()
base=app/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview'

def literal(path,name):
    tree=ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit('Runner missing: '+str(path)+' '+name)

runners={
 'PolicyTest.java':literal(REPO/'patches/autoexposurefinish1l/test.py','source').replace('M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',REV),
 'HighlightGrandfatherTest.java':literal(REPO/'patches/autoexposurefinish1m/test.py','runner').replace('M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',REV),
 'SubjectHeadroomTest.java':literal(REPO/'patches/autoexposurefinish1n/test.py','extra'),
 'TapMeterTest.java':load()['tapTest']}
stubs={
 'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json; public class JSONObject { public static final Object NULL=new Object(); public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
 'org/json/JSONArray.java':'package org.json; public class JSONArray {public JSONArray put(Object v){return this;}}'}
for name,text in {**runners,**stubs}.items():
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
sources=[str(base/'M9AutoExposure2D.java'),str(base/'M9TapMeter1A.java'),*[str(root/n) for n in runners],*[str(root/n) for n in stubs]]
subprocess.run(['javac','-d',str(root/'classes'),*sources],check=True)
results={}
for name in ['PolicyTest','HighlightGrandfatherTest','com.particlesdevs.photoncamera.m9.preview.SubjectHeadroomTest','com.particlesdevs.photoncamera.m9.preview.TapMeterTest']:
    out=subprocess.check_output(['java','-ea','-cp',str(root/'classes'),name],text=True)
    results[name]=out;print(out,end='')
summary={'revision':'M9TAPMETER1A','automaticPolicyRevision':REV,'runners':results,
 'fullCandidateClassExecuted':True,'tapHelperExecuted':True,
 'inheritedTestBodiesChanged':False,'tapTestIsSynthetic':True,
 'androidUiPhoneValidationPending':True,'privateCaptureFixturesPublished':False}
(root/'full_class_tests.json').write_text(json.dumps(summary,indent=2)+'\n')
