"""Execute production journal, logger, lifecycle and spool against counted Android IPC fakes."""
from pathlib import Path
import subprocess,sys,tempfile,json
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
j=root/'app/src/main/java/com/particlesdevs/photoncamera'
stubs={
'android/os/Looper.java':'''package android.os;import java.util.*;public class Looper {
 public static final Map<String,Looper> all=new HashMap<>();public long now;int seq;
 static class Job {Runnable r;long due;int seq;Job(Runnable r,long d,int s){this.r=r;due=d;seq=s;}}
 final List<Job> jobs=new ArrayList<>();public void add(Runnable r,long delay){jobs.add(new Job(r,now+delay,seq++));}
 public void remove(Runnable r){jobs.removeIf(j->j.r==r);}public int size(){return jobs.size();}
 public void advance(long ms){now+=ms;for(int count=0;;count++){Job next=jobs.stream().filter(j->j.due<=now).min(Comparator.comparingLong((Job j)->j.due).thenComparingInt(j->j.seq)).orElse(null);if(next==null)return;if(count>200000)throw new AssertionError("unbounded queue");jobs.remove(next);next.r.run();}}
}''',
'android/os/HandlerThread.java':'''package android.os;public class HandlerThread {private final Looper loop=new Looper();public HandlerThread(String n){Looper.all.put(n,loop);}public void start(){}public Looper getLooper(){return loop;}public void quitSafely(){loop.advance(0);}}''',
'android/os/Handler.java':'''package android.os;public class Handler {final Looper loop;public Handler(Looper l){loop=l;}public boolean post(Runnable r){loop.add(r,0);return true;}public boolean postDelayed(Runnable r,long d){loop.add(r,d);return true;}public void removeCallbacks(Runnable r){loop.remove(r);}}''',
'android/os/Process.java':'''package android.os;public class Process {public static final int THREAD_PRIORITY_BACKGROUND=10;public static void setThreadPriority(int p){}}''',
'android/os/Bundle.java':'package android.os;public class Bundle {}',
'android/util/Log.java':'''package android.util;public class Log {public static int d(String t,String m){return 0;}public static int i(String t,String m){return 0;}public static int v(String t,String m){return 0;}public static int w(String t,String m){return 0;}public static int w(String t,String m,Throwable e){return 0;}public static int e(String t,String m){return 0;}public static int e(String t,String m,Throwable e){return 0;}public static String getStackTraceString(Throwable t){return t.toString();}}''',
'android/net/Uri.java':'''package android.net;public class Uri {public final String path;public Uri(String p){path=p;}}''',
'android/content/Context.java':'''package android.content;import java.io.*;public class Context {public final File dir;public final ContentResolver resolver=new ContentResolver();public Context(File f){dir=f;}public Context getApplicationContext(){return this;}public File getFilesDir(){return dir;}public ContentResolver getContentResolver(){return resolver;}}''',
'android/content/ContentResolver.java':'''package android.content;import java.io.*;import android.net.Uri;import java.util.*;public class ContentResolver {
 public static final Map<String,ByteArrayOutputStream> data=new HashMap<>();public static int opens,closes,active,maxActive;public static boolean fail;
 public OutputStream openOutputStream(Uri uri,String mode){if(!mode.equals("wa"))throw new AssertionError("append mode");opens++;active++;maxActive=Math.max(maxActive,active);
 ByteArrayOutputStream sink=data.computeIfAbsent(uri.path,k->new ByteArrayOutputStream());return new OutputStream(){public void write(int b)throws IOException{if(fail)throw new IOException("injected failure");sink.write(b);}public void write(byte[] b,int o,int n)throws IOException{if(fail)throw new IOException("injected failure");sink.write(b,o,n);}public void close(){closes++;active--;}};}
}''',
'android/app/Activity.java':'package android.app;public class Activity {public String getLocalClassName(){return "Camera";}}',
'android/app/Application.java':'''package android.app;import android.os.Bundle;public class Application {public interface ActivityLifecycleCallbacks {void onActivityCreated(Activity a,Bundle b);void onActivityStarted(Activity a);void onActivityResumed(Activity a);void onActivityPaused(Activity a);void onActivityStopped(Activity a);void onActivitySaveInstanceState(Activity a,Bundle b);void onActivityDestroyed(Activity a);}}''',
'androidx/annotation/NonNull.java':'package androidx.annotation;public @interface NonNull {}',
'androidx/annotation/Nullable.java':'package androidx.annotation;public @interface Nullable {}',
'androidx/documentfile/provider/DocumentFile.java':'''package androidx.documentfile.provider;import android.net.Uri;import java.util.*;public class DocumentFile {public static int queries;final String path;public DocumentFile(String p){path=p;}public DocumentFile findFile(String n){queries++;return new DocumentFile(path+"/"+n);}public DocumentFile createDirectory(String n){queries++;return new DocumentFile(path+"/"+n);}public DocumentFile createFile(String mime,String n){queries++;return new DocumentFile(path+"/"+n);}public Uri getUri(){return new Uri(path);}}''',
'com/anggrayudi/storage/file/DocumentFileCompat.java':'''package com.anggrayudi.storage.file;import android.content.Context;import androidx.documentfile.provider.DocumentFile;public class DocumentFileCompat {public static int queries;public static DocumentFile fromSimplePath(Context c,String id,String path,int type,boolean flag){queries++;return new DocumentFile(path);}}''',
'com/anggrayudi/storage/file/DocumentFileType.java':'package com.anggrayudi.storage.file;public class DocumentFileType {public static final int FOLDER=1;}',
'com/anggrayudi/storage/file/StorageId.java':'package com.anggrayudi.storage.file;public class StorageId {public static final String PRIMARY="primary";}',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;import android.content.Context;public class PhotonCamera {public static final boolean DEBUG=false;public static Context context;public static Context getAppContext(){return context;}}''',
'com/particlesdevs/photoncamera/m9/render/M9RenderCrash1D.java':'''package com.particlesdevs.photoncamera.m9.render;public class M9RenderCrash1D {public static int calls;public static void storageReady(){calls++;}}''',
'com/particlesdevs/photoncamera/util/SimpleStorageHelper.java':'''package com.particlesdevs.photoncamera.util;import java.io.*;import java.util.*;import android.content.Context;public class SimpleStorageHelper {public static final String PHOTON_CAMERA_RELATIVE_PATH="DCIM/PhotonCamera";public static int checks,opens,closes,active;public static boolean fail,permissionFailure;public static final Map<String,ByteArrayOutputStream> data=new HashMap<>();public static boolean hasStorageAccess(Context c){checks++;if(permissionFailure){Log.e("Storage","injected permission error");return false;}return true;}
 public static OutputStream openOutputStreamByAbsPath(String path)throws IOException{opens++;if(fail)throw new IOException("injected provider death");active++;ByteArrayOutputStream bytes=new ByteArrayOutputStream();data.put(path,bytes);return new FilterOutputStream(bytes){public void close()throws IOException{super.close();active--;closes++;}};}}
''',
# Serialization-only JSON facade: Android's real org.json is compiled by the APK gate.
'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject {final Map<String,Object> values=new LinkedHashMap<>();String raw;public JSONObject(){}public JSONObject(String s){raw=s;}public JSONObject put(String k,Object v){values.put(k,v);return this;}public Object get(String k){return values.get(k);}public static String str(Object o){if(o instanceof String)return "\\\""+((String)o).replace("\\\\","\\\\\\\\").replace("\\\"","\\\\\\\"").replace("\\n","\\\\n")+"\\\"";return String.valueOf(o);}public String toString(){if(raw!=null)return raw;StringJoiner s=new StringJoiner(",","{","}");values.forEach((k,v)->s.add(str(k)+":"+str(v)));return s.toString();}public String toString(int indent){return toString();}}''',
'org/json/JSONArray.java':'''package org.json;import java.util.*;public class JSONArray {final List<Object> a=new ArrayList<>();public JSONArray put(Object o){a.add(o);return this;}public String toString(){StringJoiner j=new StringJoiner(",","[","]");a.forEach(o->j.add(JSONObject.str(o)));return j.toString();}}'''
}
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);out=d/'classes';out.mkdir()
 for path,code in stubs.items():
  p=d/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(code)
 sources=[j/p for p in ['util/M9LocalLog1E.java','util/Log.java','util/log/ActivityLifecycleMonitor.java','m9/M9DiagnosticBurstSpool.java']]
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),*[str(p) for p in d.rglob('*.java')],*[str(p) for p in sources],str(here/'JournalTest.java'),str(here/'AndroidIoTest.java')],check=True)
 for main,args in [('JournalTest',[]),('AndroidIoTest',['logger']),('AndroidIoTest',['stage',str(d/'restart')]),('AndroidIoTest',['recover',str(d/'restart')])]:
  subprocess.run(['java','-ea','-cp',str(out),main,*args],check=True,timeout=30)
 print(json.dumps({'revision':'M9DIAGIO1E','actual_production_java':True,'ipc_implementation':'counted Android fakes; device validation still required','journal_exact_bytes_restart_failure_concurrency':'PASS','logger_background_bounded_ipc_descriptor_cleanup':'PASS','activity_overlap_debug_false':'PASS','spool_background_failure_restart_latest_payload':'PASS'}))
