#!/usr/bin/env python3
"""Exercise production output boundaries with minimal platform/app service adapters."""
from pathlib import Path
import json,subprocess,sys,urllib.request,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera';stub=out/'stubs';classes=out/'classes';classes.mkdir(exist_ok=True)
jar=out/'json.jar'
if not jar.exists():
 with urllib.request.urlopen('https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar',timeout=30) as r:jar.write_bytes(r.read())
stubs={
'android/content/Context.java':'''package android.content; public class Context {private final java.io.File files;public Context(java.io.File f){files=f;}public java.io.File getFilesDir(){return files;}}''',
'android/os/Process.java':'''package android.os;public class Process {public static final int THREAD_PRIORITY_BACKGROUND=10;public static void setThreadPriority(int n){}}''',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;import com.particlesdevs.photoncamera.settings.SettingsManager;public class PhotonCamera {public static SettingsManager settings=new SettingsManager();public static android.content.Context context;public static SettingsManager getSettingsManagerStatic(){return settings;}public static android.content.Context getAppContext(){return context;}}''',
'com/particlesdevs/photoncamera/settings/SettingsManager.java':'''package com.particlesdevs.photoncamera.settings;public class SettingsManager {public static final String SCOPE_GLOBAL="global";public final java.util.Map<String,String> values=new java.util.concurrent.ConcurrentHashMap<>();public boolean getBoolean(String scope,String key,boolean d){return Integer.parseInt(values.getOrDefault(key,d?"1":"0"))!=0;}}''',
'com/particlesdevs/photoncamera/util/Log.java':'''package com.particlesdevs.photoncamera.util;public class Log {public static void d(String a,String b){}public static void w(String a,String b){}public static void e(String a,String b,Throwable t){}}''',
'com/particlesdevs/photoncamera/util/SimpleStorageHelper.java':'''package com.particlesdevs.photoncamera.util;public class SimpleStorageHelper {public static java.io.OutputStream openOutputStreamByAbsPath(String p){return null;}}'''
}
for name,s in stubs.items():p=stub/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
sources=[src/name for name in ['m9/M9OutputSettings.java','m9/M9DiagnosticBurstSpool.java','m9/M9DiagnosticSidecarIO.java','m9/M9DeferredMetadataStore.java','processing/M9DngRawPair.java']]
subprocess.run(['java','com.sun.tools.javac.Main','-cp',str(jar),'-d',str(classes),*map(str,stub.rglob('*.java')),*map(str,sources),str(HERE/'OutputHostProbe.java')],check=True)
log=subprocess.check_output(['java','-cp',str(classes)+':'+str(jar),'com.particlesdevs.photoncamera.m9.OutputHostProbe',str(out/'cases')],text=True);assert 'OUTPUT_CASES=8' in log
ns='{http://schemas.android.com/apk/res/android}';ui=ET.parse(root/'app/src/main/res/xml/preferences.xml').getroot();photo=next(x for x in ui if x.get(ns+'key')=='@string/pref_category_photo_key')
for key in ['pref_m9_save_unfiltered_dng','pref_m9_save_diagnostic_files']:
 p=next(x for x in photo if x.get(ns+'key')==key);assert p.get(ns+'defaultValue')=='false';assert p.tag.endswith('ManagedSwitchPreference')
queue=(src/'m9/render/M9PrimaryRenderQueue.java').read_text()
assert queue.index('final boolean saveUnfilteredDng = M9OutputSettings.saveUnfilteredDng();')<queue.index('Runnable job =')
assert 'job.cameraRotation, job.saveUnfilteredDng);' in queue
assert 'M9DngProfileExport.embed(' in queue and 'rendererDiagnosticsJson = renderResult.diagnostics.toString()' in queue
image=(src/'processing/ImageSaver.java').read_text();assert 'M9DngRawPair.saveIfEnabled(saveUnfilteredDng, dngFilePath,' in image
assert image.index('boolean boundary2QSaved = saveSingleRaw')<image.index('M9DngRawPair.saveIfEnabled(')
logsrc=(src/'util/Log.java').read_text();publish=logsrc[logsrc.index('private static boolean publish('):logsrc.index('private static void writeToFile(')]
assert publish.index('M9OutputSettings.diagnosticsEnabled()')<publish.index('DocumentFileCompat.fromSimplePath(')
assert 'onDiagnosticPreferenceChanged()' in (src/'ui/settings/SettingsActivity.java').read_text()
report=dict(status='passed',outputCombinations=4,behaviorCases=8,defaultsOff=True,primaryFilesPreserved=True,renderMetadataPreserved=True,unfilteredAvoidsAllWorkWhenOff=True,delayedAndFallbackSidecarsBlockedWhenOff=True,rawOptionFrozenAtEnqueue=True,exportedLogsGated=True,existingPublicFilesNotDeleted=True,handsetValidationPending=True)
(out/'OUTPUT_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(log.strip());print(json.dumps(report))
