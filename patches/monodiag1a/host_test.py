"""Run actual capture-snapshot and preference-reader methods with a typed store adapter.

This deliberately tests Android's string-vs-Boolean storage boundary without a phone.
ProfileCapture and RenderProfile are complete production classes. Only PreferenceKeys'
three relevant methods are extracted unchanged; the rest of Android is stubbed.
Use the Robolectric test in the patch for full widget/storage integration.
"""
from pathlib import Path
import argparse, json, subprocess, tempfile
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--expect-parent-bug',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
base=a.source.resolve()/'app/src/main/java/com/particlesdevs/photoncamera'
def method(source,signature):
    start=source.index(signature);brace=source.index('{',start);level=1;end=brace+1
    while level:
        if source[end]=='{':level+=1
        if source[end]=='}':level-=1
        end+=1
    return source[start:end]
prefs=(base/'settings/PreferenceKeys.java').read_text()
methods='\n'.join(method(prefs,s) for s in ['private static boolean monoBool(', 'public static boolean isMonoOriginalSensorRawEnabled(', 'public static boolean isMonoDiagnosticsEnabled('])
stubs={
'android/hardware/camera2/CaptureRequest.java':'package android.hardware.camera2; public class CaptureRequest {}',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;
import com.particlesdevs.photoncamera.settings.SettingsManager;
public class PhotonCamera { public static final SettingsManager SETTINGS=new SettingsManager(); public static SettingsManager getSettingsManagerStatic(){return SETTINGS;} }''',
'com/particlesdevs/photoncamera/settings/SettingsManager.java':'''package com.particlesdevs.photoncamera.settings;
import java.util.*;
public class SettingsManager {
 public static final String SCOPE_GLOBAL="default_scope";
 public final Store store=new Store();
 public Store getDefaultPreferences(){return store;}
 public String getString(String scope,String key,String fallback){Object v=store.values.get(key);return v==null?fallback:(String)v;}
 public void set(String scope,String key,String value){store.values.put(key,value);}
 public static class Store {public final Map<String,Object> values=new HashMap<>();
  public Map<String,Object> getAll(){return new HashMap<>(values);}
  public boolean getBoolean(String key,boolean fallback){Object v=values.get(key);return v==null?fallback:(Boolean)v;}
 }
}''',
'com/particlesdevs/photoncamera/settings/PreferenceKeys.java':'''package com.particlesdevs.photoncamera.settings;
import com.particlesdevs.photoncamera.app.PhotonCamera;
public class PreferenceKeys {
 private static final PreferenceKeys preferenceKeys=new PreferenceKeys();
 private final SettingsManager settingsManager=PhotonCamera.SETTINGS;
'''+methods+'\n}',
'Probe.java':'''import java.util.*;
import java.util.concurrent.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.renderprofile.*;
import com.particlesdevs.photoncamera.settings.*;
public class Probe {
 static int checks=0;
 static void check(boolean ok){checks++;if(!ok)throw new AssertionError("check "+checks);}
 public static void main(String[] args)throws Exception {
  boolean parent=args.length>0;
  Map<String,Object> store=PhotonCamera.SETTINGS.store.values;
  String diag="pref_m9_save_diagnostic_files", raw="pref_m9_save_unfiltered_dng";
  RenderProfile.persist(RenderProfile.MONOCHROM);
  store.put(diag,"1");store.put(raw,"0");
  ProfileCapture.Snapshot enabled=ProfileCapture.freeze();
  if(parent) {
   try(ProfileCapture.Scope s=enabled.open()){check(!PreferenceKeys.isMonoDiagnosticsEnabled());}
   boolean failed=false;try{PreferenceKeys.isMonoDiagnosticsEnabled();}catch(ClassCastException expected){failed=true;}
   check(failed);System.out.println("REPRODUCED: enabled switch reads false in capture snapshot and throws on live export read; checks="+checks);return;
  }
  check(PreferenceKeys.isMonoDiagnosticsEnabled());check(!PreferenceKeys.isMonoOriginalSensorRawEnabled());
  for(boolean d:new boolean[]{false,true})for(boolean r:new boolean[]{false,true}) {
   store.put(diag,d?"1":"0");store.put(raw,r?"1":"0");
   check(PreferenceKeys.isMonoDiagnosticsEnabled()==d);check(PreferenceKeys.isMonoOriginalSensorRawEnabled()==r);
   ProfileCapture.Snapshot shot=ProfileCapture.freeze();
   store.put(diag,d?"0":"1");store.put(raw,r?"0":"1");
   try(ProfileCapture.Scope s=shot.open()) {
    check(PreferenceKeys.isMonoDiagnosticsEnabled()==d);check(PreferenceKeys.isMonoOriginalSensorRawEnabled()==r);
    try(ProfileCapture.Scope nested=enabled.open()){check(PreferenceKeys.isMonoDiagnosticsEnabled());check(!PreferenceKeys.isMonoOriginalSensorRawEnabled());}
    check(PreferenceKeys.isMonoDiagnosticsEnabled()==d);
   }
   check(ProfileCapture.current()==null);
  }
  for(Object value:new Object[]{null,"","oops","true","2147483648",true,false,"0","1","-1","2"}) {
   store.put(diag,value);Map<String,Object> before=new HashMap<>(store);
   boolean expected=Boolean.TRUE.equals(value)||"1".equals(value)||"-1".equals(value)||"2".equals(value);
   check(PreferenceKeys.isMonoDiagnosticsEnabled()==expected);
   try(ProfileCapture.Scope s=ProfileCapture.freeze().open()){check(PreferenceKeys.isMonoDiagnosticsEnabled()==expected);}
   check(store.equals(before));
  }
  ExecutorService worker=Executors.newSingleThreadExecutor();
  try {
   check(worker.submit(()->{try(ProfileCapture.Scope s=enabled.open()){return PreferenceKeys.isMonoDiagnosticsEnabled();}}).get());
   check(worker.submit(()->ProfileCapture.current()==null).get());
  }finally{worker.shutdownNow();}
  System.out.println("PASS: string/native Boolean reads, malformed values, independent switches, frozen/nested/worker scopes; checks="+checks);
 }
}'''
}
with tempfile.TemporaryDirectory() as folder:
    tmp=Path(folder);classes=tmp/'classes';classes.mkdir()
    for name,body in stubs.items():
        target=tmp/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
    sources=list(tmp.rglob('*.java'))+[base/'renderprofile/ProfileCapture.java',base/'renderprofile/RenderProfile.java']
    subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),*map(str,sources)],check=True)
    run=subprocess.run(['java','-cp',str(classes),'Probe']+(['parent'] if a.expect_parent_bug else []),capture_output=True,text=True,check=True)
    print(run.stdout.strip())
    if a.output:
        a.output.write_text(json.dumps(dict(status='REPRODUCED' if a.expect_parent_bug else 'PASS',output=run.stdout.strip(),limits='Typed store adapter; complete ProfileCapture/RenderProfile, unchanged extracted PreferenceKeys reader methods. Not Android storage or device validation.'),indent=2)+'\n')
